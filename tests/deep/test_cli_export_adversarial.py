"""Adversarial deep tests for personal_index/cli_export.py (never-probed subsystem).

Cycle 280 (VALIDATOR). The module is a standalone click command `export_cmd`
plus private helpers `_load_pages` / `_dispatch_format` / `_tag_names` /
`_export_markdown` / `_export_json` / `_export_csv` / `_export_html`.

docs/cli_export.md is a precise "as-designed" spec that documents the CURRENT
behavior verbatim (title-only escaping in CSV/HTML, filter order
query -> tag -> limit, empty short-circuit, unknown-fmt -> markdown fallback).
These tests PIN that documented contract with adversarial inputs
(None/empty/whitespace/unicode/duplicate/out-of-range) plus one end-to-end
installed-CLI run through the `export_cmd` click command.

NOTE: `export_cmd` is NOT yet registered on the `main` group (ARCH-98 Option A
is an IMPL-lane change, not yet on main). The live `main export` is cli.py's
thinner duplicate. These tests therefore drive `export_cmd` directly via
click.testing.CliRunner (the command surface of THIS module), which is exactly
what docs/cli_export.md says is "untested" and what ARCH-98 will make reachable.
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from personal_index.cli_export import (
    export_cmd,
    _dispatch_format,
    _export_csv,
    _export_html,
    _export_json,
    _export_markdown,
    _load_pages,
    _tag_names,
)
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage
from personal_index.tags import Tag, TagStore


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

def _page(url, title="", content="", score=1.0, content_length=0):
    return IndexedPage(
        url=url,
        title=title,
        content=content,
        score=score,
        content_length=content_length or len(content),
    )


@pytest.fixture
def index(tmp_path):
    idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
    return idx


@pytest.fixture
def tag_store(tmp_path):
    return TagStore(store_path=str(tmp_path / "tags.json"))


@pytest.fixture
def populated(index, tag_store):
    """Three pages, two tagged, one untagged."""
    index.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
    index.add_page(_page("http://b.com", "Beta", "rust guide", score=1.5))
    index.add_page(_page("http://c.com", "Gamma", "python advanced", score=1.0))
    tag_store.add_tag_to_page("http://a.com", "python")
    tag_store.add_tag_to_page("http://c.com", "python")
    tag_store.add_tag_to_page("http://a.com", "tutorial")
    return index, tag_store


# ---------------------------------------------------------------------------
# _tag_names
# ---------------------------------------------------------------------------

class TestTagNames:
    def test_tag_objects(self):
        tags = [Tag(name="zeta"), Tag(name="alpha")]
        assert _tag_names(tags) == ["zeta", "alpha"]

    def test_strings(self):
        assert _tag_names(["x", "y"]) == ["x", "y"]

    def test_mixed(self):
        assert _tag_names([Tag(name="obj"), "plain"]) == ["obj", "plain"]

    def test_empty(self):
        assert _tag_names([]) == []

    def test_unicode_tag(self):
        assert _tag_names([Tag(name="café")]) == ["café"]

    def test_non_string_non_tag_coerced_via_str(self):
        # a tag without a .name attr falls through to str(t)
        class Weird:
            def __str__(self):
                return "weird"
        assert _tag_names([Weird()]) == ["weird"]


# ---------------------------------------------------------------------------
# _load_pages
# ---------------------------------------------------------------------------

class TestLoadPages:
    def test_no_filters_returns_all(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        assert {p.url for p in pages} == {"http://a.com", "http://b.com", "http://c.com"}

    def test_query_filter_is_set_intersection(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query="python", tag=(), limit=0)
        # only a.com and c.com contain "python"
        assert {p.url for p in pages} == {"http://a.com", "http://c.com"}

    def test_query_filter_preserves_list_pages_order(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query="python", tag=(), limit=0)
        urls = [p.url for p in pages]
        # list_pages order is insertion order: a, b, c -> filtered a, c
        assert urls == ["http://a.com", "http://c.com"]

    def test_query_no_match_returns_empty(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query="zzzznomatch", tag=(), limit=0)
        assert pages == []

    @pytest.mark.xfail(strict=True, reason="QA-44: --tag filter is a silent no-op (set[str] and set[Tag] always empty); implementer fix pending")
    def test_tag_filter_intersection(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=("python",), limit=0)
        assert {p.url for p in pages} == {"http://a.com", "http://c.com"}

    @pytest.mark.xfail(strict=True, reason="QA-44: --tag filter is a silent no-op (set[str] and set[Tag] always empty); implementer fix pending")
    def test_tag_filter_multiple_tags_any_match(self, populated):
        index, tag_store = populated
        # "tutorial" only on a.com; "python" on a.com + c.com -> union
        pages = _load_pages(index, tag_store, query=None, tag=("tutorial", "python"), limit=0)
        assert {p.url for p in pages} == {"http://a.com", "http://c.com"}

    def test_tag_filter_no_match(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=("nope",), limit=0)
        assert pages == []

    def test_limit_positive(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=2)
        assert len(pages) == 2

    def test_limit_zero_means_all(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        assert len(pages) == 3

    def test_limit_negative_is_noop_all(self, populated):
        # contract: `if limit > 0` -> negative limit is a no-op (all pages)
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=-5)
        assert len(pages) == 3

    def test_limit_larger_than_count(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=100)
        assert len(pages) == 3

    @pytest.mark.xfail(strict=True, reason="QA-44: --tag filter is a silent no-op (set[str] and set[Tag] always empty); implementer fix pending")
    def test_filter_order_query_then_tag_then_limit(self, populated):
        # query "python" -> {a,c}; tag "tutorial" -> {a}; limit 1 -> {a}
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query="python", tag=("tutorial",), limit=1)
        assert [p.url for p in pages] == ["http://a.com"]

    def test_empty_index(self, index, tag_store):
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        assert pages == []

    def test_query_empty_string_is_falsy_no_filter(self, populated):
        # `if query:` -> empty string is falsy, so no query filter applied
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query="", tag=(), limit=0)
        assert len(pages) == 3


# ---------------------------------------------------------------------------
# _dispatch_format
# ---------------------------------------------------------------------------

class TestDispatchFormat:
    def test_all_four_formats(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        for fmt in ("markdown", "json", "csv", "html"):
            out = _dispatch_format(fmt, pages, tag_store)
            assert isinstance(out, str)
            assert len(out) > 0

    def test_unknown_fmt_falls_back_to_markdown(self, populated):
        index, tag_store = populated
        pages = _load_pages(index, tag_store, query=None, tag=(), limit=0)
        out = _dispatch_format("bogus", pages, tag_store)
        md = _export_markdown(pages, tag_store)
        # fallback must be byte-identical to the markdown exporter
        assert out == md

    def test_empty_pages_all_formats(self, index, tag_store):
        for fmt in ("markdown", "json", "csv", "html"):
            out = _dispatch_format(fmt, [], tag_store)
            assert isinstance(out, str)


# ---------------------------------------------------------------------------
# _export_markdown
# ---------------------------------------------------------------------------

class TestExportMarkdown:
    def test_empty(self, index, tag_store):
        out = _export_markdown([], tag_store)
        assert "Total pages: 0" in out
        assert "# Personal Index Export" in out

    def test_single_page_fields(self, index, tag_store):
        p = _page("http://x.com", "My Title", "hello world", score=3.25)
        out = _export_markdown([p], tag_store)
        assert "## My Title" in out
        assert "http://x.com" in out
        assert "3.250" in out

    def test_empty_title_untitled(self, index, tag_store):
        p = _page("http://x.com", "", "body")
        out = _export_markdown([p], tag_store)
        assert "## Untitled" in out

    def test_none_title_untitled(self, index, tag_store):
        p = _page("http://x.com", None, "body")
        out = _export_markdown([p], tag_store)
        assert "## Untitled" in out

    def test_unicode_title_and_content(self, index, tag_store):
        p = _page("http://x.com", "Café résumé", "naïve façade")
        out = _export_markdown([p], tag_store)
        assert "Café résumé" in out
        assert "naïve façade" in out

    def test_content_snippet_truncated_at_300(self, index, tag_store):
        long_content = "x" * 500
        p = _page("http://x.com", "T", long_content)
        out = _export_markdown([p], tag_store)
        # snippet is content[:300] + "..."
        assert "x" * 300 in out
        assert "x" * 301 not in out
        assert "..." in out

    def test_content_exactly_300_no_ellipsis(self, index, tag_store):
        content = "y" * 300
        p = _page("http://x.com", "T", content)
        out = _export_markdown([p], tag_store)
        assert "y" * 300 in out
        # exactly 300 -> no "..." appended
        assert "y" * 300 + "..." not in out

    def test_content_empty_no_snippet_line(self, index, tag_store):
        p = _page("http://x.com", "T", "")
        out = _export_markdown([p], tag_store)
        # no content -> no snippet line; just the header/url/score
        assert "## T" in out

    def test_tags_rendered_sorted(self, index, tag_store):
        p = _page("http://x.com", "T", "body")
        tag_store.add_tag_to_page("http://x.com", "zeta")
        tag_store.add_tag_to_page("http://x.com", "alpha")
        out = _export_markdown([p], tag_store)
        assert "alpha, zeta" in out

    def test_score_zero_formats(self, index, tag_store):
        p = _page("http://x.com", "T", "body", score=0.0)
        out = _export_markdown([p], tag_store)
        assert "0.000" in out


# ---------------------------------------------------------------------------
# _export_json
# ---------------------------------------------------------------------------

class TestExportJson:
    def test_empty_is_empty_list(self, index, tag_store):
        out = _export_json([], tag_store)
        assert json.loads(out) == []

    def test_valid_json_round_trip(self, index, tag_store):
        p = _page("http://x.com", "Title", "body", score=1.5)
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["url"] == "http://x.com"
        assert data[0]["title"] == "Title"
        assert data[0]["score"] == 1.5

    def test_entry_has_documented_keys(self, index, tag_store):
        p = _page("http://x.com", "Title", "body", score=1.5)
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert set(data[0].keys()) == {
            "url", "title", "score", "content_length", "tags", "crawled_at",
        }

    def test_empty_title_becomes_empty_string(self, index, tag_store):
        p = _page("http://x.com", "", "body")
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert data[0]["title"] == ""

    def test_none_title_becomes_empty_string(self, index, tag_store):
        p = _page("http://x.com", None, "body")
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert data[0]["title"] == ""

    def test_unicode_round_trip(self, index, tag_store):
        p = _page("http://x.com", "Café", "naïve", score=1.0)
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert data[0]["title"] == "Café"

    def test_tags_included(self, index, tag_store):
        p = _page("http://x.com", "T", "body")
        tag_store.add_tag_to_page("http://x.com", "python")
        out = _export_json([p], tag_store)
        data = json.loads(out)
        assert data[0]["tags"] == ["python"]

    def test_multiple_pages(self, index, tag_store):
        pages = [_page(f"http://{i}.com", f"T{i}", "body") for i in range(5)]
        out = _export_json(pages, tag_store)
        data = json.loads(out)
        assert len(data) == 5


# ---------------------------------------------------------------------------
# _export_csv
# ---------------------------------------------------------------------------

class TestExportCsv:
    def test_empty_has_header_only(self, index, tag_store):
        out = _export_csv([], tag_store)
        lines = out.split("\n")
        assert lines[0] == "url,title,score,tags,content_length"
        assert len(lines) == 1

    def test_header(self, index, tag_store):
        out = _export_csv([_page("http://x.com", "T", "body")], tag_store)
        assert out.split("\n")[0] == "url,title,score,tags,content_length"

    def test_title_quote_escaped(self, index, tag_store):
        # a title containing a double-quote is escaped by doubling it
        p = _page("http://x.com", 'He said "hi"', "body")
        out = _export_csv([p], tag_store)
        assert '""hi""' in out

    def test_row_structure(self, index, tag_store):
        p = _page("http://x.com", "Title", "body", score=2.5)
        out = _export_csv([p], tag_store)
        lines = out.split("\n")
        row = lines[1]
        # url is quoted, title quoted, score unquoted, tags quoted, content_length unquoted
        assert row.startswith('"http://x.com",')
        assert '"Title"' in row
        assert "2.500" in row

    def test_tags_semicolon_joined(self, index, tag_store):
        p = _page("http://x.com", "T", "body")
        tag_store.add_tag_to_page("http://x.com", "b")
        tag_store.add_tag_to_page("http://x.com", "a")
        out = _export_csv([p], tag_store)
        assert '"a;b"' in out

    def test_unicode_title(self, index, tag_store):
        p = _page("http://x.com", "Café", "body")
        out = _export_csv([p], tag_store)
        assert "Café" in out

    def test_empty_title(self, index, tag_store):
        p = _page("http://x.com", "", "body")
        out = _export_csv([p], tag_store)
        lines = out.split("\n")
        # empty title -> empty quoted field
        assert '""' in lines[1]


# ---------------------------------------------------------------------------
# _export_html
# ---------------------------------------------------------------------------

class TestExportHtml:
    def test_empty_structure(self, index, tag_store):
        out = _export_html([], tag_store)
        assert "<!DOCTYPE html>" in out
        assert "Total pages: 0" in out
        assert "</table></body></html>" in out

    def test_title_angle_escaped(self, index, tag_store):
        p = _page("http://x.com", "A < B > C", "body")
        out = _export_html([p], tag_store)
        assert "A &lt; B &gt; C" in out
        # raw angle brackets must not appear in the title cell
        assert "A < B > C" not in out

    def test_table_header(self, index, tag_store):
        out = _export_html([_page("http://x.com", "T", "body")], tag_store)
        assert "<th>Title</th><th>URL</th><th>Score</th><th>Tags</th>" in out

    def test_row_contains_url_and_score(self, index, tag_store):
        p = _page("http://x.com", "T", "body", score=1.25)
        out = _export_html([p], tag_store)
        assert "http://x.com" in out
        assert "1.250" in out

    def test_empty_title_untitled(self, index, tag_store):
        p = _page("http://x.com", "", "body")
        out = _export_html([p], tag_store)
        assert "<td>Untitled</td>" in out

    def test_unicode_title(self, index, tag_store):
        p = _page("http://x.com", "Café", "body")
        out = _export_html([p], tag_store)
        assert "Café" in out

    def test_tags_comma_joined(self, index, tag_store):
        p = _page("http://x.com", "T", "body")
        tag_store.add_tag_to_page("http://x.com", "b")
        tag_store.add_tag_to_page("http://x.com", "a")
        out = _export_html([p], tag_store)
        assert "a, b" in out


# ---------------------------------------------------------------------------
# export_cmd end-to-end (installed click command surface)
# ---------------------------------------------------------------------------

class TestExportCmdE2E:
    def _run(self, tmp_path, args):
        runner = CliRunner()
        result = runner.invoke(export_cmd, args, obj={"data_dir": str(tmp_path)})
        return result

    def test_empty_index_no_pages(self, tmp_path):
        result = self._run(tmp_path, ["--format", "markdown"])
        assert result.exit_code == 0
        assert "No pages to export." in result.output

    def test_markdown_stdout(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        result = self._run(tmp_path, ["--format", "markdown"])
        assert result.exit_code == 0
        assert "# Personal Index Export" in result.output
        assert "Alpha" in result.output

    def test_json_stdout_valid(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        result = self._run(tmp_path, ["--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["url"] == "http://a.com"

    def test_csv_stdout(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        result = self._run(tmp_path, ["--format", "csv"])
        assert result.exit_code == 0
        assert result.output.split("\n")[0] == "url,title,score,tags,content_length"

    def test_html_stdout(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        result = self._run(tmp_path, ["--format", "html"])
        assert result.exit_code == 0
        assert "<!DOCTYPE html>" in result.output

    def test_output_file_written(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        out_file = tmp_path / "out.json"
        result = self._run(tmp_path, ["--format", "json", "-o", str(out_file)])
        assert result.exit_code == 0
        assert out_file.exists()
        data = json.loads(out_file.read_text(encoding="utf-8"))
        assert data[0]["url"] == "http://a.com"
        assert "Exported 1 pages to" in result.output

    @pytest.mark.xfail(strict=True, reason="QA-44: --tag filter is a silent no-op (set[str] and set[Tag] always empty); implementer fix pending")
    def test_tag_filter_e2e(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        ts = TagStore(store_path=str(tmp_path / "tags.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        idx.add_page(_page("http://b.com", "Beta", "rust guide", score=1.5))
        ts.add_tag_to_page("http://a.com", "python")
        result = self._run(tmp_path, ["--format", "json", "--tag", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert [d["url"] for d in data] == ["http://a.com"]

    def test_query_filter_e2e(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python tutorial", score=2.0))
        idx.add_page(_page("http://b.com", "Beta", "rust guide", score=1.5))
        result = self._run(tmp_path, ["--format", "json", "--query", "python"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert [d["url"] for d in data] == ["http://a.com"]

    def test_limit_e2e(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        for i in range(5):
            idx.add_page(_page(f"http://{i}.com", f"T{i}", "body", score=1.0))
        result = self._run(tmp_path, ["--format", "json", "--limit", "2"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 2

    def test_invalid_format_rejected_by_click(self, tmp_path):
        # click.Choice validates; "bogus" is not a valid choice
        result = self._run(tmp_path, ["--format", "bogus"])
        assert result.exit_code != 0

    def test_unicode_round_trip_e2e(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://x.com", "Café résumé", "naïve façade", score=1.0))
        result = self._run(tmp_path, ["--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["title"] == "Café résumé"

    def test_duplicate_urls_deduped(self, tmp_path):
        # SearchIndex stores by url key -> adding the same url twice keeps one
        idx = SearchIndex(db_path=str(tmp_path / "search_index.json"))
        idx.add_page(_page("http://a.com", "Alpha", "python", score=2.0))
        idx.add_page(_page("http://a.com", "Alpha2", "python", score=3.0))
        result = self._run(tmp_path, ["--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
