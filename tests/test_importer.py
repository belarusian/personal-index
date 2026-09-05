"""Tests for the importer module."""

from __future__ import annotations

import json
import os

from personal_index.bookmarks import BookmarkManager
from personal_index.importer import Importer, ImportResult


class TestImportResult:
    def test_default_values(self):
        result = ImportResult()
        assert result.total_imported == 0
        assert result.total_skipped == 0
        assert result.errors == []
        assert result.source == ""
        assert result.format == ""
        assert result.imported_at != ""

    def test_custom_values(self):
        result = ImportResult(total_imported=5, source="test.json", format="json")
        assert result.total_imported == 5
        assert result.source == "test.json"
        assert result.format == "json"


class TestImporter:
    def setup_method(self):
        self.importer = Importer()

    def test_manager_property(self):
        manager = BookmarkManager()
        imp = Importer(manager)
        assert imp.manager is manager

    def test_supported_formats(self):
        assert "json" in Importer.SUPPORTED_FORMATS
        assert "csv" in Importer.SUPPORTED_FORMATS
        assert "html" in Importer.SUPPORTED_FORMATS
        assert "xml" in Importer.SUPPORTED_FORMATS


class TestImporterJson:
    def setup_method(self):
        self.importer = Importer()

    def test_import_json_list(self, tmp_path):
        data = [
            {"url": "http://a.com", "title": "A", "category": "tech"},
            {"url": "http://b.com", "title": "B", "tags": ["web"]},
        ]
        path = tmp_path / "bookmarks.json"
        path.write_text(json.dumps(data))
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 2
        assert result.total_skipped == 0
        assert result.format == "json"

    def test_import_json_single_dict(self, tmp_path):
        data = {"url": "http://a.com", "title": "A"}
        path = tmp_path / "bookmark.json"
        path.write_text(json.dumps(data))
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1

    def test_import_json_invalid(self, tmp_path):
        path = tmp_path / "bad.json"
        path.write_text("{invalid json}")
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_json_empty_url(self, tmp_path):
        data = [{"url": "", "title": "No URL"}, {"url": "http://a.com", "title": "A"}]
        path = tmp_path / "bookmarks.json"
        path.write_text(json.dumps(data))
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1
        assert result.total_skipped == 1

    def test_import_json_with_all_fields(self, tmp_path):
        data = [{
            "url": "http://a.com",
            "title": "Test",
            "description": "A test bookmark",
            "category": "tech",
            "tags": ["python", "web"],
            "is_favorite": True,
        }]
        path = tmp_path / "bookmarks.json"
        path.write_text(json.dumps(data))
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1
        bm = self.importer.manager.get("http://a.com")
        assert bm.title == "Test"
        assert bm.description == "A test bookmark"
        assert bm.category == "tech"
        assert bm.tags == ["python", "web"]
        assert bm.is_favorite is True

    def test_import_json_per_item_error_accumulates_and_continues(self, monkeypatch):
        """Pin _import_json sub-component 4: a per-item (ValueError, TypeError)
        raised during manager.add is caught, appended to result.errors, and the
        loop continues to the next item (no abort)."""
        calls = []

        def fake_add(bookmark):
            calls.append(bookmark.url)
            if bookmark.url == "http://bad.com":
                raise TypeError("boom")
            return bookmark

        monkeypatch.setattr(self.importer._manager, "add", fake_add)
        data = [
            {"url": "http://good.com", "title": "Good"},
            {"url": "http://bad.com", "title": "Bad"},
            {"url": "http://also-good.com", "title": "Also Good"},
        ]
        result = self.importer.import_from_content(json.dumps(data), "json")
        # The loop did not abort: both good items were still imported.
        assert result.total_imported == 2
        assert result.total_skipped == 0
        # Exactly one per-item error was accumulated for the failing item.
        assert len(result.errors) == 1
        assert result.errors[0].startswith("Error importing item:")
        # The failing item was attempted (add called) but not counted as imported.
        assert calls == ["http://good.com", "http://bad.com", "http://also-good.com"]


class TestImporterCsv:
    def setup_method(self):
        self.importer = Importer()

    def test_import_csv_basic(self, tmp_path):
        content = "url,title,description,category,tags\nhttp://a.com,A,Desc A,tech,python\nhttp://b.com,B,Desc B,news,web\n"
        path = tmp_path / "bookmarks.csv"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 2
        assert result.format == "csv"

    def test_import_csv_with_favorites(self, tmp_path):
        content = "url,title,favorite\nhttp://a.com,A,true\nhttp://b.com,B,false\n"
        path = tmp_path / "bookmarks.csv"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 2
        assert self.importer.manager.get("http://a.com").is_favorite is True
        assert self.importer.manager.get("http://b.com").is_favorite is False

    def test_import_csv_empty_url_skipped(self, tmp_path):
        content = "url,title\n,A\nhttp://b.com,B\n"
        path = tmp_path / "bookmarks.csv"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1
        assert result.total_skipped == 1

    def test_import_csv_case_insensitive_headers_and_multi_tags(self):
        # Uppercase headers (URL/Title/Tags) must be honored via the
        # case-insensitive fallback, and the Tags value must be
        # comma-split and stripped into a list.
        content = (
            "URL,Title,Tags\n"
            "http://a.com,A,\"python, web,  ai\"\n"
            "http://b.com,B,news\n"
        )
        result = self.importer.import_from_content(content, "csv")
        assert result.total_imported == 2
        a = self.importer.manager.get("http://a.com")
        b = self.importer.manager.get("http://b.com")
        assert a.title == "A"
        assert a.tags == ["python", "web", "ai"]
        assert b.title == "B"
        assert b.tags == ["news"]


