"""Tests for the export module."""

from __future__ import annotations

import csv
import json
import os
from io import StringIO

import pytest

from personal_index.export import Exporter, ExportResult
from personal_index.bookmarks import Bookmark, BookmarkManager


class TestExportResult:
    def test_default_values(self):
        result = ExportResult()
        assert result.total_exported == 0
        assert result.output_path == ""
        assert result.format == ""
        assert result.errors == []
        assert result.exported_at != ""


class TestExporter:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech", tags=["python"]))
        self.manager.add(Bookmark(url="http://b.com", title="B", category="news", is_favorite=True))
        self.exporter = Exporter(self.manager)

    def test_manager_property(self):
        assert self.exporter.manager is self.manager

    def test_supported_formats(self):
        assert "json" in Exporter.SUPPORTED_FORMATS
        assert "csv" in Exporter.SUPPORTED_FORMATS
        assert "markdown" in Exporter.SUPPORTED_FORMATS


class TestExportJson:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech"))
        self.exporter = Exporter(self.manager)

    def test_export_json_content(self):
        content = self.exporter.export_to_content("json")
        assert content is not None
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["url"] == "http://a.com"
        assert data[0]["title"] == "A"

    def test_export_json_file(self, tmp_path):
        path = tmp_path / "bookmarks.json"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 1
        assert result.format == "json"
        assert os.path.exists(str(path))
        with open(path) as f:
            data = json.load(f)
        assert len(data) == 1

    def test_export_json_empty(self):
        exporter = Exporter()
        content = exporter.export_to_content("json")
        assert content == "[]"


class TestExportCsv:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech", tags=["python", "web"]))
        self.exporter = Exporter(self.manager)

    def test_export_csv_content(self):
        content = self.exporter.export_to_content("csv")
        reader = csv.reader(StringIO(content))
        rows = list(reader)
        assert len(rows) == 2  # header + 1 data row
        assert rows[0][0] == "url"
        assert rows[1][0] == "http://a.com"
        assert rows[1][1] == "A"
        assert rows[1][4] == "python;web"

    def test_export_csv_file(self, tmp_path):
        path = tmp_path / "bookmarks.csv"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 1
        assert result.format == "csv"


class TestExportHtml:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A"))
        self.exporter = Exporter(self.manager)

    def test_export_html_content(self):
        content = self.exporter.export_to_content("html")
        assert "DOCTYPE NETSCAPE-Bookmark-file" in content
        assert 'HREF="http://a.com"' in content
        assert "A" in content

    def test_export_html_escapes_special_chars(self):
        self.manager.add(Bookmark(url="http://b.com", title='A & "B" <C>'))
        content = self.exporter.export_to_content("html")
        assert "&amp;" in content
        assert "&lt;" in content
        assert "&gt;" in content

    def test_export_html_file(self, tmp_path):
        path = tmp_path / "bookmarks.html"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 1


class TestExportXml:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", description="Desc", category="tech", tags=["python"]))
        self.exporter = Exporter(self.manager)

    def test_export_xml_content(self):
        content = self.exporter.export_to_content("xml")
        assert '<?xml version="1.0"' in content
        assert "<bookmarks>" in content
        assert 'url="http://a.com"' in content
        assert "<title>A</title>" in content
        assert "<description>Desc</description>" in content
        assert "<category>tech</category>" in content
        assert "<tags>python</tags>" in content

    def test_export_xml_escapes_special_chars(self):
        self.manager.add(Bookmark(url="http://b.com", title="A & B"))
        content = self.exporter.export_to_content("xml")
        assert "&amp;" in content

    def test_export_xml_file(self, tmp_path):
        path = tmp_path / "bookmarks.xml"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 1


class TestExportMarkdown:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech", tags=["python"]))
        self.manager.add(Bookmark(url="http://b.com", title="B", category="news", is_favorite=True))
        self.exporter = Exporter(self.manager)

    def test_export_markdown_content(self):
        content = self.exporter.export_to_content("markdown")
        assert "# Bookmarks" in content
        assert "## tech" in content
        assert "## news" in content
        assert "[A](http://a.com)" in content
        assert "[B](http://b.com) ⭐" in content
        assert "Tags: python" in content

    def test_export_markdown_file(self, tmp_path):
        path = tmp_path / "bookmarks.md"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 2
        assert result.format == "markdown"


class TestExportOpml:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A"))
        self.exporter = Exporter(self.manager)

    def test_export_opml_content(self):
        content = self.exporter.export_to_content("opml")
        assert '<?xml version="1.0"' in content
        assert "<opml version=\"2.0\">" in content
        assert 'htmlUrl="http://a.com"' in content
        assert 'text="A"' in content

    def test_export_opml_file(self, tmp_path):
        path = tmp_path / "bookmarks.opml"
        result = self.exporter.export_to_file(str(path))
        assert result.total_exported == 1


class TestExportFiltered:
    def setup_method(self):
        self.manager = BookmarkManager()
        self.manager.add(Bookmark(url="http://a.com", title="A", category="tech", tags=["python"]))
        self.manager.add(Bookmark(url="http://b.com", title="B", category="news", tags=["web"]))
        self.manager.add(Bookmark(url="http://c.com", title="C", category="tech", is_favorite=True))
        self.exporter = Exporter(self.manager)

    def test_export_filtered_by_category(self):
        content = self.exporter.export_filtered("json", category="tech")
        data = json.loads(content)
        assert len(data) == 2
        urls = {d["url"] for d in data}
        assert urls == {"http://a.com", "http://c.com"}

    def test_export_filtered_by_tag(self):
        content = self.exporter.export_filtered("json", tag="python")
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["url"] == "http://a.com"

    def test_export_filtered_favorites_only(self):
        content = self.exporter.export_filtered("json", favorites_only=True)
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["url"] == "http://c.com"

    def test_export_filtered_combined(self):
        content = self.exporter.export_filtered("json", category="tech", favorites_only=True)
        data = json.loads(content)
        assert len(data) == 1
        assert data[0]["url"] == "http://c.com"

    def test_export_filtered_no_match(self):
        content = self.exporter.export_filtered("json", category="nonexistent")
        data = json.loads(content)
        assert len(data) == 0


class TestExportErrors:
    def test_export_unsupported_format(self, tmp_path):
        exporter = Exporter()
        path = tmp_path / "bookmarks.xyz"
        result = exporter.export_to_file(str(path))
        assert result.total_exported == 0
        assert len(result.errors) > 0

    def test_export_to_content_unsupported(self):
        exporter = Exporter()
        content = exporter.export_to_content("xyz")
        assert content is None
