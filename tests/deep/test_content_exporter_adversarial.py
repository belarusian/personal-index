"""Adversarial deep tests for personal_index/content_exporter.py.

Cycle 286 — first deep-probe of ContentExporter (232 lines).

Targets the documented per-format escaping contract in ContentExporter.export:
  - HTML: every user field escaped with html.escape (& < > " ')
  - RSS:  title/description/link/guid escaped with xml.sax.saxutils.escape
          (only & < >, NOT quotes)
  - Markdown: backslash / [ ] ( ) escaped, newlines collapsed, link spaces %20
  - JSON:   verbatim via json.dumps
Plus: format normalization, unsupported-format ValueError, empty/None/malformed
items, unicode/encoding edges, oversized payloads, idempotency, error paths,
detect_format edge cases, and an end-to-end CLI run.

QA-48: ContentExporter._rss_item double-escapes the <guid> when an item has no
"id" field but has a "link" containing an XML-special character. link is
escaped once into the local `link` var, then xml_escape is applied AGAIN to that
already-escaped value as the guid fallback, so "a&b" -> "a&amp;b" ->
"a&amp;amp;b". An RSS reader would render the guid as "a&amp;b" instead of
"a&b". Pinned with xfail-strict below.
"""

from __future__ import annotations

import json
import re
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_exporter import ContentExporter


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def exporter():
    return ContentExporter(title="Test Index", base_url="http://example.com")


@pytest.fixture
def sample_items():
    return [
        {"id": "i-1", "title": "First", "description": "Hello", "link": "http://a.com", "tags": ["x", "y"]},
        {"id": "i-2", "title": "Second", "description": "World", "link": "", "tags": []},
    ]


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


# ---------------------------------------------------------------------------
# 1. Format normalization + unsupported format
# ---------------------------------------------------------------------------

class TestFormatNormalization:
    def test_padded_mixed_case_json(self, exporter, sample_items):
        """'JSON ' / ' Json' should normalize to json."""
        out = exporter.export(sample_items, " JSON ")
        assert json.loads(out) == sample_items

    def test_padded_mixed_case_html(self, exporter, sample_items):
        out = exporter.export(sample_items, " Html")
        assert "<!DOCTYPE html>" in out

    def test_padded_mixed_case_markdown(self, exporter, sample_items):
        out = exporter.export(sample_items, "MARKDOWN")
        assert out.startswith("#")

    def test_padded_mixed_case_rss(self, exporter, sample_items):
        out = exporter.export(sample_items, " rss ")
        assert out.startswith('<?xml')

    def test_unsupported_format_raises(self, exporter, sample_items):
        with pytest.raises(ValueError):
            exporter.export(sample_items, "yaml")

    def test_unsupported_format_empty_string(self, exporter, sample_items):
        with pytest.raises(ValueError):
            exporter.export(sample_items, "")

    def test_unsupported_format_whitespace_only(self, exporter, sample_items):
        with pytest.raises(ValueError):
            exporter.export(sample_items, "   ")


# ---------------------------------------------------------------------------
# 2. Empty / None / malformed items
# ---------------------------------------------------------------------------

