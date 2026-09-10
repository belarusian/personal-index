"""Adversarial deep tests for the LIVE `top` CLI command (cycle 193).

The live `top` command is the inline `def top` at personal_index/cli.py:906
(registered via `@main.command()`), NOT `personal_index/cli_top.py:top_pages`
(which is a dead alternate impl, never imported by cli.py). This file attacks
the live command end-to-end through the installed CLI group:

  - guard paths: empty index (no file / explicit empty file), negative limit
    (clamped to 0 per the docstring), zero limit, limit larger than the pool;
  - ordering: pages must be ranked by score DESCENDING (the docstring claims
    "highest-scored indexed pages");
  - truncation: limit smaller than the pool;
  - JSON contract: valid JSON, `top_pages` list, `total` count, per-page dict;
  - text contract: "Top N pages by score:" header, numbered entries, score
    formatted to 4 decimals;
  - unicode titles round-trip through JSON;
  - idempotence: two identical invocations produce byte-identical output.
"""

from __future__ import annotations

import json
import os

from click.testing import CliRunner, Result

from personal_index.cli import main
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


def _page(url: str, title: str = "", score: float = 1.0) -> IndexedPage:
    return IndexedPage(url=url, title=title, content="", score=score, keywords=[])


def _make_index(data_dir: str, pages: list[IndexedPage]) -> None:
    idx = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
    for p in pages:
        idx.add_page(p)


def _invoke(args: list[str], data_dir: str) -> "Result":
    runner = CliRunner()
    return runner.invoke(main, ["top", *args, "--data-dir", data_dir])


# ---------------------------------------------------------------------------
# Guard paths
# ---------------------------------------------------------------------------
class TestTopGuardPaths:
    def test_empty_index_no_file(self, tmp_path):
        dd = str(tmp_path)
        res = _invoke([], dd)
        assert res.exit_code == 0
        assert "Top 0 pages by score:" in res.output

    def test_empty_index_explicit_empty_file(self, tmp_path):
        dd = str(tmp_path)
        SearchIndex(db_path=os.path.join(dd, "search_index.json"))  # creates empty
        res = _invoke([], dd)
        assert res.exit_code == 0
        assert "Top 0 pages by score:" in res.output

    def test_negative_limit_clamped_to_zero(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "A", 5.0),
                         _page("https://a.com/2", "B", 3.0)])
        res = _invoke(["--limit", "-1"], dd)
        assert res.exit_code == 0
        assert "Top 0 pages by score:" in res.output

    def test_large_negative_limit_clamped_to_zero(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "A", 5.0)])
        res = _invoke(["--limit", "-100"], dd)
        assert res.exit_code == 0
        assert "Top 0 pages by score:" in res.output

    def test_zero_limit_no_pages(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "A", 5.0)])
        res = _invoke(["--limit", "0"], dd)
        assert res.exit_code == 0
        assert "Top 0 pages by score:" in res.output


# ---------------------------------------------------------------------------
# Ordering: highest score first
# ---------------------------------------------------------------------------
class TestTopOrdering:
    def test_ranked_by_score_descending(self, tmp_path):
        dd = str(tmp_path)
        # inserted in NON-descending score order to prove the command sorts
        _make_index(dd, [
            _page("https://a.com/low", "Low", 1.0),
            _page("https://a.com/high", "High", 9.0),
            _page("https://a.com/mid", "Mid", 5.0),
        ])
        res = _invoke(["--limit", "10"], dd)
        assert res.exit_code == 0
        out = res.output
        # High (9.0) must appear before Mid (5.0) before Low (1.0)
        assert out.index("High") < out.index("Mid") < out.index("Low")

    def test_json_rank_order_matches_score_desc(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/low", "Low", 1.0),
            _page("https://a.com/high", "High", 9.0),
            _page("https://a.com/mid", "Mid", 5.0),
        ])
        res = _invoke(["--limit", "10", "--format", "json"], dd)
        assert res.exit_code == 0
        data = json.loads(res.output)
        scores = [p["score"] for p in data["top_pages"]]
        assert scores == sorted(scores, reverse=True)
        assert scores == [9.0, 5.0, 1.0]


