"""ARCH-15 VERIFY pin (cycle 193) — negative top_n guard on the Recommender.

ARCH-15 (IMPLEMENTED PR#1235@21acaa3, cycle 221) pins the guard that
`Recommender.recommend` and `Recommender.recommend_for_keywords` return `[]`
for `top_n <= 0` instead of leaking Python negative-slice semantics
(`candidates[:-1]` = all-but-last).

The implementer's pinning tests (tests/test_content_recommender.py) build pools
with only ONE surviving candidate, where `candidates[:-1]` is trivially empty —
so they pass even if the guard were removed. This file makes the guard
LOAD-BEARING: every negative/zero case uses >= 2 surviving candidates, so a
regression that drops the `if top_n <= 0: return []` line re-leaks
all-but-last and reopens the ticket. It also re-runs the guard end-to-end
through the installed `recommend` CLI (which passes `--top-n` straight into
`recommend_for_keywords`).
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner, Result

from personal_index.cli import main
from personal_index.content_recommender import ContentItem, Recommender
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _item(url: str, content: str = "python") -> ContentItem:
    return ContentItem(url=url, title="t", content=content)


def _pool_with_two_survivors() -> Recommender:
    """A pool where a query for 'python' yields >= 2 surviving candidates, so
    a missing guard would leak `candidates[:-1]` (all-but-last, non-empty)."""
    r = Recommender(min_score=0.0)
    r.add_item(_item("https://a.com/1", "python alpha"))
    r.add_item(_item("https://a.com/2", "python beta"))
    r.add_item(_item("https://a.com/3", "python gamma"))
    return r


def _seed_pool() -> tuple[Recommender, ContentItem]:
    """Seed + 2 other matching items -> 2 surviving candidates after the seed
    is excluded from its own recommendations."""
    seed = _item("https://a.com/seed", "python seed")
    r = Recommender(min_score=0.0)
    r.add_item(seed)
    r.add_item(_item("https://a.com/1", "python alpha"))
    r.add_item(_item("https://a.com/2", "python beta"))
    return r, seed


def _make_index(data_dir: str, pages: list[IndexedPage]) -> None:
    idx = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
    for p in pages:
        idx.add_page(p)


def _page(url: str, content: str) -> IndexedPage:
    return IndexedPage(url=url, title="t", content=content, score=1.0, keywords=[])


def _invoke(args: list[str], data_dir: str) -> "Result":
    runner = CliRunner()
    return runner.invoke(main, ["recommend", *args, "--data-dir", data_dir])


# ---------------------------------------------------------------------------
# Engine: recommend_for_keywords — guard is load-bearing (>= 2 candidates)
# ---------------------------------------------------------------------------
class TestRecommendForKeywordsNegativeTopN:
    def test_top_n_minus_one_returns_empty(self):
        # 3 candidates; without the guard candidates[:-1] -> 2 (leak).
        assert _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=-1) == []

    def test_top_n_zero_returns_empty(self):
        assert _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=0) == []

    def test_top_n_large_negative_returns_empty(self):
        assert _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=-5) == []

    def test_top_n_huge_negative_returns_empty(self):
        assert _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=-100) == []

    def test_top_n_minus_one_is_idempotent(self):
        r = _pool_with_two_survivors()
        assert r.recommend_for_keywords(["python"], top_n=-1) == []
        assert r.recommend_for_keywords(["python"], top_n=-1) == []

    @pytest.mark.parametrize("top_n", [-1, -2, -3, -10, -1000])
    def test_property_all_negative_top_n_empty(self, top_n):
        assert _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=top_n) == []

    def test_normal_path_unchanged_top_n_one(self):
        recs = _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=1)
        assert len(recs) == 1

    def test_normal_path_unchanged_top_n_two(self):
        recs = _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=2)
        assert len(recs) == 2

    def test_normal_path_larger_than_pool(self):
        recs = _pool_with_two_survivors().recommend_for_keywords(["python"], top_n=50)
        assert len(recs) == 3


# ---------------------------------------------------------------------------
# Engine: recommend (seed-based) — guard is load-bearing (2 candidates after
# the seed self-exclusion)
# ---------------------------------------------------------------------------
class TestRecommendNegativeTopN:
    def test_top_n_minus_one_returns_empty(self):
        r, seed = _seed_pool()
        # 2 surviving candidates; without the guard candidates[:-1] -> 1 (leak).
        assert r.recommend(seed, top_n=-1) == []

    def test_top_n_zero_returns_empty(self):
        r, seed = _seed_pool()
        assert r.recommend(seed, top_n=0) == []

    def test_top_n_large_negative_returns_empty(self):
        r, seed = _seed_pool()
        assert r.recommend(seed, top_n=-7) == []

    def test_normal_path_unchanged_top_n_one(self):
        r, seed = _seed_pool()
        recs = r.recommend(seed, top_n=1)
        assert len(recs) == 1
        assert all(rec.url != seed.url for rec in recs)

    def test_normal_path_unchanged_top_n_two(self):
        r, seed = _seed_pool()
        recs = r.recommend(seed, top_n=2)
        assert len(recs) == 2
        assert all(rec.url != seed.url for rec in recs)


# ---------------------------------------------------------------------------
# End-to-end: the installed `recommend` CLI passes --top-n straight into
# recommend_for_keywords, so a >= 2-match index makes the guard load-bearing.
# ---------------------------------------------------------------------------
class TestCliRecommendNegativeTopNEndToEnd:
    def _two_match_index(self, dd: str) -> None:
        _make_index(dd, [
            _page("https://a.com/1", "python alpha guide"),
            _page("https://a.com/2", "python beta guide"),
            _page("https://a.com/3", "python gamma guide"),
        ])

    def test_cli_top_n_minus_one_no_results(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        res = _invoke(["python", "--top-n", "-1"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_cli_top_n_zero_no_results(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        res = _invoke(["python", "--top-n", "0"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_cli_top_n_large_negative_no_results(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        res = _invoke(["python", "--top-n", "-5"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_cli_top_n_one_returns_exactly_one(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        res = _invoke(["python", "--top-n", "1"], dd)
        assert res.exit_code == 0
        assert "Top 1 Recommendations:" in res.output
        # exactly one numbered entry
        assert "\n1. " in res.output
        assert "\n2. " not in res.output

    def test_cli_top_n_two_returns_exactly_two(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        res = _invoke(["python", "--top-n", "2"], dd)
        assert res.exit_code == 0
        assert "Top 2 Recommendations:" in res.output
        assert "\n1. " in res.output
        assert "\n2. " in res.output
        assert "\n3. " not in res.output

    def test_cli_negative_top_n_is_idempotent(self, tmp_path):
        dd = str(tmp_path)
        self._two_match_index(dd)
        r1 = _invoke(["python", "--top-n", "-1"], dd)
        r2 = _invoke(["python", "--top-n", "-1"], dd)
        assert r1.output == r2.output
        assert "No recommendations found" in r1.output
