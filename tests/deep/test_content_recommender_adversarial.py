"""Adversarial deep tests for personal_index.content_recommender (LIVE `recommend` CLI).

Cycle 271 PROBE: content_recommender is the engine behind the live `recommend`
CLI command (cli.py:1511 -> cli_recommend.py -> Recommender) and had NO deep
test. Attacks: negative/zero top_n (the "top N" negative-slice class — confirm
BOTH clamps), empty pool, empty/whitespace/unicode/duplicate query, score
ordering, min_score filtering, seed exclusion, the documented case-sensitivity
contract, and an end-to-end CLI run.
"""

from __future__ import annotations

import pytest

from personal_index.content_recommender import (
    ContentItem,
    Recommender,
    _extract_keywords,
)


def _item(url, title="", content="", keywords=None, tags=None, score=0.0):
    return ContentItem(
        url=url,
        title=title,
        content=content,
        keywords=keywords or [],
        tags=tags or [],
        score=score,
    )


class TestTopNNegativeSliceClass:
    """The 'top N' negative-slice class: confirm BOTH clamps (floor + cap)."""

    def test_recommend_negative_top_n_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python programming"))
        r.add_item(_item("b", content="python scripting"))
        seed = _item("seed", content="python")
        assert r.recommend(seed, top_n=-3) == []

    def test_recommend_for_keywords_negative_top_n_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python programming"))
        assert r.recommend_for_keywords(["python"], top_n=-1) == []

    def test_recommend_zero_top_n_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python programming"))
        seed = _item("seed", content="python")
        assert r.recommend(seed, top_n=0) == []

    def test_recommend_for_keywords_zero_top_n_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python programming"))
        assert r.recommend_for_keywords(["python"], top_n=0) == []

    def test_recommend_positive_top_n_truncates(self):
        r = Recommender(min_score=0.0)
        for i in range(5):
            r.add_item(_item(f"u{i}", content=f"python topic{i}"))
        seed = _item("seed", content="python")
        recs = r.recommend(seed, top_n=2)
        assert len(recs) == 2

    def test_recommend_for_keywords_positive_top_n_truncates(self):
        r = Recommender(min_score=0.0)
        for i in range(5):
            r.add_item(_item(f"u{i}", content=f"python topic{i}"))
        recs = r.recommend_for_keywords(["python"], top_n=3)
        assert len(recs) == 3


