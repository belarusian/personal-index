"""Cycle 160 PROBE: personal_index/results.py (never-probed subsystem).

Adversarial deep tests for the search-results formatting/export layer:
  - ResultsFormatter.create_snippet  (windowing bound)
  - ResultsFormatter.format_result / format_results
  - ResultsExporter.to_json / to_csv / to_markdown  (round-trips)
  - one end-to-end run through the installed CLI (import -> search)

Guard inputs: None/empty/whitespace/unicode/duplicate/out-of-range,
round-trips, idempotence, property checks.

DEFECT FILED (QA-6): create_snippet with a NEGATIVE max_length produces
garbage ('...' when the query is found, '' when not) instead of a sane
bounded snippet. Out-of-range (negative) max_length is a caller error that
should be clamped to a non-negative bound (matching the 0 behaviour), not
produce a lone ellipsis. Pinned xfail-strict so the suite stays green while
the defect exists; flips to a hard pass once guarded.
"""

from __future__ import annotations

import csv
import io
import json
import os
import subprocess
import sys

import pytest

from personal_index.results import (
    ResultsExporter,
    ResultsFormatter,
    SearchResult,
)


def _mk(rank=1, url="http://a.com", title="T", score=0.5,
        snippet="s", interests=None, meta="") -> SearchResult:
    return SearchResult(
        rank=rank, url=url, title=title, score=score, snippet=snippet,
        matched_interests=interests or [], meta_description=meta,
    )


class TestCreateSnippetGuards:
    """Guard inputs for create_snippet (clean armor)."""

    def test_empty_text_returns_empty(self):
        assert ResultsFormatter().create_snippet("", "q") == ""

    def test_whitespace_text_returns_unchanged(self):
        # No query match -> text[:max+50]; whitespace is returned as-is.
        assert ResultsFormatter().create_snippet("   ", "q") == "   "

    def test_none_text_returns_empty(self):
        # create_snippet(None, ...) -> `not text` short-circuits to "".
        assert ResultsFormatter().create_snippet(None, "q") == ""  # type: ignore[arg-type]

    def test_query_not_found_returns_prefix(self):
        # No match -> text[:max_length + 50] (default 200 -> whole short text).
        assert ResultsFormatter().create_snippet("hello world", "zzz") == "hello world"

    def test_query_at_start_no_leading_ellipsis(self):
        out = ResultsFormatter().create_snippet("world hello", "world")
        assert not out.startswith("...")

    def test_query_at_end_no_trailing_ellipsis(self):
        out = ResultsFormatter().create_snippet("hello world", "world")
        assert not out.endswith("...")

    def test_query_in_middle_has_both_ellipses(self):
        # Small max_length so the window is strictly inside the text -> both
        # ellipses. (With the default 200 the window reaches the end, so only
        # the leading ellipsis appears.)
        text = "a" * 60 + "NEEDLE" + "b" * 60
        out = ResultsFormatter().create_snippet(text, "needle", 10)
        assert out.startswith("...")
        assert out.endswith("...")
        assert "NEEDLE" in out

    def test_case_insensitive_match(self):
        out = ResultsFormatter().create_snippet("Hello World", "WORLD")
        assert "World" in out

    def test_unicode_roundtrip(self):
        out = ResultsFormatter().create_snippet("héllo wörld", "wörld")
        assert "wörld" in out

    def test_empty_query_returns_prefix(self):
        # Empty query -> find("") == 0 -> treated as found at index 0.
        assert ResultsFormatter().create_snippet("hello world", "") == "hello world"

    def test_max_length_zero_is_sane(self):
        # max_length=0 -> end = idx+len(query) reaches the text end here, so
        # the whole short text is returned; the point is it is SANE (no lone
        # ellipsis, query present) - contrast with the negative-bound defect.
        out = ResultsFormatter().create_snippet("hello world", "world", 0)
        assert out != "..."
        assert "world" in out


class TestCreateSnippetNegativeMaxLength:
    """QA-6: negative max_length is out-of-range and must not produce garbage."""

    @pytest.mark.xfail(
        strict=True,
        reason="QA-6: create_snippet(max_length=-100) returns '...' garbage "
               "instead of a sane bounded snippet (negative bound unguarded)",
    )
    def test_negative_max_length_found_is_sane(self):
        # Expected contract: a negative bound is clamped to a non-negative
        # bound (like 0), yielding the query window, never a lone '...'.
        out = ResultsFormatter().create_snippet("hello world", "world", -100)
        assert out != "..."
        assert "world" in out

    @pytest.mark.xfail(
        strict=True,
        reason="QA-6: create_snippet(max_length=-100) with no match returns '' "
               "instead of the text prefix (negative bound unguarded)",
    )
    def test_negative_max_length_notfound_is_sane(self):
        # Expected contract: no-match path should return text[:max+50]; with a
        # clamped non-negative bound that is the text prefix, not ''.
        out = ResultsFormatter().create_snippet("hello world", "zzz", -100)
        assert out != ""
        assert "hello" in out


