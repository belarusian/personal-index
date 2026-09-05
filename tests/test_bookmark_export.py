"""Tests for the bookmark_export module."""

from __future__ import annotations

import json
import os
from xml.etree import ElementTree as ET

import pytest

from personal_index.bookmark_export import (
    BookmarkExporter,
    BookmarkExportResult,
)
from personal_index.bookmarks import Bookmark

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_bookmarks():
    """Return a list of sample Bookmark objects."""
    return [
        Bookmark(
            url="http://example.com",
            title="Example Site",
            description="A simple example",
            category="tech",
            tags=["example", "web"],
            is_favorite=True,
        ),
        Bookmark(
            url="http://news.com/article",
            title="Breaking News",
            description="Important news today",
            category="news",
            tags=["news"],
            is_favorite=False,
        ),
        Bookmark(
            url="http://blog.dev/python-tips",
            title="Python Tips & Tricks",
            description="Useful Python tips",
            category="tech",
            tags=["python", "tips"],
            is_favorite=True,
        ),
    ]


@pytest.fixture
def exporter(sample_bookmarks):
    """Return a BookmarkExporter pre-loaded with sample bookmarks."""
    return BookmarkExporter(sample_bookmarks)


# ---------------------------------------------------------------------------
# BookmarkExportResult tests
# ---------------------------------------------------------------------------

class TestBookmarkExportResult:
    """Tests for the BookmarkExportResult dataclass."""

    def test_default_values(self):
        result = BookmarkExportResult()
        assert result.format == ""
        assert result.bookmark_count == 0
        assert result.output_path == ""
        assert result.exported_at != ""
        assert result.errors == []

    def test_custom_values(self):
        result = BookmarkExportResult(
            format="json",
            bookmark_count=5,
            output_path="/tmp/test.json",
        )
        assert result.format == "json"
        assert result.bookmark_count == 5
        assert result.output_path == "/tmp/test.json"
        assert result.errors == []

    def test_with_errors(self):
        result = BookmarkExportResult(
            format="json",
            errors=["Something went wrong"],
        )
        assert len(result.errors) == 1
        assert result.errors[0] == "Something went wrong"


# ---------------------------------------------------------------------------
# BookmarkExporter basic tests
# ---------------------------------------------------------------------------

class TestBookmarkExporterInit:
    """Tests for BookmarkExporter initialization."""

    def test_init_with_bookmarks(self, sample_bookmarks):
        exporter = BookmarkExporter(sample_bookmarks)
        assert len(exporter.bookmarks) == 3

    def test_init_empty(self):
        exporter = BookmarkExporter([])
        assert len(exporter.bookmarks) == 0

    def test_init_single_bookmark(self):
        b = Bookmark(url="http://single.com", title="Single")
        exporter = BookmarkExporter([b])
        assert len(exporter.bookmarks) == 1
        assert exporter.bookmarks[0].url == "http://single.com"

    def test_supported_formats(self):
        assert "json" in BookmarkExporter.SUPPORTED_FORMATS
        assert "html" in BookmarkExporter.SUPPORTED_FORMATS
        assert "opml" in BookmarkExporter.SUPPORTED_FORMATS


# ---------------------------------------------------------------------------
# JSON Export tests
# ---------------------------------------------------------------------------