class TestEmptyPoolAndQuery:
    def test_recommend_empty_pool_returns_empty(self):
        r = Recommender(min_score=0.0)
        seed = _item("seed", content="python")
        assert r.recommend(seed) == []

    def test_recommend_for_keywords_empty_pool_returns_empty(self):
        r = Recommender(min_score=0.0)
        assert r.recommend_for_keywords(["python"]) == []

    def test_recommend_for_keywords_empty_list_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        assert r.recommend_for_keywords([]) == []

    def test_recommend_for_keywords_all_empty_strings_returns_empty(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        assert r.recommend_for_keywords(["", ""]) == []

    def test_recommend_for_keywords_whitespace_only_returns_empty(self):
        # whitespace is truthy so it enters keyword_set, but item keywords
        # (from [a-z0-9]+) never contain whitespace -> no match.
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        assert r.recommend_for_keywords(["   "]) == []

    def test_recommend_for_keywords_unicode_query_no_crash(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        # unicode query that does not match -> empty, no exception
        assert r.recommend_for_keywords(["\u043f\u0438\u0442\u043e\u043d"]) == []


class TestQueryNormalization:
    def test_duplicate_query_keywords_collapsed(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        # duplicates collapse to one keyword -> fraction 1/1 = 1.0
        recs = r.recommend_for_keywords(["python", "python"])
        assert len(recs) == 1
        assert recs[0].score == pytest.approx(1.0)

    def test_query_keywords_lowercased(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        recs = r.recommend_for_keywords(["PYTHON"])
        assert len(recs) == 1
        assert recs[0].score == pytest.approx(1.0)

    def test_explicit_item_keywords_case_sensitive(self):
        # Documented contract: explicit item keywords are matched
        # case-sensitively (only content/title-derived are lowercased).
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", keywords=["Python"]))  # capital P, explicit
        # query lowercased to "python" -> no match against explicit "Python"
        assert r.recommend_for_keywords(["python"]) == []

    def test_content_derived_keywords_lowercased(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="PYTHON"))  # content-derived -> lowercased
        recs = r.recommend_for_keywords(["python"])
        assert len(recs) == 1


class TestScoringAndOrdering:
    def test_scores_sorted_descending(self):
        r = Recommender(min_score=0.0)
        # item a matches 2 of 2 query kws, item b matches 1 of 2
        r.add_item(_item("a", content="python java"))
        r.add_item(_item("b", content="python"))
        recs = r.recommend_for_keywords(["python", "java"])
        scores = [x.score for x in recs]
        assert scores == sorted(scores, reverse=True)
        assert recs[0].url == "a"

    def test_min_score_filters_low_matches(self):
        r = Recommender(min_score=0.5)
        r.add_item(_item("a", content="python"))       # 1/2 = 0.5 -> kept
        r.add_item(_item("b", content="python java"))  # 2/2 = 1.0 -> kept
        r.add_item(_item("c", content="java"))         # 1/2 = 0.5 -> kept
        recs = r.recommend_for_keywords(["python", "java"])
        urls = {x.url for x in recs}
        assert urls == {"a", "b", "c"}

    def test_min_score_drops_below_threshold(self):
        r = Recommender(min_score=0.9)
        r.add_item(_item("a", content="python"))  # 1/2 = 0.5 < 0.9 -> dropped
        r.add_item(_item("b", content="python java"))  # 1.0 -> kept
        recs = r.recommend_for_keywords(["python", "java"])
        assert [x.url for x in recs] == ["b"]

    def test_recommend_seed_excluded_by_url(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("seed", content="python"))
        r.add_item(_item("other", content="python"))
        seed = _item("seed", content="python")
        recs = r.recommend(seed)
        assert all(x.url != "seed" for x in recs)
        assert [x.url for x in recs] == ["other"]

    def test_recommend_score_based_reason_when_no_overlap(self):
        # seed has no overlap with item, but item has a positive score
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="unrelated", score=10.0))
        seed = _item("seed", content="zzz")
        recs = r.recommend(seed, score_weight=1.0)
        assert len(recs) == 1
        assert recs[0].reason == "score-based"


class TestWeightedPath:
    def test_weighted_path_uses_weights(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python", score=10.0))
        # kw_score=1.0, norm=min(10/10,1)=1.0 -> 1.0*0.6 + 1.0*0.1 = 0.7
        recs = r.recommend_for_keywords(
            ["python"], keyword_weight=0.6, score_weight=0.1
        )
        assert recs[0].score == pytest.approx(0.7)

    def test_weighted_path_tag_weight_no_effect(self):
        # tag_weight is accepted but has no effect on the keyword path
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python", tags=["x"]))
        base = r.recommend_for_keywords(["python"], keyword_weight=0.6)
        with_tag = r.recommend_for_keywords(
            ["python"], keyword_weight=0.6, tag_weight=0.9
        )
        assert base[0].score == pytest.approx(with_tag[0].score)

    def test_weighted_path_negative_score_norm_zero(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python", score=-5.0))
        # norm = 0.0 for negative score -> score = 1.0*0.6 + 0 = 0.6
        recs = r.recommend_for_keywords(["python"], keyword_weight=0.6)
        assert recs[0].score == pytest.approx(0.6)


class TestIdempotenceAndClear:
    def test_clear_resets_pool(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        assert r.item_count == 1
        r.clear()
        assert r.item_count == 0
        assert r.recommend_for_keywords(["python"]) == []

    def test_recommend_idempotent(self):
        r = Recommender(min_score=0.0)
        r.add_item(_item("a", content="python"))
        r.add_item(_item("b", content="python"))
        seed = _item("seed", content="python")
        first = [x.url for x in r.recommend(seed)]
        second = [x.url for x in r.recommend(seed)]
        assert first == second


class TestExtractKeywords:
    def test_empty_text(self):
        assert _extract_keywords("") == set()

    def test_stopwords_removed(self):
        assert _extract_keywords("the and of") == set()

    def test_short_words_removed(self):
        # len(w) > 2 required
        assert _extract_keywords("go in") == set()

    def test_unicode_ignored(self):
        # [a-z0-9]+ only -> unicode yields no ascii keywords
        assert _extract_keywords("\u043f\u0438\u0442\u043e\u043d") == set()


class TestEndToEndCLI:
    @staticmethod
    def _page(url, title, content):
        from personal_index.models import IndexedPage
        return IndexedPage(
            url=url, title=title, content=content,
            score=1.0, indexed_at="2024-01-01T00:00:00",
            source_interest="test", word_count=len(content.split()),
        )

    def test_recommend_cli_end_to_end(self, tmp_path):
        """End-to-end: seed a data dir, run `personal-index recommend`."""
        from click.testing import CliRunner
        from personal_index.cli import main
        from personal_index.index import SearchIndex

        dd = str(tmp_path)
        idx = SearchIndex(db_path=f"{dd}/search_index.json")
        idx.add_page(self._page("http://a", "Python Guide", "python programming tutorial"))
        idx.add_page(self._page("http://b", "Java Guide", "java programming tutorial"))

        runner = CliRunner(isolate_filesystem=False)
        res = runner.invoke(
            main, ["recommend", "python", "--data-dir", dd, "--top-n", "5"]
        )
        assert res.exit_code == 0, res.output
        assert "Python Guide" in res.output
        # Java page should not be recommended for query "python"
        assert "Java Guide" not in res.output

    def test_recommend_cli_empty_index(self, tmp_path):
        from click.testing import CliRunner
        from personal_index.cli import main
        from personal_index.index import SearchIndex

        dd = str(tmp_path)
        SearchIndex(db_path=f"{dd}/search_index.json")

        runner = CliRunner(isolate_filesystem=False)
        res = runner.invoke(main, ["recommend", "python", "--data-dir", dd])
        assert res.exit_code == 0, res.output
        assert "No indexed content found" in res.output

    def test_recommend_cli_negative_top_n(self, tmp_path):
        from click.testing import CliRunner
        from personal_index.cli import main
        from personal_index.index import SearchIndex

        dd = str(tmp_path)
        idx = SearchIndex(db_path=f"{dd}/search_index.json")
        idx.add_page(self._page("http://a", "Python Guide", "python programming"))

        runner = CliRunner(isolate_filesystem=False)
        res = runner.invoke(
            main, ["recommend", "python", "--data-dir", dd, "--top-n", "-3"]
        )
        assert res.exit_code == 0, res.output
        # negative top_n -> no recommendations
        assert "No recommendations found" in res.output
