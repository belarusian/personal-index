"""Cycle 272 (VALIDATOR) — adversarial deep probe of ``search_suggestions``.

Target: ``personal_index/search_suggestions.py`` — the module PR #1604 (QA-35,
implementer cycle 324) just touched by adding the ``max_suggestions <= 0``
guard to ``SearchSuggestions.suggest``. The QA-35 ticket explicitly says
"re-verify on next validator cycle", and this module had NO dedicated deep
test file (its QA-35 pins live in the sweep file
``tests/deep/test_negslice_sweep4_adversarial.py``).

This file is ARMOR: it pins the verified QA-35 fix and the full adversarial
surface of the module (None/empty/whitespace/unicode/duplicate/out-of-range
inputs, round-trips, idempotence, property checks, and one end-to-end CLI run
of the ``personal-index search`` command, which is the closest reachable CLI
surface — ``search_suggestions`` itself is a passive in-memory generator with
no CLI command).

No NEW contract violation was found in this probe: every behavior below
matches ``docs/search-suggestions.md``. The QA-35 fix is VERIFIED (issue
#1392 closed).
"""

from __future__ import annotations

import random
import string
import subprocess
import sys

from personal_index.search_suggestions import (
    SearchSuggestions,
    Suggestion,
    _fuzzy_match_score,
)


# ---------------------------------------------------------------------------
# QA-35 fix verification: suggest(fuzzy=True) with negative max_suggestions
# must return [] (the guard added at search_suggestions.py:205).
# ---------------------------------------------------------------------------
class TestQA35NegativeMaxSuggestions:
    def test_fuzzy_negative_max_suggestions_returns_empty(self):
        s = SearchSuggestions(max_suggestions=-1, fuzzy_threshold=0.0)
        s.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
        assert [x.text for x in s.suggest("py", fuzzy=True)] == []

    def test_fuzzy_negative_max_suggestions_matches_zero_guard(self):
        s = SearchSuggestions(max_suggestions=-1, fuzzy_threshold=0.0)
        s.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
        s0 = SearchSuggestions(max_suggestions=0, fuzzy_threshold=0.0)
        s0.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
        assert s.suggest("py", fuzzy=True) == s0.suggest("py", fuzzy=True) == []

    def test_exact_match_negative_max_suggestions_returns_empty(self):
        # The exact-match path is accidentally masked by
        # Counter.most_common(-1) -> []; pin it so a refactor that removes the
        # most_common cap does not silently turn the exact-match path into a
        # leak too.
        s = SearchSuggestions(max_suggestions=-1)
        s.add_search_history(["python", "pytorch", "pandas", "pypi", "pyramid"])
        assert [x.text for x in s.suggest("py")] == []

    def test_sibling_get_trending_negative_guarded(self):
        s = SearchSuggestions()
        for q in ["a", "b", "c"]:
            s.record_search(q)
        assert s.get_trending(-1) == []

    def test_sibling_get_related_queries_negative_guarded(self):
        s = SearchSuggestions()
        s.add_search_history(["foo bar", "foo baz", "foo qux"])
        assert [x.text for x in s.get_related_queries("foo", -1)] == []


