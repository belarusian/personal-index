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
from personal_index.index import SearchIndex, IndexedPage
from personal_index.models import SearchResult


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