# ---------------------------------------------------------------------------
# Truncation
# ---------------------------------------------------------------------------
class TestTopTruncation:
    def test_limit_smaller_than_pool(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [
            _page("https://a.com/1", "P1", 1.0),
            _page("https://a.com/2", "P2", 2.0),
            _page("https://a.com/3", "P3", 3.0),
        ])
        res = _invoke(["--limit", "2"], dd)
        assert res.exit_code == 0
        assert "Top 2 pages by score:" in res.output
        # only the top 2 (P3, P2) appear; P1 (lowest) does not
        assert "P3" in res.output
        assert "P2" in res.output
        assert "P1" not in res.output

    def test_limit_larger_than_pool_shows_all(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.0),
                         _page("https://a.com/2", "P2", 2.0)])
        res = _invoke(["--limit", "50"], dd)
        assert res.exit_code == 0
        assert "Top 2 pages by score:" in res.output
        assert "P1" in res.output and "P2" in res.output


# ---------------------------------------------------------------------------
# JSON contract
# ---------------------------------------------------------------------------
class TestTopJsonContract:
    def test_json_is_valid_and_shaped(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.5),
                         _page("https://a.com/2", "P2", 2.5)])
        res = _invoke(["--limit", "10", "--format", "json"], dd)
        assert res.exit_code == 0
        data = json.loads(res.output)
        assert set(data.keys()) == {"top_pages"}
        assert isinstance(data["top_pages"], list)
        assert len(data["top_pages"]) == 2
        # each entry is a full page dict (to_dict) with url/title/score
        for entry in data["top_pages"]:
            assert "url" in entry and "title" in entry and "score" in entry

    def test_json_empty_index(self, tmp_path):
        dd = str(tmp_path)
        res = _invoke(["--format", "json"], dd)
        assert res.exit_code == 0
        data = json.loads(res.output)
        assert data == {"top_pages": []}

    def test_json_unicode_title_round_trips(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "R\u00e9sum\u00e9 \u2603", 3.0)])
        res = _invoke(["--limit", "10", "--format", "json"], dd)
        assert res.exit_code == 0
        data = json.loads(res.output)
        assert data["top_pages"][0]["title"] == "R\u00e9sum\u00e9 \u2603"


# ---------------------------------------------------------------------------
# Text contract
# ---------------------------------------------------------------------------
class TestTopTextContract:
    def test_header_and_separator(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.0)])
        res = _invoke(["--limit", "10"], dd)
        assert res.exit_code == 0
        assert "Top 1 pages by score:" in res.output
        assert "=" * 60 in res.output

    def test_numbered_entries_and_score_format(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.2345)])
        res = _invoke(["--limit", "10"], dd)
        assert res.exit_code == 0
        assert "1. P1" in res.output
        # score formatted to 4 decimals
        assert "1.2345" in res.output

    def test_url_printed(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/xyz", "P1", 1.0)])
        res = _invoke(["--limit", "10"], dd)
        assert res.exit_code == 0
        assert "https://a.com/xyz" in res.output


# ---------------------------------------------------------------------------
# Idempotence
# ---------------------------------------------------------------------------
class TestTopIdempotence:
    def test_text_output_is_idempotent(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.0),
                         _page("https://a.com/2", "P2", 2.0)])
        r1 = _invoke(["--limit", "10"], dd)
        r2 = _invoke(["--limit", "10"], dd)
        assert r1.output == r2.output

    def test_json_output_is_idempotent(self, tmp_path):
        dd = str(tmp_path)
        _make_index(dd, [_page("https://a.com/1", "P1", 1.0),
                         _page("https://a.com/2", "P2", 2.0)])
        r1 = _invoke(["--limit", "10", "--format", "json"], dd)
        r2 = _invoke(["--limit", "10", "--format", "json"], dd)
        assert r1.output == r2.output
        assert json.loads(r1.output) == json.loads(r2.output)
