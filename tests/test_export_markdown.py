"""Tests for export_markdown module - export content as markdown."""

from __future__ import annotations

import pytest
from personal_index.export_markdown import (
    MarkdownExporter,
    ExportConfig,
    ExportFormat,
)


class TestExportConfig:
    """Test ExportConfig dataclass."""

    def test_default_config(self):
        config = ExportConfig()
        assert config.include_metadata is True
        assert config.include_tags is True
        assert config.include_summary is False
        assert config.sort_by == "date"

    def test_custom_config(self):
        config = ExportConfig(sort_by="priority", include_summary=True)
        assert config.sort_by == "priority"
        assert config.include_summary is True

    def test_invalid_sort_by(self):
        with pytest.raises(ValueError):
            ExportConfig(sort_by="invalid")


class TestExportFormat:
    """Test ExportFormat enum."""

    def test_all_formats(self):
        formats = list(ExportFormat)
        assert ExportFormat.MARKDOWN in formats
        assert ExportFormat.HTML in formats
        assert ExportFormat.PLAIN_TEXT in formats

    def test_format_value(self):
        assert ExportFormat.MARKDOWN.value == "markdown"
        assert ExportFormat.HTML.value == "html"
        assert ExportFormat.PLAIN_TEXT.value == "plain_text"


class TestMarkdownExporterBasic:
    """Test basic markdown export functionality."""

    def test_export_single_item(self):
        exporter = MarkdownExporter()
        items = [
            {
                "url": "https://example.com/article",
                "title": "Test Article",
                "content": "This is the article content.",
                "tags": ["test", "example"],
            }
        ]
        result = exporter.export(items)
        assert "# Test Article" in result
        assert "https://example.com/article" in result

    def test_export_empty_items(self):
        exporter = MarkdownExporter()
        result = exporter.export([])
        assert result == ""

    def test_export_preserves_links(self):
        exporter = MarkdownExporter()
        items = [
            {
                "url": "https://example.com/page",
                "title": "My Page",
                "content": "Content here.",
            }
        ]
        result = exporter.export(items)
        assert "[My Page](https://example.com/page)" in result


class TestMarkdownExporterMetadata:
    """Test metadata inclusion in export."""

    def test_include_tags(self):
        config = ExportConfig(include_tags=True)
        exporter = MarkdownExporter(config=config)
        items = [
            {
                "url": "https://example.com/article",
                "title": "Tagged Article",
                "content": "Content.",
                "tags": ["python", "tutorial"],
            }
        ]
        result = exporter.export(items)
        assert "python" in result
        assert "tutorial" in result

    def test_include_date(self):
        config = ExportConfig(include_metadata=True)
        exporter = MarkdownExporter(config=config)
        items = [
            {
                "url": "https://example.com/article",
                "title": "Dated Article",
                "content": "Content.",
                "published_date": "2024-01-15",
            }
        ]
        result = exporter.export(items)
        assert "2024-01-15" in result

    def test_no_tags(self):
        config = ExportConfig(include_tags=True)
        exporter = MarkdownExporter(config=config)
        items = [
            {
                "url": "https://example.com/article",
                "title": "No Tags",
                "content": "Content.",
            }
        ]
        result = exporter.export(items)
        assert "# No Tags" in result


class TestMarkdownExporterSorting:
    """Test sorting options in export."""

    def test_sort_by_date(self):
        config = ExportConfig(sort_by="date")
        exporter = MarkdownExporter(config=config)
        items = [
            {"url": "https://a.com", "title": "Old", "content": "Content.", "published_date": "2023-01-01"},
            {"url": "https://b.com", "title": "New", "content": "Content.", "published_date": "2024-01-01"},
        ]
        result = exporter.export(items)
        # Newer items should appear first
        new_pos = result.index("New")
        old_pos = result.index("Old")
        assert new_pos < old_pos

    def test_sort_by_title(self):
        config = ExportConfig(sort_by="title")
        exporter = MarkdownExporter(config=config)
        items = [
            {"url": "https://a.com", "title": "Zebra", "content": "Content."},
            {"url": "https://b.com", "title": "Apple", "content": "Content."},
        ]
        result = exporter.export(items)
        apple_pos = result.index("Apple")
        zebra_pos = result.index("Zebra")
        assert apple_pos < zebra_pos

    def test_sort_by_priority(self):
        config = ExportConfig(sort_by="priority")
        exporter = MarkdownExporter(config=config)
        items = [
            {"url": "https://a.com", "title": "Low", "content": "Content.", "priority_score": 0.2},
            {"url": "https://b.com", "title": "High", "content": "Content.", "priority_score": 0.9},
        ]
        result = exporter.export(items)
        high_pos = result.index("High")
        low_pos = result.index("Low")
        assert high_pos < low_pos