class TestExportJson:
    """Tests for JSON export functionality."""

    def test_export_json_returns_string(self, exporter):
        result = exporter.export_json()
        assert isinstance(result, str)

    def test_export_json_valid_json(self, exporter):
        result = exporter.export_json()
        data = json.loads(result)
        assert isinstance(data, list)

    def test_export_json_count(self, exporter):
        result = exporter.export_json()
        data = json.loads(result)
        assert len(data) == 3

    def test_export_json_fields(self, exporter):
        result = exporter.export_json()
        data = json.loads(result)
        first = data[0]
        assert first["url"] == "http://example.com"
        assert first["title"] == "Example Site"
        assert first["description"] == "A simple example"
        assert first["category"] == "tech"
        assert first["tags"] == ["example", "web"]
        assert first["is_favorite"] is True

    def test_export_json_preserves_order(self, exporter):
        result = exporter.export_json()
        data = json.loads(result)
        urls = [item["url"] for item in data]
        assert urls[0] == "http://example.com"
        assert urls[1] == "http://news.com/article"
        assert urls[2] == "http://blog.dev/python-tips"

    def test_export_json_empty(self):
        exporter = BookmarkExporter([])
        result = exporter.export_json()
        data = json.loads(result)
        assert data == []

    def test_export_json_special_chars(self):
        b = Bookmark(
            url="http://example.com/path?q=1&lang=en",
            title='Title with "quotes" & <tags>',
            description="Description with special chars: <>&\"'",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_json()
        data = json.loads(result)
        assert data[0]["title"] == 'Title with "quotes" & <tags>'
        assert data[0]["description"] == "Description with special chars: <>&\"'"

    def test_export_json_pretty_printed(self, exporter):
        result = exporter.export_json()
        # Should be indented (pretty printed)
        assert "\n" in result
        assert "  " in result


# ---------------------------------------------------------------------------
# HTML Export tests
# ---------------------------------------------------------------------------

class TestExportHtml:
    """Tests for HTML export functionality."""

    def test_export_html_returns_string(self, exporter):
        result = exporter.export_html()
        assert isinstance(result, str)

    def test_export_html_doctype(self, exporter):
        result = exporter.export_html()
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in result

    def test_export_html_meta_charset(self, exporter):
        result = exporter.export_html()
        assert 'charset="UTF-8"' in result or "charset=UTF-8" in result

    def test_export_html_title(self, exporter):
        result = exporter.export_html()
        assert "<TITLE>Bookmarks</TITLE>" in result

    def test_export_html_h1(self, exporter):
        result = exporter.export_html()
        assert "<H1>Bookmarks</H1>" in result

    def test_export_html_dl_structure(self, exporter):
        result = exporter.export_html()
        assert "<DL>" in result
        assert "</DL>" in result

    def test_export_html_contains_urls(self, exporter):
        result = exporter.export_html()
        assert 'HREF="http://example.com"' in result
        assert 'HREF="http://news.com/article"' in result
        assert 'HREF="http://blog.dev/python-tips"' in result

    def test_export_html_contains_titles(self, exporter):
        result = exporter.export_html()
        assert "Example Site" in result
        assert "Breaking News" in result
        assert "Python Tips &amp; Tricks" in result

    def test_export_html_escapes_ampersand(self, exporter):
        result = exporter.export_html()
        # The title "Python Tips & Tricks" should be escaped
        assert "Python Tips &amp; Tricks" in result

    def test_export_html_escapes_angle_brackets(self):
        b = Bookmark(
            url="http://example.com",
            title="Title with <script>alert('xss')</script>",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_html()
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_export_html_escapes_quotes(self):
        b = Bookmark(
            url="http://example.com",
            title='Title with "quotes"',
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_html()
        assert "&quot;" in result

    def test_export_html_empty(self):
        exporter = BookmarkExporter([])
        result = exporter.export_html()
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in result
        assert "<DT><A" not in result

    def test_export_html_uses_url_as_title_when_empty(self):
        b = Bookmark(url="http://no-title.com")
        exporter = BookmarkExporter([b])
        result = exporter.export_html()
        assert "http://no-title.com" in result

    def test_export_html_contains_add_date(self, exporter):
        result = exporter.export_html()
        assert 'ADD_DATE="' in result


# ---------------------------------------------------------------------------
# OPML Export tests
# ---------------------------------------------------------------------------

class TestExportOpml:
    """Tests for OPML export functionality."""

    def test_export_opml_returns_string(self, exporter):
        result = exporter.export_opml()
        assert isinstance(result, str)

    def test_export_opml_xml_declaration(self, exporter):
        result = exporter.export_opml()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result

    def test_export_opml_opml_tag(self, exporter):
        result = exporter.export_opml()
        assert '<opml version="2.0">' in result

    def test_export_opml_head(self, exporter):
        result = exporter.export_opml()
        assert "<head>" in result
        assert "</head>" in result

    def test_export_opml_body(self, exporter):
        result = exporter.export_opml()
        assert "<body>" in result
        assert "</body>" in result

    def test_export_opml_outline_elements(self, exporter):
        result = exporter.export_opml()
        assert result.count("<outline") >= 3

    def test_export_opml_contains_urls(self, exporter):
        result = exporter.export_opml()
        assert "http://example.com" in result
        assert "http://news.com/article" in result
        assert "http://blog.dev/python-tips" in result

    def test_export_opml_contains_titles(self, exporter):
        result = exporter.export_opml()
        assert "Example Site" in result
        assert "Breaking News" in result

    def test_export_opml_valid_xml(self, exporter):
        result = exporter.export_opml()
        # Should parse as valid XML
        ET.fromstring(result)

    def test_export_opml_escapes_special_chars(self):
        b = Bookmark(
            url="http://example.com",
            title="Title with <tags> & 'quotes'",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_opml()
        assert "&lt;tags&gt;" in result
        assert "&amp;" in result

    def test_export_opml_empty(self):
        exporter = BookmarkExporter([])
        result = exporter.export_opml()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert "<opml version=\"2.0\">" in result
        assert "<outline" not in result

    def test_export_opml_uses_url_as_title_when_empty(self):
        b = Bookmark(url="http://no-title.com")
        exporter = BookmarkExporter([b])
        result = exporter.export_opml()
        assert "http://no-title.com" in result

    def test_export_opml_has_title_in_head(self, exporter):
        result = exporter.export_opml()
        assert "<title>" in result
        assert "Bookmarks" in result

    def test_export_opml_has_date_in_head(self, exporter):
        result = exporter.export_opml()
        assert "<dateCreated>" in result or "<dateModified>" in result


# ---------------------------------------------------------------------------
# Export dispatch tests
# ---------------------------------------------------------------------------

class TestExportDispatch:
    """Tests for the export() method that dispatches by format."""

    def test_export_json_dispatch(self, exporter):
        result = exporter.export("json")
        assert isinstance(result, str)
        data = json.loads(result)
        assert len(data) == 3

    def test_export_html_dispatch(self, exporter):
        result = exporter.export("html")
        assert isinstance(result, str)
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in result

    def test_export_opml_dispatch(self, exporter):
        result = exporter.export("opml")
        assert isinstance(result, str)
        assert '<opml version="2.0">' in result

    def test_export_unsupported_format(self, exporter):
        result = exporter.export("xml")
        assert result is None

    def test_export_unknown_format(self, exporter):
        result = exporter.export("pdf")
        assert result is None

    def test_export_case_insensitive(self, exporter):
        result = exporter.export("JSON")
        assert isinstance(result, str)
        data = json.loads(result)
        assert len(data) == 3

    def test_export_html_uppercase(self, exporter):
        result = exporter.export("HTML")
        assert isinstance(result, str)
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in result


# ---------------------------------------------------------------------------
# Export to file tests
# ---------------------------------------------------------------------------

class TestExportToFile:
    """Tests for exporting to files."""

    def test_export_to_file_json(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.json")
        result = exporter.export_to_file(filepath, "json")
        assert result is not None
        assert result.format == "json"
        assert result.bookmark_count == 3
        assert result.output_path == filepath
        assert os.path.exists(filepath)
        with open(filepath) as f:
            data = json.load(f)
        assert len(data) == 3

    def test_export_to_file_html(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.html")
        result = exporter.export_to_file(filepath, "html")
        assert result is not None
        assert result.format == "html"
        assert result.bookmark_count == 3
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
        assert "<!DOCTYPE NETSCAPE-Bookmark-file-1>" in content

    def test_export_to_file_opml(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.opml")
        result = exporter.export_to_file(filepath, "opml")
        assert result is not None
        assert result.format == "opml"
        assert result.bookmark_count == 3
        assert os.path.exists(filepath)
        with open(filepath) as f:
            content = f.read()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in content

    def test_export_to_file_auto_detect_json(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.json")
        result = exporter.export_to_file(filepath)
        assert result.format == "json"

    def test_export_to_file_auto_detect_html(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.html")
        result = exporter.export_to_file(filepath)
        assert result.format == "html"

    def test_export_to_file_auto_detect_opml(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.opml")
        result = exporter.export_to_file(filepath)
        assert result.format == "opml"

    def test_export_to_file_auto_detect_htm(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.htm")
        result = exporter.export_to_file(filepath)
        assert result.format == "html"

    def test_export_to_file_unsupported_extension(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.pdf")
        result = exporter.export_to_file(filepath)
        assert result is not None
        assert len(result.errors) > 0

    def test_export_to_file_unsupported_format(self, exporter, tmp_path):
        filepath = str(tmp_path / "bookmarks.xyz")
        result = exporter.export_to_file(filepath, "pdf")
        assert result is not None
        assert len(result.errors) > 0

    def test_export_to_file_empty_bookmarks(self, tmp_path):
        exporter = BookmarkExporter([])
        filepath = str(tmp_path / "empty.json")
        result = exporter.export_to_file(filepath, "json")
        assert result.bookmark_count == 0
        with open(filepath) as f:
            data = json.load(f)
        assert data == []

    def test_export_to_file_never_returns_none(self, exporter, tmp_path):
        # TICKET-323 regression: export_to_file always returns a
        # BookmarkExportResult (errors reported via result.errors), never None.
        # Success path.
        ok_path = str(tmp_path / "ok.json")
        ok = exporter.export_to_file(ok_path, "json")
        assert ok is not None
        assert isinstance(ok, BookmarkExportResult)
        assert ok.errors == []
        # Unsupported-format path (explicit fmt).
        bad = exporter.export_to_file(str(tmp_path / "x.pdf"), "pdf")
        assert bad is not None
        assert isinstance(bad, BookmarkExportResult)
        assert len(bad.errors) > 0
        # Unsupported-extension path (auto-detect).
        bad2 = exporter.export_to_file(str(tmp_path / "x.xyz"))
        assert bad2 is not None
        assert isinstance(bad2, BookmarkExportResult)
        assert len(bad2.errors) > 0

    def test_export_to_file_returns_result_with_errors_on_write_failure(
        self, exporter, tmp_path, monkeypatch
    ):
        # TICKET-428 claim-truth: the ORIGINAL docstring claim
        # "A BookmarkExportResult on success, or a result with errors on
        # failure" must hold for the file-write failure path too. An OSError
        # during the write must return a BookmarkExportResult with non-empty
        # errors, not propagate.
        import builtins

        real_open = builtins.open

        def fake_open(file, mode="r", *args, **kwargs):
            if "w" in mode and str(file) == str(tmp_path / "denied.json"):
                raise OSError("Permission denied")
            return real_open(file, mode, *args, **kwargs)

        monkeypatch.setattr(builtins, "open", fake_open)

        result = exporter.export_to_file(str(tmp_path / "denied.json"), "json")
        assert result is not None
        assert isinstance(result, BookmarkExportResult)
        assert len(result.errors) > 0
        assert "denied.json" in result.errors[0]
        # No file was written.
        assert not os.path.exists(str(tmp_path / "denied.json"))


# ---------------------------------------------------------------------------
# Edge case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_export_json_unicode(self):
        b = Bookmark(
            url="http://example.com",
            title="日本語のタイトル",
            description="日本語の説明",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_json()
        data = json.loads(result)
        assert data[0]["title"] == "日本語のタイトル"

    def test_export_html_unicode(self):
        b = Bookmark(
            url="http://example.com",
            title="日本語のタイトル",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_html()
        assert "日本語のタイトル" in result

    def test_export_opml_unicode(self):
        b = Bookmark(
            url="http://example.com",
            title="日本語のタイトル",
        )
        exporter = BookmarkExporter([b])
        result = exporter.export_opml()
        assert "日本語のタイトル" in result

    def test_export_many_bookmarks(self):
        bookmarks = [
            Bookmark(url=f"http://example{i}.com", title=f"Site {i}")
            for i in range(100)
        ]
        exporter = BookmarkExporter(bookmarks)

        json_data = json.loads(exporter.export_json())
        assert len(json_data) == 100

        html = exporter.export_html()
        assert html.count("<DT><A") == 100

        opml = exporter.export_opml()
        assert opml.count("<outline") >= 100

    def test_export_bookmark_with_empty_fields(self):
        b = Bookmark(url="http://empty.com")
        exporter = BookmarkExporter([b])

        json_result = json.loads(exporter.export_json())
        assert json_result[0]["title"] == ""
        assert json_result[0]["tags"] == []

        html_result = exporter.export_html()
        assert "http://empty.com" in html_result

        opml_result = exporter.export_opml()
        assert "http://empty.com" in opml_result