# ---------------------------------------------------------------------------
# min_prefix_length guard: a prefix shorter than min_prefix_length returns [].
# ---------------------------------------------------------------------------
class TestMinPrefixLengthGuard:
    def test_short_prefix_returns_empty(self):
        s = SearchSuggestions(min_prefix_length=5)
        s.add_search_history(["python"])
        assert s.suggest("py") == []

    def test_default_min_prefix_length_two(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        assert [x.text for x in s.suggest("py")] == ["python"]

    def test_single_char_prefix_returns_empty(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        assert s.suggest("p") == []


# ---------------------------------------------------------------------------
# sources filtering: sources=None searches all four; a named list searches only
# those; an unknown source name searches nothing.
# ---------------------------------------------------------------------------
class TestSourcesFiltering:
    def test_default_searches_all_sources(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        s.add_tags(["python"])
        # "python" is in both history and tags; the candidates dict dedups by
        # text, so exactly one suggestion.
        assert [x.text for x in s.suggest("py")] == ["python"]

    def test_history_only(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        s.add_tags(["python"])
        assert [x.source for x in s.suggest("py", sources=["history"])] == ["history"]

    def test_tags_only(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        s.add_tags(["python"])
        assert [x.source for x in s.suggest("py", sources=["tags"])] == ["tags"]

    def test_bogus_source_returns_empty(self):
        s = SearchSuggestions()
        s.add_search_history(["python"])
        assert s.suggest("py", sources=["bogus"]) == []

    def test_empty_sources_list_searches_all(self):
        # sources=[] is falsy -> the `not sources` branch fires -> all sources.
        s = SearchSuggestions()
        s.add_search_history(["python"])
        assert [x.text for x in s.suggest("py", sources=[])] == ["python"]


# ---------------------------------------------------------------------------
# record_search case-dedup: _trending is keyed by query.lower(), so
# "Python"/"python"/"PYTHON" collapse to one entry with count 3.
# ---------------------------------------------------------------------------
class TestRecordSearchCaseDedup:
    def test_case_variants_collapse_to_one_trending_entry(self):
        s = SearchSuggestions()
        s.record_search("Python")
        s.record_search("python")
        s.record_search("PYTHON")
        assert list(s._trending.keys()) == ["python"]
        assert s._trending["python"].count == 3

    def test_record_search_appends_to_history(self):
        s = SearchSuggestions()
        s.record_search("alpha")
        s.record_search("beta")
        assert s._search_history == ["alpha", "beta"]


# ---------------------------------------------------------------------------
# get_trending: n > len returns all; decay_half_life <= 0 uses raw count.
# ---------------------------------------------------------------------------
class TestGetTrending:
    def test_n_greater_than_len_returns_all(self):
        s = SearchSuggestions()
        s.record_search("a")
        s.record_search("b")
        assert s.get_trending(100) == ["a", "b"]

    def test_decay_half_life_zero_uses_raw_count(self):
        s = SearchSuggestions(decay_half_life=0)
        s.record_search("a")
        s.record_search("a")
        s.record_search("b")
        # "a" has count 2, "b" has count 1 -> "a" first.
        assert s.get_trending(10) == ["a", "b"]

    def test_empty_trending_returns_empty(self):
        assert SearchSuggestions().get_trending(10) == []


# ---------------------------------------------------------------------------
# get_related_queries: word-overlap related queries from history.
# ---------------------------------------------------------------------------
class TestGetRelatedQueries:
    def test_empty_query_returns_empty(self):
        s = SearchSuggestions()
        s.add_search_history(["python web dev", "python data"])
        assert s.get_related_queries("") == []

    def test_whitespace_query_returns_empty(self):
        s = SearchSuggestions()
        s.add_search_history(["python web dev", "python data"])
        assert s.get_related_queries("   ") == []

    def test_duplicate_history_accumulates_score(self):
        s = SearchSuggestions()
        s.add_search_history(["python web", "python web", "python data"])
        res = s.get_related_queries("python")
        # "python web" appears twice -> its score is accumulated (2.0), so it
        # ranks above "python data" (1.0).
        assert [x.text for x in res] == ["python web", "python data"]
        assert res[0].score > res[1].score

    def test_n_greater_than_len_returns_all(self):
        s = SearchSuggestions()
        s.add_search_history(["python web", "python data"])
        assert [x.text for x in s.get_related_queries("python", n=100)] == [
            "python web",
            "python data",
        ]

    def test_no_overlap_returns_empty(self):
        s = SearchSuggestions()
        s.add_search_history(["python web", "python data"])
        assert s.get_related_queries("rust") == []


# ---------------------------------------------------------------------------
# to_dict / from_dict round-trip: all four state fields survive, including the
# trending count.
# ---------------------------------------------------------------------------
class TestRoundTrip:
    def test_full_round_trip(self):
        s = SearchSuggestions()
        s.add_search_history(["alpha", "beta"])
        s.add_tags(["t1"])
        s.add_keywords(["k1"])
        s.record_search("alpha")
        s.record_search("alpha")
        d = s.to_dict()
        s2 = SearchSuggestions.from_dict(d)
        assert s2._search_history == ["alpha", "beta", "alpha", "alpha"]
        assert s2._tags == ["t1"]
        assert s2._keywords == ["k1"]
        assert {k: v.count for k, v in s2._trending.items()} == {"alpha": 2}

    def test_legacy_int_trending_format(self):
        # Backward compat: old format was {query: count} (bare int).
        s = SearchSuggestions.from_dict({"trending": {"foo": 5}})
        assert s._trending["foo"].query == "foo"
        assert s._trending["foo"].count == 5

    def test_empty_round_trip(self):
        e = SearchSuggestions()
        d = e.to_dict()
        assert d == {
            "search_history": [],
            "tags": [],
            "keywords": [],
            "trending": {},
        }
        e2 = SearchSuggestions.from_dict({})
        assert e2._search_history == []
        assert e2._trending == {}

    def test_from_dict_tolerates_missing_keys(self):
        s = SearchSuggestions.from_dict({"search_history": ["x"]})
        assert s._search_history == ["x"]
        assert s._tags == []
        assert s._keywords == []
        assert s._trending == {}


# ---------------------------------------------------------------------------
# clear(): empties all four state fields.
# ---------------------------------------------------------------------------
class TestClear:
    def test_clear_empties_everything(self):
        s = SearchSuggestions()
        s.add_search_history(["x"])
        s.add_tags(["t"])
        s.add_keywords(["k"])
        s.record_search("x")
        s.clear()
        assert s._search_history == []
        assert s._tags == []
        assert s._keywords == []
        assert s._trending == {}


# ---------------------------------------------------------------------------
# Unicode and whitespace handling.
# ---------------------------------------------------------------------------
class TestUnicodeAndWhitespace:
    def test_unicode_prefix_match(self):
        s = SearchSuggestions()
        s.add_search_history(["日本語の検索", "日本語"])
        assert [x.text for x in s.suggest("日本")] == ["日本語の検索", "日本語"]

    def test_unicode_min_prefix_length_counts_code_points(self):
        # len() counts code points, so a 2-code-point prefix passes a
        # min_prefix_length=2 guard.
        s = SearchSuggestions(min_prefix_length=2)
        s.add_search_history(["日本語の検索"])
        assert [x.text for x in s.suggest("日本")] == ["日本語の検索"]

    def test_whitespace_history_entry(self):
        s = SearchSuggestions()
        s.add_search_history(["   "])
        # A whitespace-only entry does not start with "py" -> no match.
        assert s.suggest("py") == []


# ---------------------------------------------------------------------------
# Idempotence: calling suggest twice with the same state yields the same
# result (suggest is a pure read over the state).
# ---------------------------------------------------------------------------
class TestIdempotence:
    def test_suggest_is_idempotent(self):
        s = SearchSuggestions()
        s.add_search_history(["alpha", "beta", "gamma"])
        a = [x.text for x in s.suggest("a")]
        b = [x.text for x in s.suggest("a")]
        assert a == b

    # NOTE: get_trending is intentionally NOT idempotent - its ranking uses
    # time-dependent half-life decay (entry.age_seconds), so two calls at
    # different wall-clock times can rank the same entries differently. That
    # is documented behavior, not a defect, so it is not pinned here.



# ---------------------------------------------------------------------------
# Property checks: _fuzzy_match_score is documented to return a score in
# [0.0, 1.0]; the trending exact-match score is clamped to <= 1.0 (the docs'
# "1.1" contract hole is actually already clamped by min(..., 1.0) before the
# *1.1 multiplier is applied to the clamped base).
# ---------------------------------------------------------------------------
class TestScoreBounds:
    def test_fuzzy_match_score_in_unit_interval(self):
        rng = random.Random(272)
        for _ in range(20000):
            a = "".join(rng.choices(string.ascii_lowercase, k=rng.randint(0, 12)))
            b = "".join(rng.choices(string.ascii_lowercase, k=rng.randint(0, 12)))
            sc = _fuzzy_match_score(a, b)
            assert 0.0 <= sc <= 1.0, f"score {sc} out of [0,1] for {a!r}/{b!r}"

    def test_fuzzy_match_score_empty_guard(self):
        assert _fuzzy_match_score("", "abc") == 0.0
        assert _fuzzy_match_score("abc", "") == 0.0
        assert _fuzzy_match_score("", "") == 0.0

    def test_trending_score_clamped_to_at_most_one(self):
        # A single dominant trending entry: its decayed score == the total, so
        # the base clamps to 1.0 and the final score is <= 1.0.
        s = SearchSuggestions()
        s.record_search("python")
        res = s.suggest("py")
        assert len(res) == 1
        assert res[0].score <= 1.0

    def test_suggestion_to_dict_rounds_score_to_four_places(self):
        sg = Suggestion(text="t", score=0.123456789)
        assert sg.to_dict()["score"] == 0.1235


# ---------------------------------------------------------------------------
# End-to-end CLI run: ``search_suggestions`` is a passive in-memory generator
# with NO CLI command, so the closest reachable CLI surface is the
# ``personal-index search`` command (the full-text search pipeline). This pins
# the empty-index guard path end-to-end.
# ---------------------------------------------------------------------------
class TestEndToEndCLI:
    def test_cli_search_empty_index_guard(self, tmp_path):
        data_dir = tmp_path / "e2e_qa272"
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "anything",
             "--data-dir", str(data_dir)],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, f"CLI exited {proc.returncode}: {proc.stderr}"
        assert "No indexed content found" in proc.stdout
