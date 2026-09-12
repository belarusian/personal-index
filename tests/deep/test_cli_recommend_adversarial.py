"""Adversarial deep tests for personal_index.cli_recommend + content_recommender.

Cycle 192 (VALIDATOR). The `recommend` CLI command is registered on the main
group (personal_index/cli.py:1511 `main.add_command(recommend)`), so this is a
live CLI entry point - the end-to-end path is a real `personal-index recommend`
run through the installed CLI group.

The command advertises three weight options:
    --keyword-weight  "Keyword overlap weight"
    --tag-weight      "Tag similarity weight"
    --score-weight    "Score weight"
but the function body only consumes `query`, `top_n`, `data_dir` and calls
`Recommender.recommend_for_keywords(keywords, top_n)` - a method that does NOT
accept weights. The three options are therefore accepted and silently ignored.
Pinned xfail-strict below as QA-24 (defect: advertised option does nothing).

The rest of the file is armor: guard inputs (empty index / no query /
whitespace / unicode / out-of-range top_n), output formatting, ordering,
truncation, idempotence, and the engine's documented weight behavior on the
seed-based `recommend` path (which DOES honor weights).
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner, Result

from personal_index.cli import main
from personal_index.content_recommender import (
    ContentItem,
    Recommendation,
    Recommender,
)
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


def _make_index(data_dir: str, pages: list[IndexedPage]) -> None:
    """Persist a SearchIndex with the given pages under data_dir."""
    idx = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
    for p in pages:
        idx.add_page(p)


def _page(url: str, title: str = "", content: str = "", score: float = 1.0,
          keywords: list | None = None) -> IndexedPage:
    return IndexedPage(url=url, title=title, content=content, score=score,
                       keywords=keywords or [])


def _invoke(args: list[str], data_dir: str) -> "Result":
    runner = CliRunner()
    return runner.invoke(main, ["recommend", *args, "--data-dir", data_dir])


# ---------------------------------------------------------------------------
# Guard paths (empty index / no query / whitespace / unicode / out-of-range)
# ---------------------------------------------------------------------------
class TestCliRecommendGuardPaths:
    def test_empty_index_no_file(self, tmp_path):
        dd = str(tmp_path)
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "No indexed content found" in res.output

    def test_empty_index_explicit_empty_file(self, tmp_path):
        dd = str(tmp_path)
        SearchIndex(db_path=os.path.join(dd, "search_index.json"))  # creates empty
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "No indexed content found" in res.output

    def test_no_query_empty_keywords(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke([], dd)  # no query argument
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_whitespace_only_query(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["   "], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_query_no_matches(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["zzzqqq"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_top_n_negative(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--top-n", "-1"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_top_n_zero(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--top-n", "0"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_unicode_query_no_match(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["\u00e9\u00e8\u00ea"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output

    def test_unicode_content_ascii_query_matches(self, tmp_path):
        # Accented chars are stripped by the [a-z0-9]+ extractor, so an ASCII
        # query word still matches content that also contains unicode.
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "R\u00e9sum\u00e9 guide",
                               "r\u00e9sum\u00e9 python tips")])
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "R\u00e9sum\u00e9 guide" in res.output

    def test_pure_unicode_query_word_no_match(self, tmp_path):
        # A query word made only of accented chars is stripped to nothing by
        # the [a-z0-9]+ extractor and cannot match (armor: pins the regex).
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "R\u00e9sum\u00e9 guide",
                               "r\u00e9sum\u00e9 tips")])
        res = _invoke(["r\u00e9sum\u00e9"], dd)
        assert res.exit_code == 0
        assert "No recommendations found" in res.output


# ---------------------------------------------------------------------------
# Output formatting / ordering / truncation
# ---------------------------------------------------------------------------
class TestCliRecommendOutput:
    def test_normal_query_prints_recommendations(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python guide", "python basics"),
            _page("https://a.com/2", "Python advanced", "python advanced"),
        ])
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "Top 5 Recommendations:" in res.output
        assert "Python guide" in res.output
        assert "Python advanced" in res.output

    def test_output_header_and_separator(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python"], dd)
        assert "Top 5 Recommendations:" in res.output
        assert "=" * 50 in res.output

    def test_output_score_format(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python"], dd)
        # single query keyword matched by one item -> fraction 1.0 -> "1.000"
        assert "Score: 1.000" in res.output

    def test_output_reason_format(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python"], dd)
        assert "matched keywords: python" in res.output

    def test_top_n_truncates(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python one", "python a"),
            _page("https://a.com/2", "Python two", "python b"),
            _page("https://a.com/3", "Python three", "python c"),
        ])
        res = _invoke(["python", "--top-n", "2"], dd)
        assert res.exit_code == 0
        assert "Top 2 Recommendations:" in res.output
        # exactly two numbered entries
        assert "\n1. " in res.output
        assert "\n2. " in res.output
        assert "\n3. " not in res.output

    def test_top_n_larger_than_results(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--top-n", "50"], dd)
        assert res.exit_code == 0
        assert "Top 50 Recommendations:" in res.output
        assert "Python guide" in res.output

    def test_ordering_by_score_desc(self, tmp_path):
        dd = str(tmp_path)
        # "High" matches 2/2 query keywords (score 1.0); "Low" matches 1/2 (0.5)
        _make_index(dd, [
            _page("https://a.com/2", "Low", "python python"),
            _page("https://a.com/1", "High", "python java"),
        ])
        res = _invoke(["python java"], dd)
        assert res.exit_code == 0
        pos_high = res.output.index("High")
        pos_low = res.output.index("Low")
        assert pos_high < pos_low

    def test_idempotence_same_run(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        r1 = _invoke(["python"], dd)
        r2 = _invoke(["python"], dd)
        assert r1.output == r2.output


# ---------------------------------------------------------------------------
# DEFECT: advertised weight options are accepted but never used (QA-24)
# ---------------------------------------------------------------------------
class TestCliRecommendWeightsDefect:
    def test_weight_options_are_accepted(self, tmp_path):
        """The options parse without error (they exist on the command)."""
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python", "--keyword-weight", "0.5",
                       "--tag-weight", "0.2", "--score-weight", "0.3"], dd)
        assert res.exit_code == 0

    def test_cli_recommend_weights_affect_output(self, tmp_path):
        """Contract implied by the advertised options: different weights must
        change the recommendation output. They do not - the options are dead."""
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python guide", "python basics", score=5.0),
            _page("https://a.com/2", "Python advanced", "python advanced", score=8.0),
        ])
        r0 = _invoke(["python", "--keyword-weight", "0.0",
                      "--tag-weight", "0.0", "--score-weight", "0.0"], dd)
        r1 = _invoke(["python", "--keyword-weight", "1.0",
                      "--tag-weight", "1.0", "--score-weight", "1.0"], dd)
        assert r0.exit_code == 0 and r1.exit_code == 0
        assert r0.output != r1.output


# ---------------------------------------------------------------------------
# Engine armor: Recommender (seed path honors weights; keyword path documented)
# ---------------------------------------------------------------------------
class TestRecommenderEngine:
    def test_recommend_empty_pool(self):
        assert Recommender().recommend(ContentItem(url="u", title="t")) == []

    def test_recommend_for_keywords_empty_pool(self):
        assert Recommender().recommend_for_keywords(["a"]) == []

    def test_recommend_for_keywords_empty_keywords(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python"))
        assert r.recommend_for_keywords([]) == []

    def test_recommend_for_keywords_whitespace_keywords(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python"))
        assert r.recommend_for_keywords(["  ", ""]) == []

    def test_recommend_for_keywords_top_n_negative(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python"))
        assert r.recommend_for_keywords(["python"], top_n=-1) == []

    def test_recommend_for_keywords_top_n_zero(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python"))
        assert r.recommend_for_keywords(["python"], top_n=0) == []

    def test_recommend_for_keywords_query_lowercased(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python basics"))
        recs = r.recommend_for_keywords(["PYTHON"])
        assert len(recs) == 1
        assert recs[0].matching_keywords == ["python"]

    def test_recommend_for_keywords_explicit_case_sensitive(self):
        # explicit keywords are matched case-sensitively (only content/title
        # derived keywords are lowercased) -> "Python" != query "python"
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="", keywords=["Python"]))
        assert r.recommend_for_keywords(["python"]) == []

    def test_recommend_for_keywords_fraction_score(self):
        r = Recommender()
        r.add_item(ContentItem(url="u", title="t", content="python java"))
        recs = r.recommend_for_keywords(["python", "java", "go"])
        assert len(recs) == 1
        assert recs[0].score == pytest.approx(2 / 3)

    def test_recommend_for_keywords_min_score_drop(self):
        r = Recommender(min_score=0.9)
        r.add_item(ContentItem(url="u", title="t", content="python java"))
        # 2/3 = 0.667 < 0.9 -> dropped
        assert r.recommend_for_keywords(["python", "java", "go"]) == []

    def test_recommend_seed_excludes_self(self):
        r = Recommender()
        seed = ContentItem(url="https://a.com/1", title="t", content="python")
        r.add_item(seed)
        r.add_item(ContentItem(url="https://a.com/2", title="t", content="python"))
        recs = r.recommend(seed)
        assert all(rec.url != "https://a.com/1" for rec in recs)

    def test_recommend_top_n_negative(self):
        r = Recommender()
        seed = ContentItem(url="https://a.com/1", title="t", content="python")
        r.add_item(seed)
        r.add_item(ContentItem(url="https://a.com/2", title="t", content="python"))
        assert r.recommend(seed, top_n=-1) == []

    def test_recommend_honors_weights(self):
        """The seed-based recommend() DOES honor the weight arguments (armor:
        distinguishes the live weight path from the dead CLI weight options)."""
        seed = ContentItem(url="https://a.com/1", title="t", content="python")
        other = ContentItem(url="https://a.com/2", title="t", content="python",
                            score=10.0)
        r = Recommender(min_score=0.0)
        r.add_item(seed)
        r.add_item(other)
        # score_weight 0.0 -> norm contributes nothing; 1.0 -> norm=1.0 adds 1.0
        recs0 = r.recommend(seed, keyword_weight=0.0, tag_weight=0.0, score_weight=0.0)
        recs1 = r.recommend(seed, keyword_weight=0.0, tag_weight=0.0, score_weight=1.0)
        assert recs0[0].score != recs1[0].score

    def test_recommendation_to_dict(self):
        rec = Recommendation(url="u", title="t", score=0.12345, reason="r",
                             matching_keywords=["a"], matching_tags=["b"])
        d = rec.to_dict()
        assert d == {"url": "u", "title": "t", "score": 0.1235, "reason": "r",
                     "matching_keywords": ["a"], "matching_tags": ["b"]}

    def test_clear_and_item_count(self):
        r = Recommender()
        r.add_item(ContentItem(url="u1", title="t"))
        r.add_item(ContentItem(url="u2", title="t"))
        assert r.item_count == 2
        r.clear()
        assert r.item_count == 0


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed CLI group)
# ---------------------------------------------------------------------------
class TestCliRecommendEndToEnd:
    def test_end_to_end_full_run(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "Python guide", "python basics", score=5.0),
            _page("https://a.com/2", "Java guide", "java basics", score=6.0),
        ])
        res = _invoke(["python", "--top-n", "1"], dd)
        assert res.exit_code == 0
        assert "Top 1 Recommendations:" in res.output
        assert "Python guide" in res.output
        assert "Java guide" not in res.output

    def test_data_dir_flag_is_respected(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "Python guide", "python basics")])
        res = _invoke(["python"], dd)
        assert res.exit_code == 0
        assert "Python guide" in res.output
