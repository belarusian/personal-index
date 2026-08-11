"""Tests for content_exporter module."""

import json
import pytest
from datetime import datetime, timezone
from personal_index.content_exporter import ContentExporter


# --- Fixtures ---

@pytest.fixture
def exporter():
    return ContentExporter(title="My Index", base_url="http://example.com")


@pytest.fixture
def sample_items():
    return [
        {
            "id": "1",
            "title": "First Post",
            "description": "This is the first post.",
            "link": "http://example.com/1",
            "date": datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            "tags": ["python", "tutorial"],
        },
        {
            "id": "2",
            "title": "Second Post",
            "description": "This is the second post.",
            "link": "http://example.com/2",
            "date": datetime(2024, 2, 20, 14, 0, 0, tzinfo=timezone.utc),
            "tags": ["javascript"],
        },
    ]


# --- JSON Export Tests ---

class TestJsonExport:
    def test_export_json_basic(self, exporter, sample_items):
        result = exporter.export(sample_items, "json")
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 2

    def test_export_json_preserves_fields(self, exporter, sample_items):
        result = exporter.export(sample_items, "json")
        data = json.loads(result)
        assert data[0]["title"] == "First Post"
        assert data[0]["description"] == "This is the first post."
        assert data[0]["link"] == "http://example.com/1"

    def test_export_json_tags(self, exporter, sample_items):
        result = exporter.export(sample_items, "json")
        data = json.loads(result)
        assert data[0]["tags"] == ["python", "tutorial"]

    def test_export_json_empty_list(self, exporter):
        result = exporter.export([], "json")
        assert result == "[]"

    def test_export_json_case_insensitive(self, exporter, sample_items):
        result = exporter.export(sample_items, "JSON")
        data = json.loads(result)
        assert len(data) == 2

    def test_export_json_indent(self, exporter, sample_items):
        result = exporter.export(sample_items, "json")
        assert "  " in result  # indented


# --- HTML Export Tests ---

class TestHtmlExport:
    def test_export_html_doctype(self, exporter, sample_items):
        result = exporter.export(sample_items, "html")
        assert "<!DOCTYPE html>" in result

    def test_export_html_title(self, exporter, sample_items):
        result = exporter.export(sample_items, "html")
        assert "<title>My Index</title>" in result

    def test_export_html_item_count(self, exporter, sample_items):
        result = exporter.export(sample_items, "html")
        assert result.count("<article>") == 2

    def test_export_html_escaped_content(self, exporter):
        items = [{"title": "<script>alert('xss')</script>", "description": "& < >"}]
        result = exporter.export(items, "html")
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_export_html_links(self, exporter, sample_items):
        result = exporter.export(sample_items, "html")
        assert 'href="http://example.com/1"' in result

    def test_export_html_tags(self, exporter, sample_items):
        result = exporter.export(sample_items, "html")
        assert 'class="tag"' in result
        assert "python" in result
        assert "tutorial" in result

    def test_export_html_empty_items(self, exporter):
        result = exporter.export([], "html")
        assert "<html" in result
        assert result.count("<article>") == 0

    def test_export_html_no_link(self, exporter):
        items = [{"title": "No Link Post", "description": "No link here"}]
        result = exporter.export(items, "html")
        assert "No Link Post" in result
        assert 'href=""' not in result