class TestEmptyAndMalformedItems:
    def test_empty_list_json(self, exporter):
        out = exporter.export([], "json")
        assert json.loads(out) == []

    def test_empty_list_html(self, exporter):
        out = exporter.export([], "html")
        assert "<!DOCTYPE html>" in out
        assert "<article>" not in out

    def test_empty_list_markdown(self, exporter):
        out = exporter.export([], "markdown")
        assert out.startswith("#")

    def test_empty_list_rss(self, exporter):
        out = exporter.export([], "rss")
        assert "<channel>" in out
        assert "<item>" not in out

    def test_none_items_json(self, exporter):
        """export(None, 'json') serializes None via json.dumps -> 'null' (no raise)."""
        out = exporter.export(None, "json")
        assert out == "null"

    def test_item_missing_all_fields(self, exporter):
        """An empty dict item should render with defaults, not crash."""
        out = exporter.export([{}], "json")
        assert json.loads(out) == [{}]

    @pytest.mark.xfail(
        strict=True,
        reason="QA-48: explicit None field value crashes HTML export (html.escape(None) -> AttributeError)",
    )
    def test_item_none_values(self, exporter):
        """None field values should not crash any format. The docstring promises
        every user-supplied field is escaped with html.escape, but html.escape(None)
        raises AttributeError, so an item with title=None crashes HTML export."""
        item = {"id": None, "title": None, "description": None, "link": None, "tags": None}
        for fmt in ("json", "html", "markdown", "rss"):
            out = exporter.export([item], fmt)
            assert isinstance(out, str)

    def test_item_tags_as_string(self, exporter):
        """tags as a string (not list) should not crash; JSON stays verbatim."""
        item = {"id": "t1", "title": "T", "description": "D", "link": "", "tags": "not-a-list"}
        out = exporter.export([item], "json")
        assert json.loads(out)[0]["tags"] == "not-a-list"

    def test_item_non_dict_json(self, exporter):
        """A non-dict item in JSON is serialized verbatim by json.dumps (no raise)."""
        out = exporter.export(["not-a-dict"], "json")
        assert json.loads(out) == ["not-a-dict"]

    def test_item_extra_fields_preserved_json(self, exporter):
        item = {"id": "e1", "title": "T", "description": "D", "link": "", "tags": [], "custom": 42}
        out = exporter.export([item], "json")
        assert json.loads(out)[0]["custom"] == 42


# ---------------------------------------------------------------------------
# 3. HTML escaping contract (html.escape: & < > " ')
# ---------------------------------------------------------------------------

class TestHtmlEscaping:
    def test_html_title_escaped(self, exporter):
        item = {"id": "h1", "title": "<script>alert(1)</script>", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "html")
        assert "<script>" not in out
        assert "&lt;script&gt;" in out

    def test_html_description_escaped(self, exporter):
        item = {"id": "h2", "title": "T", "description": 'a & b < c > d " e \' f', "link": "", "tags": []}
        out = exporter.export([item], "html")
        assert "&amp;" in out
        assert "&lt;" in out
        assert "&gt;" in out
        assert "&quot;" in out

    def test_html_link_escaped_in_href(self, exporter):
        item = {"id": "h3", "title": "T", "description": "D", "link": 'http://x.com?a=1&b=2', "tags": []}
        out = exporter.export([item], "html")
        assert "a=1&amp;b=2" in out

    def test_html_tags_escaped(self, exporter):
        item = {"id": "h4", "title": "T", "description": "D", "link": "", "tags": ["<b>bold</b>"]}
        out = exporter.export([item], "html")
        assert "<b>bold</b>" not in out
        assert "&lt;b&gt;" in out

    def test_html_document_title_escaped(self):
        exp = ContentExporter(title="<evil> & \"x\"")
        out = exp.export([], "html")
        assert "<evil>" not in out
        assert "&lt;evil&gt;" in out


# ---------------------------------------------------------------------------
# 4. RSS escaping contract (xml_escape: only & < >, NOT quotes)
# ---------------------------------------------------------------------------