class TestMarkdownExporterGrouping:
    """Test grouping options in export."""

    def test_group_by_tags(self):
        config = ExportConfig(group_by="tags")
        exporter = MarkdownExporter(config=config)
        items = [
            {"url": "https://a.com", "title": "Python 1", "content": "Content.", "tags": ["python"]},
            {"url": "https://b.com", "title": "JS 1", "content": "Content.", "tags": ["javascript"]},
            {"url": "https://c.com", "title": "Python 2", "content": "Content.", "tags": ["python"]},
        ]
        result = exporter.export(items)
        assert "## python" in result or "## Python" in result

    def test_group_by_date(self):
        config = ExportConfig(group_by="date")
        exporter = MarkdownExporter(config=config)
        items = [
            {"url": "https://a.com", "title": "Jan", "content": "Content.", "published_date": "2024-01-15"},
            {"url": "https://b.com", "title": "Feb", "content": "Content.", "published_date": "2024-02-15"},
        ]
        result = exporter.export(items)
        assert "2024-01" in result or "2024-02" in result


class TestMarkdownExporterHTML:
    """Test HTML export format."""

    def test_export_html(self):
        exporter = MarkdownExporter()
        items = [
            {"url": "https://example.com", "title": "HTML Test", "content": "Content."},
        ]
        result = exporter.export(items, format=ExportFormat.HTML)
        assert "<h1>" in result or "<h2>" in result
        assert "HTML Test" in result

    def test_html_escapes_special_chars(self):
        exporter = MarkdownExporter()
        items = [
            {"url": "https://example.com", "title": "Test <script>", "content": "Content & more."},
        ]
        result = exporter.export(items, format=ExportFormat.HTML)
        assert "<script>" not in result


class TestMarkdownExporterPlainText:
    """Test plain text export format."""

    def test_export_plain_text(self):
        exporter = MarkdownExporter()
        items = [
            {"url": "https://example.com", "title": "Plain Test", "content": "Content."},
        ]
        result = exporter.export(items, format=ExportFormat.PLAIN_TEXT)
        assert "Plain Test" in result
        assert "https://example.com" in result


class TestMarkdownExporterIntegration:
    """Integration tests for markdown export."""

    def test_export_large_collection(self):
        exporter = MarkdownExporter()
        items = [
            {"url": f"https://example.com/{i}", "title": f"Article {i}",
             "content": f"Content for article {i}.", "tags": ["test"]}
            for i in range(100)
        ]
        result = exporter.export(items)
        assert "Article 0" in result
        assert "Article 99" in result

    def test_export_with_all_options(self):
        config = ExportConfig(
            include_metadata=True,
            include_tags=True,
            include_summary=True,
            sort_by="title",
            group_by="tags",
        )
        exporter = MarkdownExporter(config=config)
        items = [
            {
                "url": "https://example.com/1",
                "title": "Z Article",
                "content": "This is a longer article with enough content to be summarized properly.",
                "tags": ["tech"],
                "published_date": "2024-01-01",
            },
            {
                "url": "https://example.com/2",
                "title": "A Article",
                "content": "Another article with different content for testing purposes.",
                "tags": ["science"],
                "published_date": "2024-02-01",
            },
        ]
        result = exporter.export(items)
        assert "A Article" in result
        assert "Z Article" in result

    def test_export_special_characters_in_title(self):
        exporter = MarkdownExporter()
        items = [
            {"url": "https://example.com", "title": "Title with # hash", "content": "Content."},
        ]
        result = exporter.export(items)
        assert "hash" in result

    def test_export_unicode_content(self):
        exporter = MarkdownExporter()
        items = [
            {"url": "https://example.com", "title": "日本語記事", "content": "これはテストです。"},
        ]
        result = exporter.export(items)
        assert "日本語記事" in result