class TestImporterHtml:
    def setup_method(self):
        self.importer = Importer()

    def test_import_html_basic(self, tmp_path):
        content = '<!DOCTYPE NETSCAPE-Bookmark-file><ROOT><a href="http://a.com">A</a><a href="http://b.com">B</a></ROOT>'
        path = tmp_path / "bookmarks.html"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 2
        assert result.format == "html"

    def test_import_html_invalid(self, tmp_path):
        content = "<not valid html"
        path = tmp_path / "bookmarks.html"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_html_nested(self, tmp_path):
        content = '<ROOT><DL><DT><H3>Folder</H3><DL><DT><A HREF="http://a.com">A</A></DL></DL></ROOT>'
        path = tmp_path / "bookmarks.html"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1


class TestImporterXml:
    def setup_method(self):
        self.importer = Importer()

    def test_import_xml_basic(self, tmp_path):
        content = '<bookmarks><bookmark url="http://a.com"><title>A</title><description>Desc</description><category>tech</category><tags>python,web</tags></bookmark></bookmarks>'
        path = tmp_path / "bookmarks.xml"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1
        bm = self.importer.manager.get("http://a.com")
        assert bm.title == "A"
        assert bm.tags == ["python", "web"]

    def test_import_xml_invalid(self, tmp_path):
        content = "<not valid xml"
        path = tmp_path / "bookmarks.xml"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_xml_empty_url(self, tmp_path):
        content = '<bookmarks><bookmark url=""><title>A</title></bookmark></bookmarks>'
        path = tmp_path / "bookmarks.xml"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 0
        assert result.total_skipped == 1

    def test_import_xml_tags_and_empty_url_accounting(self, tmp_path):
        """Pin _import_xml sub-components: comma-split tags and the
        url-truthy import-vs-skip accounting (TICKET-399)."""
        content = (
            "<bookmarks>"
            "<bookmark url=\"http://a.com\"><title>A</title>"
            "<tags>python, web, </tags></bookmark>"
            "<bookmark url=\"\"><title>B</title></bookmark>"
            "</bookmarks>"
        )
        path = tmp_path / "bookmarks.xml"
        path.write_text(content)
        result = self.importer.import_from_file(str(path))
        assert result.total_imported == 1
        assert result.total_skipped == 1
        bm = self.importer.manager.get("http://a.com")
        assert bm.tags == ["python", "web"]


class TestImporterOpml:
    def setup_method(self):
        self.importer = Importer()

    def test_import_opml(self):
        content = '<opml><body><outline text="Feed" xmlUrl="http://a.com/rss" htmlUrl="http://a.com"/><outline text="Feed2" xmlUrl="http://b.com/rss"/></body></opml>'
        result = self.importer.import_opml(content)
        assert result.total_imported == 2
        assert result.format == "opml"

    def test_import_opml_invalid(self):
        result = self.importer.import_opml("<invalid")
        assert result.total_imported == 0
        assert len(result.errors) > 0


class TestImporterFileErrors:
    def test_import_nonexistent_file(self):
        result = Importer().import_from_file("/tmp/does_not_exist.json")
        assert result.total_imported == 0
        assert len(result.errors) > 0

    def test_import_unsupported_format(self, tmp_path):
        path = tmp_path / "bookmarks.xyz"
        path.write_text("data")
        result = Importer().import_from_file(str(path))
        assert result.total_imported == 0
        assert "Unsupported format" in result.errors[0]


class TestImporterContent:
    def test_import_from_content_json(self):
        importer = Importer()
        data = json.dumps([{"url": "http://a.com", "title": "A"}])
        result = importer.import_from_content(data, "json")
        assert result.total_imported == 1

    def test_import_from_content_csv(self):
        importer = Importer()
        content = "url,title\nhttp://a.com,A\n"
        result = importer.import_from_content(content, "csv")
        assert result.total_imported == 1

    def test_import_from_content_unsupported(self):
        importer = Importer()
        result = importer.import_from_content("data", "xyz")
        assert result.total_imported == 0
        assert len(result.errors) > 0


def test_importer_uses_defusedxml():
    """Verify importer.py uses defusedxml for safe XML parsing (TICKET-62)."""
    importer_path = os.path.join(os.path.dirname(__file__), "..", "personal_index", "importer.py")
    with open(importer_path) as f:
        source = f.read()
    assert "defusedxml" in source, "importer.py should use defusedxml for safe XML parsing"
    assert "ET.fromstring" not in source, "importer.py should not use ET.fromstring directly"


def test_rss_uses_defusedxml():
    """Verify rss.py uses defusedxml for safe XML parsing (TICKET-62)."""
    rss_path = os.path.join(os.path.dirname(__file__), "..", "personal_index", "rss.py")
    with open(rss_path) as f:
        source = f.read()
    assert "defusedxml" in source, "rss.py should use defusedxml for safe XML parsing"


def test_sitemap_uses_defusedxml():
    """Verify sitemap.py uses defusedxml for safe XML parsing (TICKET-62)."""
    sitemap_path = os.path.join(os.path.dirname(__file__), "..", "personal_index", "sitemap.py")
    with open(sitemap_path) as f:
        source = f.read()
    assert "defusedxml" in source, "sitemap.py should use defusedxml for safe XML parsing"