class TestFormatResultGuards:
    """format_result / format_results guard inputs (clean armor)."""

    def test_format_result_empty_fields(self):
        out = ResultsFormatter().format_result(_mk(url="", title="", score=0.0, snippet=""))
        assert "[1]" in out
        assert "URL:" in out
        assert "Score: 0.00" in out

    def test_format_result_omits_empty_snippet(self):
        out = ResultsFormatter().format_result(_mk(snippet=""))
        # snippet line only appears when snippet is truthy
        assert "    s" not in out

    def test_format_result_includes_interests(self):
        out = ResultsFormatter().format_result(_mk(interests=["x", "y"]))
        assert "Interests: x, y" in out

    def test_format_results_empty_list(self):
        assert ResultsFormatter().format_results([]) == "No results found."

    def test_format_results_separators(self):
        out = ResultsFormatter().format_results([_mk(rank=1), _mk(rank=2)])
        assert out.count("-" * 60) == 2

    def test_score_two_decimal_format(self):
        out = ResultsFormatter().format_result(_mk(score=1.234567))
        assert "Score: 1.23" in out


class TestExporterRoundTrips:
    """to_json / to_csv / to_markdown round-trips and guards (clean armor)."""

    def test_json_roundtrip(self):
        rs = [
            _mk(rank=1, url="http://a.com", title="T1", score=0.5,
                snippet="s", interests=["x", "y"]),
            _mk(rank=2, url="http://b.com", title="T2", score=0.7),
        ]
        back = json.loads(ResultsExporter.to_json(rs))
        assert len(back) == 2
        assert back[0]["url"] == "http://a.com"
        assert back[0]["interests"] == ["x", "y"]
        assert back[1]["score"] == 0.7

    def test_json_empty(self):
        assert json.loads(ResultsExporter.to_json([])) == []

    def test_json_unicode(self):
        back = json.loads(ResultsExporter.to_json([_mk(title="héllo", snippet="wörld")]))
        assert back[0]["title"] == "héllo"
        assert back[0]["snippet"] == "wörld"

    def test_csv_roundtrip(self):
        rs = [_mk(rank=1, interests=["x", "y"]), _mk(rank=2)]
        rows = list(csv.reader(io.StringIO(ResultsExporter.to_csv(rs))))
        assert rows[0] == ["rank", "url", "title", "score", "snippet", "interests"]
        assert rows[1][5] == "x;y"
        assert rows[2][5] == ""

    def test_csv_empty_has_header_only(self):
        rows = list(csv.reader(io.StringIO(ResultsExporter.to_csv([]))))
        assert len(rows) == 1
        assert rows[0][0] == "rank"

    def test_markdown_contains_titles(self):
        rs = [_mk(rank=1, title="T1"), _mk(rank=2, title="T2")]
        md = ResultsExporter.to_markdown(rs)
        assert "T1" in md and "T2" in md

    def test_markdown_empty(self):
        assert ResultsExporter.to_markdown([]) == ""

    def test_markdown_omits_empty_snippet(self):
        md = ResultsExporter.to_markdown([_mk(snippet="")])
        # snippet line omitted when empty
        assert "s" not in md


class TestIdempotenceAndProperties:
    """Idempotence and property checks (clean armor)."""

    def test_format_result_idempotent(self):
        f = ResultsFormatter()
        r = _mk(interests=["a"])
        assert f.format_result(r) == f.format_result(r)

    def test_export_json_idempotent(self):
        rs = [_mk(), _mk(rank=2)]
        assert ResultsExporter.to_json(rs) == ResultsExporter.to_json(rs)

    def test_snippet_length_bounded_by_max(self):
        # Property: snippet never exceeds (max_length + 100) chars for a
        # mid-text match (50 before + 50 after + ellipses).
        text = "x" * 500 + "NEEDLE" + "y" * 500
        out = ResultsFormatter().create_snippet(text, "needle", 20)
        assert len(out) <= 20 + 100 + 2

    def test_snippet_always_contains_query_when_found(self):
        text = "prefix " + "target" + " suffix"
        out = ResultsFormatter().create_snippet(text, "target")
        assert "target" in out


class TestCliEndToEnd:
    """One end-to-end run through the installed CLI (import -> search)."""

    def test_cli_import_then_search(self, tmp_path):
        page = tmp_path / "page.html"
        page.write_text(
            "<html><head><title>Python Tutorial</title></head>"
            "<body>Learn python programming today</body></html>",
            encoding="utf-8",
        )
        data_dir = str(tmp_path / "data")
        env = dict(os.environ)

        imp = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "import", str(page)],
            capture_output=True, text=True, env=env,
        )
        assert imp.returncode == 0, imp.stderr
        assert "Import complete" in imp.stdout

        srch = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "search", "python"],
            capture_output=True, text=True, env=env,
        )
        assert srch.returncode == 0, srch.stderr
        assert "Search results for 'python'" in srch.stdout
        assert "Python Tutorial" in srch.stdout

    def test_cli_search_empty_index(self, tmp_path):
        data_dir = str(tmp_path / "data")
        env = dict(os.environ)
        srch = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "search", "python"],
            capture_output=True, text=True, env=env,
        )
        assert srch.returncode == 0, srch.stderr
        assert "No indexed content found" in srch.stdout
