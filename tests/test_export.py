"""Tests for export functionality."""

from __future__ import annotations

import csv
import io
import json
import tempfile
from datetime import datetime, timezone

import pytest

from personal_index.export import (
    export_to_json,
    export_to_csv,
    export_search_results_to_json,
    export_search_results_to_csv,
    export_to_markdown,
    export_to_markdown_results,
)
from personal_index.index import SearchIndex, IndexedPage, SearchResult


@pytest.fixture
def sample_index():
    """Create a SearchIndex with sample data."""
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
        idx = SearchIndex(db_path=f.name)
        idx.add_page(IndexedPage(
            url="http://example.com/page1",
            title="First Page",
            content="This is the first page content about python",
            score=8.5,
            indexed_at=datetime.now(timezone.utc).isoformat(),
        ))
        idx.add_page(IndexedPage(
            url="http://example.com/page2",
            title="Second Page",
            content="This is the second page about javascript",
            score=6.0,
            indexed_at=datetime.now(timezone.utc).isoformat(),
        ))
        return idx


class TestExportToJson:
    """Tests for JSON export."""

    def test_export_to_json_basic(self, sample_index):
        result = export_to_json(sample_index)
        data = json.loads(result)
        assert data["total_pages"] == 2
        assert len(data["pages"]) == 2

    def test_export_to_json_includes_urls(self, sample_index):
        result = export_to_json(sample_index)
        data = json.loads(result)
        urls = [p["url"] for p in data["pages"]]
        assert "http://example.com/page1" in urls
        assert "http://example.com/page2" in urls

    def test_export_to_json_excludes_content(self, sample_index):
        result = export_to_json(sample_index, include_content=False)
        data = json.loads(result)
        for page in data["pages"]:
            assert "content" not in page

    def test_export_to_json_includes_content(self, sample_index):
        result = export_to_json(sample_index, include_content=True)
        data = json.loads(result)
        assert any("python" in p.get("content", "") for p in data["pages"])

    def test_export_to_json_empty_index(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            idx = SearchIndex(db_path=f.name)
        result = export_to_json(idx)
        data = json.loads(result)
        assert data["total_pages"] == 0
        assert data["pages"] == []

    def test_export_to_json_indent(self, sample_index):
        result = export_to_json(sample_index, indent=4)
        assert "    " in result


class TestExportToCsv:
    """Tests for CSV export."""

    def test_export_to_csv_basic(self, sample_index):
        result = export_to_csv(sample_index)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 3  # header + 2 pages
        assert rows[0] == ["url", "title", "score", "indexed_at", "content"]

    def test_export_to_csv_includes_content(self, sample_index):
        result = export_to_csv(sample_index, include_content=True)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)[1:]  # skip header
        content_values = [r[4] for r in rows]
        assert any("python" in c for c in content_values)

    def test_export_to_csv_excludes_content(self, sample_index):
        result = export_to_csv(sample_index, include_content=False)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)[1:]
        assert all(r[4] == "" for r in rows)

    def test_export_to_csv_empty_index(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            idx = SearchIndex(db_path=f.name)
        result = export_to_csv(idx)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1  # only header


class TestExportSearchResults:
    """Tests for search result export."""

    def test_export_search_results_to_json(self):
        results = [
            SearchResult(
                url="http://example.com",
                title="Test Page",
                snippet="Some content here",
                relevance_score=5.0,
            )
        ]
        data = json.loads(export_search_results_to_json(results))
        assert data["total_results"] == 1
        assert data["results"][0]["title"] == "Test Page"

    def test_export_search_results_to_csv(self):
        results = [
            SearchResult(
                url="http://example.com",
                title="Test Page",
                snippet="Some content here",
                relevance_score=5.0,
            )
        ]
        reader = csv.reader(io.StringIO(export_search_results_to_csv(results)))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[0] == ["url", "title", "snippet", "relevance_score"]

    def test_export_search_results_empty(self):
        data = json.loads(export_search_results_to_json([]))
        assert data["total_results"] == 0


class TestExportToMarkdown:
    """Tests for Markdown export."""

    def test_export_to_markdown_basic(self, sample_index):
        result = export_to_markdown(sample_index)
        assert "# Indexed Pages" in result
        assert "First Page" in result
        assert "Second Page" in result

    def test_export_to_markdown_includes_content(self, sample_index):
        result = export_to_markdown(sample_index, include_content=True)
        assert "python" in result

    def test_export_to_markdown_excludes_content(self, sample_index):
        result = export_to_markdown(sample_index, include_content=False)
        assert "python" not in result

    def test_export_to_markdown_results(self):
        results = [
            SearchResult(
                url="http://example.com",
                title="Test Page",
                snippet="Some content",
                relevance_score=5.0,
            )
        ]
        result = export_to_markdown_results(results)
        assert "# Search Results" in result
        assert "Test Page" in result
        assert "5.00" in result


class TestJSONExporter:
    def test_export_entry(self, tmp_path):
        from personal_index.export import JSONExporter
        exporter = JSONExporter()
        entry = {"url": "http://example.com", "title": "Test"}
        result = exporter.export_entry(entry)
        assert "http://example.com" in result
        assert "Test" in result

    def test_export_entries_to_file(self, tmp_path):
        from personal_index.export import JSONExporter
        exporter = JSONExporter()
        entries = [
            {"url": "http://example.com/1", "title": "Page 1"},
            {"url": "http://example.com/2", "title": "Page 2"},
        ]
        filepath = str(tmp_path / "export.json")
        result = exporter.export_entries(entries, filepath)
        assert result == filepath
        import json
        with open(filepath) as f:
            data = json.load(f)
        assert data["total_entries"] == 2
        assert len(data["entries"]) == 2

    def test_export_batch(self):
        from personal_index.export import JSONExporter
        exporter = JSONExporter()
        entries = [{"url": f"http://example.com/{i}"} for i in range(250)]
        batches = exporter.export_batch(entries, batch_size=100)
        assert len(batches) == 3
        import json
        first = json.loads(batches[0])
        assert first["count"] == 100
        assert first["batch_index"] == 0

    def test_export_empty(self, tmp_path):
        from personal_index.export import JSONExporter
        exporter = JSONExporter()
        filepath = str(tmp_path / "empty.json")
        result = exporter.export_entries([], filepath)
        import json
        with open(result) as f:
            data = json.load(f)
        assert data["total_entries"] == 0
        assert data["entries"] == []

    def test_export_preserves_unicode(self, tmp_path):
        from personal_index.export import JSONExporter
        exporter = JSONExporter()
        entries = [{"url": "http://example.com", "title": "日本語テスト"}]
        filepath = str(tmp_path / "unicode.json")
        exporter.export_entries(entries, filepath)
        with open(filepath, encoding="utf-8") as f:
            content = f.read()
        assert "日本語テスト" in content