class TestRssEscaping:
    def test_rss_title_escaped(self, exporter):
        item = {"id": "r1", "title": "a & b < c > d", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "rss")
        assert "a &amp; b &lt; c &gt; d" in out

    def test_rss_quotes_not_escaped(self, exporter):
        """xml_escape does NOT escape quotes — document this contract."""
        item = {"id": "r2", "title": 'say "hi" and \'yo\'', "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "rss")
        # quotes pass through unescaped (contract: only & < > escaped)
        assert '"hi"' in out

    def test_rss_link_escaped(self, exporter):
        item = {"id": "r3", "title": "T", "description": "D", "link": "http://x.com?a=1&b=2", "tags": []}
        out = exporter.export([item], "rss")
        assert "a=1&amp;b=2" in out

    def test_rss_guid_uses_id_when_present(self, exporter):
        item = {"id": "x&y", "title": "T", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "rss")
        guid = re.search(r"<guid>(.*?)</guid>", out).group(1)
        assert guid == "x&amp;y"

    @pytest.mark.xfail(
        strict=True,
        reason="QA-48: RSS guid double-escaped when item has no id but link has &",
    )
    def test_rss_guid_fallback_single_escaped(self, exporter):
        """When an item has no 'id', guid falls back to the link. The link is
        already xml-escaped once, then escaped AGAIN for the guid, so 'a&b'
        becomes 'a&amp;amp;b' (double-escaped) instead of 'a&amp;b'."""
        item = {"title": "T", "description": "D", "link": "a&b", "tags": []}
        out = exporter.export([item], "rss")
        guid = re.search(r"<guid>(.*?)</guid>", out).group(1)
        assert guid == "a&amp;b"


# ---------------------------------------------------------------------------
# 5. Markdown escaping contract
# ---------------------------------------------------------------------------

class TestMarkdownEscaping:
    def test_md_title_brackets_escaped(self, exporter):
        item = {"id": "m1", "title": "a [b] (c)", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "markdown")
        assert "a \\[b\\] \\(c\\)" in out

    def test_md_newlines_collapsed(self, exporter):
        item = {"id": "m2", "title": "line1\nline2", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "markdown")
        assert "line1 line2" in out
        assert "line1\nline2" not in out

    def test_md_link_spaces_percent_encoded(self, exporter):
        item = {"id": "m3", "title": "T", "description": "D", "link": "http://x.com/a b/c", "tags": []}
        out = exporter.export([item], "markdown")
        assert "a%20b" in out

    def test_md_link_parens_escaped(self, exporter):
        item = {"id": "m4", "title": "T", "description": "D", "link": "http://x.com/(weird)", "tags": []}
        out = exporter.export([item], "markdown")
        assert "\\(weird\\)" in out

    def test_md_description_heading_guard(self, exporter):
        """A description starting with '#' must not become a heading."""
        item = {"id": "m5", "title": "T", "description": "# Not a heading", "link": "", "tags": []}
        out = exporter.export([item], "markdown")
        assert "\\# Not a heading" in out

    def test_md_backslash_escaped(self, exporter):
        item = {"id": "m6", "title": "back\\slash", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "markdown")
        assert "back\\\\slash" in out


# ---------------------------------------------------------------------------
# 6. Unicode / encoding edges
# ---------------------------------------------------------------------------

class TestUnicodeAndEncoding:
    def test_unicode_round_trip_json(self, exporter):
        item = {"id": "u1", "title": "日本語 🎉", "description": "café → naïve", "link": "", "tags": ["日本語"]}
        out = exporter.export([item], "json")
        data = json.loads(out)
        assert data[0]["title"] == "日本語 🎉"
        assert data[0]["description"] == "café → naïve"

    def test_unicode_html(self, exporter):
        item = {"id": "u2", "title": "日本語", "description": "café", "link": "", "tags": []}
        out = exporter.export([item], "html")
        assert "日本語" in out
        assert "café" in out

    def test_unicode_rss(self, exporter):
        item = {"id": "u3", "title": "العربية", "description": "D", "link": "", "tags": []}
        out = exporter.export([item], "rss")
        assert "العربية" in out

    def test_very_long_body(self, exporter):
        long_desc = "あ" * 100_000
        item = {"id": "u4", "title": "T", "description": long_desc, "link": "", "tags": []}
        out = exporter.export([item], "json")
        assert len(json.loads(out)[0]["description"]) == 100_000

    def test_null_byte_in_description(self, exporter):
        """A null byte should not corrupt JSON output."""
        item = {"id": "u5", "title": "T", "description": "before\x00after", "link": "", "tags": []}
        out = exporter.export([item], "json")
        data = json.loads(out)
        assert data[0]["description"] == "before\x00after"


# ---------------------------------------------------------------------------
# 7. Oversized payloads
# ---------------------------------------------------------------------------

class TestOversizedPayloads:
    def test_many_items(self, exporter):
        items = [{"id": f"r-{i:05d}", "title": f"T{i}", "description": f"D{i}", "link": "", "tags": []}
                 for i in range(10_000)]
        out = exporter.export(items, "json")
        assert len(json.loads(out)) == 10_000

    def test_single_huge_description(self, exporter):
        item = {"id": "big", "title": "T", "description": "x" * (1024 * 1024), "link": "", "tags": []}
        out = exporter.export([item], "json")
        assert len(json.loads(out)[0]["description"]) == 1024 * 1024


# ---------------------------------------------------------------------------
# 8. Idempotency
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_json_idempotent(self, exporter, sample_items):
        assert exporter.export(sample_items, "json") == exporter.export(sample_items, "json")

    def test_html_idempotent(self, exporter, sample_items):
        assert exporter.export(sample_items, "html") == exporter.export(sample_items, "html")

    def test_markdown_idempotent(self, exporter, sample_items):
        assert exporter.export(sample_items, "markdown") == exporter.export(sample_items, "markdown")

    def test_rss_structure_idempotent(self, exporter, sample_items):
        """RSS embeds a wall-clock lastBuildDate, so bytes differ; the item
        structure (everything except lastBuildDate) must be stable."""
        a = exporter.export(sample_items, "rss")
        b = exporter.export(sample_items, "rss")

        def strip(s: str) -> str:
            return re.sub(r"<lastBuildDate>.*?</lastBuildDate>", "", s)

        assert strip(a) == strip(b)


# ---------------------------------------------------------------------------
# 9. export_to_file + error paths
# ---------------------------------------------------------------------------

class TestExportToFile:
    def test_export_to_file_json(self, exporter, sample_items, tmp_dir):
        path = tmp_dir / "out.json"
        ret = exporter.export_to_file(sample_items, "json", str(path))
        assert ret == str(path)
        assert json.loads(path.read_text(encoding="utf-8")) == sample_items

    def test_export_to_file_nonexistent_dir(self, exporter, sample_items, tmp_dir):
        path = tmp_dir / "no" / "dir" / "out.json"
        with pytest.raises((OSError, FileNotFoundError)):
            exporter.export_to_file(sample_items, "json", str(path))

    def test_export_to_file_directory_path(self, exporter, sample_items, tmp_dir):
        d = tmp_dir / "isdir"
        d.mkdir()
        with pytest.raises((IsADirectoryError, OSError)):
            exporter.export_to_file(sample_items, "json", str(d))


# ---------------------------------------------------------------------------
# 10. detect_format edge cases
# ---------------------------------------------------------------------------

class TestDetectFormat:
    def test_known_extensions(self):
        assert ContentExporter.detect_format("a.html") == "html"
        assert ContentExporter.detect_format("a.htm") == "html"
        assert ContentExporter.detect_format("a.json") == "json"
        assert ContentExporter.detect_format("a.md") == "markdown"
        assert ContentExporter.detect_format("a.markdown") == "markdown"
        assert ContentExporter.detect_format("a.rss") == "rss"
        assert ContentExporter.detect_format("a.xml") == "rss"

    def test_uppercase_extension(self):
        assert ContentExporter.detect_format("a.HTML") == "html"
        assert ContentExporter.detect_format("a.JSON") == "json"

    def test_no_extension(self):
        assert ContentExporter.detect_format("noext") is None

    def test_trailing_dot(self):
        assert ContentExporter.detect_format("file.") is None

    def test_unknown_extension(self):
        assert ContentExporter.detect_format("a.yaml") is None

    def test_multiple_dots(self):
        assert ContentExporter.detect_format("archive.tar.gz") is None


# ---------------------------------------------------------------------------
# 11. End-to-end CLI run
# ---------------------------------------------------------------------------

class TestEndToEndCLI:
    def test_cli_smoke(self, tmp_dir):
        """A minimal CLI invocation should not crash (exit code 0 or a clean
        non-zero with no traceback)."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Usage" in result.output or "usage" in result.output.lower()
