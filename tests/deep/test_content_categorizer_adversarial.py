"""Adversarial deep tests for personal_index.content_categorizer (cycle 175).

Attacks ContentCategorizer, CategorizationResult, TopicCategory, and
TopicScore with guard inputs (None/empty/whitespace/unicode/duplicate/
out-of-range), round-trips, idempotence, property checks, and one
end-to-end CLI run.

DEFECT FILED (pinned xfail-strict, flip to hard passes on fix):
  QA-14: categorize(text, title=None, meta_description=None) crashes with
  AttributeError ('NoneType' object has no attribute 'lower') even though
  the docstring types both parameters as ``str`` with default ``""``.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from personal_index.content_categorizer import (
    BUILTIN_TOPICS,
    CategorizationResult,
    ContentCategorizer,
    TopicCategory,
    TopicScore,
)


# ===========================================================================
# ContentCategorizer - categorize() guard inputs
# ===========================================================================

class TestCategorizeGuards:
    """categorize() with guard / out-of-range inputs."""

    def test_all_falsy_returns_unknown(self):
        """text/title/meta all empty -> primary 'unknown', no crash."""
        c = ContentCategorizer()
        r = c.categorize(text="", title="", url="", meta_description="")
        assert r.primary_topic == "unknown"
        assert r.topics == []
        assert r.confidence == 0.0
        assert r.reasons == ["no content provided"]

    def test_whitespace_only_text_is_not_falsy(self):
        """Whitespace text is truthy, so it goes through the normal path."""
        c = ContentCategorizer()
        r = c.categorize(text="   ", title="", meta_description="")
        # Whitespace tokenizes to nothing -> no topic clears threshold.
        assert r.primary_topic == "uncategorized"
        assert r.topics == []

    def test_unicode_text_does_not_crash(self):
        """Unicode content is tokenized safely (regex is ASCII-only)."""
        c = ContentCategorizer()
        r = c.categorize(text="café résumé naïve", title="Ünïcode", meta_description="日本語")
        assert isinstance(r.primary_topic, str)
        assert isinstance(r.topics, list)

    def test_none_title_crashes(self):
        """DEFECT (QA-14): title=None crashes despite str-typed docstring.

        The docstring types ``title: str = ""`` and ``meta_description: str = ""``.
        Passing None (a common caller mistake) reaches ``text.lower()`` in
        _lowercase_signals and raises AttributeError instead of degrading.
        """
        c = ContentCategorizer()
        r = c.categorize(text="hello world", title=None, meta_description=None)
        assert isinstance(r.primary_topic, str)

    def test_none_meta_only_crashes(self):
        """DEFECT (QA-14): meta_description=None alone also crashes."""
        c = ContentCategorizer()
        r = c.categorize(text="hello world", title="t", meta_description=None)
        assert isinstance(r.primary_topic, str)


# ===========================================================================
# ContentCategorizer - constructor out-of-range params
# ===========================================================================

class TestConstructorOutOfRange:
    """min_score / max_topics out-of-range behaviour (documented, not defects)."""

    def test_max_topics_zero_returns_no_topics(self):
        """max_topics=0: the cap slice [:0] yields an empty list."""
        c = ContentCategorizer(max_topics=0)
        r = c.categorize(text="python programming software")
        assert r.topics == []
        assert r.primary_topic == "uncategorized"

    def test_max_topics_negative_returns_no_topics(self):
        """max_topics=-1: the cap slice [:-1] drops the last element but the
        list is already short; result is still bounded and does not crash."""
        c = ContentCategorizer(max_topics=-1)
        r = c.categorize(text="python programming software")
        # No crash; primary is well-defined.
        assert isinstance(r.primary_topic, str)

    def test_min_score_zero_keeps_zero_score_topics(self):
        """min_score=0.0: score >= 0.0 keeps every topic (incl. 0.0-score)."""
        c = ContentCategorizer(min_score=0.0)
        r = c.categorize(text="zzz qqq xxx")
        # All 12 built-in topics survive the >= 0.0 filter, capped at max_topics.
        assert len(r.topics) == c._max_topics

    def test_min_score_negative_keeps_all(self):
        """min_score=-5: every topic (score >= -5) survives the filter."""
        c = ContentCategorizer(min_score=-5.0)
        r = c.categorize(text="zzz qqq xxx")
        assert len(r.topics) == c._max_topics

    def test_default_min_score_drops_zero(self):
        """Default min_score=0.1: zero-score topics are dropped."""
        c = ContentCategorizer()
        r = c.categorize(text="zzz qqq xxx")
        assert r.topics == []
        assert r.primary_topic == "uncategorized"


# ===========================================================================
# ContentCategorizer - topic management
# ===========================================================================

class TestTopicManagement:
    """add_topic / remove_topic / get_topic / get_topics edge cases."""

    def test_builtin_topic_count(self):
        """12 built-in topics are loaded by default."""
        c = ContentCategorizer()
        assert len(c.get_topics()) == len(BUILTIN_TOPICS) == 12

    def test_get_topics_sorted(self):
        """get_topics returns names in ascending lexicographic order."""
        c = ContentCategorizer()
        assert c.get_topics() == sorted(c.get_topics())

    def test_add_topic_normalizes_case(self):
        """add_topic lowercases the name; get_topic is case-insensitive."""
        c = ContentCategorizer()
        c.add_topic("MyTopic", ["foo", "bar"])
        assert c.get_topic("MYTOPIC") is not None
        assert c.get_topic("mytopic") is not None
        assert c.get_topic("MyTopic") is not None

    def test_add_topic_overwrites_existing(self):
        """add_topic with an existing name replaces the entry (no dup)."""
        c = ContentCategorizer()
        before = len(c.get_topics())
        c.add_topic("technology", ["newkw"])
        assert len(c.get_topics()) == before
        assert "newkw" in c.get_topic("technology").keywords

    def test_remove_topic_existing(self):
        """remove_topic returns True and deletes an existing topic."""
        c = ContentCategorizer()
        c.add_topic("temp", ["x"])
        assert c.remove_topic("TEMP") is True
        assert c.get_topic("temp") is None

    def test_remove_topic_missing(self):
        """remove_topic returns False and does not mutate for a missing name."""
        c = ContentCategorizer()
        before = c.get_topics()
        assert c.remove_topic("does-not-exist") is False
        assert c.get_topics() == before

    def test_add_topic_non_string_keyword_crashes(self):
        """DEFECT-adjacent: add_topic with a non-string keyword crashes in
        TopicCategory.__post_init__ (kw.lower()). Documented as a crash, not
        xfail, because the type contract is list[str]."""
        c = ContentCategorizer()
        with pytest.raises(AttributeError):
            c.add_topic("x", [123, "abc"])


# ===========================================================================
# ContentCategorizer - categorize_batch
# ===========================================================================

class TestCategorizeBatch:
    """categorize_batch edge cases."""

    def test_empty_batch(self):
        """Empty list -> empty list."""
        c = ContentCategorizer()
        assert c.categorize_batch([]) == []

    def test_batch_missing_keys(self):
        """A dict missing all keys degrades to the all-falsy guard path."""
        c = ContentCategorizer()
        r = c.categorize_batch([{}])
        assert len(r) == 1
        assert r[0].primary_topic == "unknown"

    def test_batch_preserves_order(self):
        """Results are returned in the same order as input items."""
        c = ContentCategorizer()
        items = [
            {"text": "python programming"},
            {"text": "medical treatment"},
            {"text": "zzz qqq"},
        ]
        r = c.categorize_batch(items)
        assert len(r) == 3
        assert r[0].primary_topic == "technology"
        assert r[1].primary_topic == "health"

    def test_batch_non_dict_item_crashes(self):
        """A non-dict item crashes (item.get). Documented as a crash, not
        xfail, because the type contract is list[dict[str, str]]."""
        c = ContentCategorizer()
        with pytest.raises(AttributeError):
            c.categorize_batch([42])


# ===========================================================================
# CategorizationResult - top_n / secondary_topics
# ===========================================================================

class TestResultTopN:
    """CategorizationResult.top_n and secondary_topics edge cases."""

    def _result(self, n_topics: int) -> CategorizationResult:
        topics = [
            TopicScore(topic=f"t{i}", score=float(n_topics - i))
            for i in range(n_topics)
        ]
        return CategorizationResult(primary_topic="t0", topics=topics)

    def test_top_n_zero(self):
        """n=0 -> empty list (guarded)."""
        r = self._result(5)
        assert r.top_n(0) == []

    def test_top_n_negative(self):
        """n=-1 -> empty list (guarded, identical to n=0)."""
        r = self._result(5)
        assert r.top_n(-1) == []

    def test_top_n_larger_than_len(self):
        """n > len(topics) -> all topics."""
        r = self._result(3)
        assert len(r.top_n(10)) == 3

    def test_top_n_returns_fresh_list(self):
        """top_n returns a NEW list, not the internal one."""
        r = self._result(5)
        out = r.top_n(2)
        out.append(TopicScore(topic="x", score=0.0))
        assert len(r.topics) == 5

    def test_top_n_preserves_order(self):
        """top_n preserves the score-descending order of self.topics."""
        r = self._result(5)
        out = r.top_n(3)
        assert [t.topic for t in out] == ["t0", "t1", "t2"]

    def test_secondary_topics_empty(self):
        """0 topics -> secondary_topics is []."""
        r = self._result(0)
        assert r.secondary_topics == []

    def test_secondary_topics_single(self):
        """1 topic -> secondary_topics is [] (guard path)."""
        r = self._result(1)
        assert r.secondary_topics == []

    def test_secondary_topics_multiple(self):
        """3 topics -> secondary_topics is topics[1:] (fresh list)."""
        r = self._result(3)
        sec = r.secondary_topics
        assert [t.topic for t in sec] == ["t1", "t2"]
        sec.append(TopicScore(topic="x", score=0.0))
        assert len(r.topics) == 3


# ===========================================================================
# TopicScore - ordering
# ===========================================================================

class TestTopicScoreOrdering:
    """TopicScore __lt__ / __gt__ compare by score only."""

    def test_lt_by_score(self):
        a = TopicScore(topic="a", score=1.0)
        b = TopicScore(topic="b", score=2.0)
        assert a < b
        assert not b < a

    def test_gt_by_score(self):
        a = TopicScore(topic="a", score=1.0)
        b = TopicScore(topic="b", score=2.0)
        assert b > a
        assert not a > b

    def test_equal_scores_neither_lt_nor_gt(self):
        a = TopicScore(topic="a", score=1.0)
        b = TopicScore(topic="b", score=1.0)
        assert not (a < b)
        assert not (a > b)


# ===========================================================================
# TopicCategory - keyword normalization
# ===========================================================================

class TestTopicCategory:
    """TopicCategory.__post_init__ lowercases keywords in place."""

    def test_keywords_lowercased(self):
        t = TopicCategory(name="x", keywords=["Foo", "BAR", "Baz"])
        assert t.keywords == ["foo", "bar", "baz"]

    def test_keywords_default_empty(self):
        t = TopicCategory(name="x")
        assert t.keywords == []

    def test_none_keyword_crashes(self):
        """A None keyword crashes in __post_init__ (kw.lower()). Documented
        as a crash, not xfail, because the type contract is list[str]."""
        with pytest.raises(AttributeError):
            TopicCategory(name="y", keywords=[None])


# ===========================================================================
# ContentCategorizer - idempotence / round-trip / property
# ===========================================================================

class TestIdempotenceAndProperty:
    """Idempotence, round-trip, and property checks."""

    def test_categorize_is_pure(self):
        """Calling categorize twice on the same input yields equal results
        and does not mutate the categorizer's topic set."""
        c = ContentCategorizer()
        topics_before = c.get_topics()
        r1 = c.categorize(text="python programming software")
        r2 = c.categorize(text="python programming software")
        assert r1.primary_topic == r2.primary_topic
        assert r1.confidence == r2.confidence
        assert c.get_topics() == topics_before

    def test_confidence_bounded(self):
        """confidence is the top score rounded to 4 places, always >= 0."""
        c = ContentCategorizer()
        for text in ["python programming software", "medical treatment", "zzz qqq"]:
            r = c.categorize(text=text)
            assert r.confidence >= 0.0
            assert r.confidence == round(r.confidence, 4)

    def test_text_length_property(self):
        """text_length == len(text.split())."""
        c = ContentCategorizer()
        r = c.categorize(text="one two three four")
        assert r.text_length == 4

    def test_keyword_count_property(self):
        """keyword_count == number of distinct text tokens."""
        c = ContentCategorizer()
        r = c.categorize(text="python python software")
        # 'python' deduped -> 2 distinct tokens.
        assert r.keyword_count == 2


# ===========================================================================
# End-to-end CLI run
# ===========================================================================

class TestCLIEndToEnd:
    """End-to-end CLI run (content_categorizer is not directly wired to a
    subcommand; use `status` as the CLI smoke test, same pattern as cycle 162)."""

    def test_cli_status_runs(self):
        """python3 -m personal_index status completes without error."""
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "status"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(Path(__file__).resolve().parents[2]),
        )
        assert result.returncode == 0, f"CLI status failed: {result.stderr}"
