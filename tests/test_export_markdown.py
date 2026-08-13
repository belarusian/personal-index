"""Tests for export_markdown module - MarkdownExporter class."""


import pytest

from personal_index.export_markdown import (
    ExportConfig,
    MarkdownExporter,
)


class TestExportConfig:
    """Tests for ExportConfig dataclass."""

    def test_default_config(self):
        config = ExportConfig()
        assert config.include_metadata is True
        assert config.include_tags is True
        assert config.include_summary is False
        assert config.sort_by == "date"
        assert config.group_by is None

    def test_custom_sort_by(self):
        config = ExportConfig(sort_by="title")
        assert config.sort_by == "title"

    def test_custom_group_by(self):
        config = ExportConfig(group_by="tags")
        assert config.group_by == "tags"

    def test_invalid_sort_by_raises(self):
        with pytest.raises(ValueError, match="Invalid sort_by"):
            ExportConfig(sort_by="invalid")

    def test_invalid_group_by_raises(self):
        with pytest.raises(ValueError, match="Invalid group_by"):
            ExportConfig(group_by="invalid")


class TestMarkdownExporter:
    """Tests for MarkdownExporter class."""

    @pytest.fixture
    def sample_items(self):
        return [
            {
                "title": "Python Tutorial",
                "url": "https://example.com/python",
                "content": "Learn Python programming",
                "tags": ["python", "tutorial"],
                "published_date": "2024-01-15",
            },
            {
                "title": "JavaScript Guide",
                "url": "https://example.com/javascript",
                "content": "Learn JavaScript",
                "tags": ["javascript", "web"],
                "published_date": "2024-02-20",
            },
        ]

    @pytest.fixture
    def exporter(self):
        return MarkdownExporter()

    # -- export_single_page() --
    def test_export_single_page(self, exporter):
        items = [{"title": "Single Page", "url": "https://example.com"}]
        result = exporter.export(items)
        assert "Single Page" in result
        assert "https://example.com" in result

    def test_export_single_page_with_metadata(self, exporter):
        items = [
            {
                "title": "Test",
                "url": "https://example.com",
                "published_date": "2024-01-01",
            }
        ]
        result = exporter.export(items)
        assert "2024-01-01" in result

    def test_export_single_page_with_tags(self, exporter):
        items = [
            {
                "title": "Test",
                "url": "https://example.com",
                "tags": ["python", "web"],
            }
        ]
        result = exporter.export(items)
        assert "python" in result
        assert "web" in result

    # -- export_collection() --
    def test_export_collection(self, exporter, sample_items):
        result = exporter.export(sample_items)
        assert "Python Tutorial" in result
        assert "JavaScript Guide" in result

    def test_export_collection_empty(self, exporter):
        result = exporter.export([])
        assert result == ""

    # -- heading levels --
    def test_heading_level_h1_for_title(self, exporter):
        items = [{"title": "My Title", "url": "https://example.com"}]
        result = exporter.export(items)
        assert "# My Title" in result

    def test_heading_level_h2_for_group(self, exporter):
        config = ExportConfig(group_by="tags")
        exporter = MarkdownExporter(config=config)
        items = [
            {"title": "A", "url": "https://a.com", "tags": ["python"]},
            {"title": "B", "url": "https://b.com", "tags": ["javascript"]},
        ]
        result = exporter.export(items)
        assert "## python" in result or "## javascript" in result

    # -- link formatting --
    def test_link_formatting(self, exporter):
        items = [{"title": "My Link", "url": "https://example.com/page"}]
        result = exporter.export(items)
        assert "[My Link](https://example.com/page)" in result

    def test_link_with_special_chars(self, exporter):
        items = [{"title": "Test & More", "url": "https://example.com/path?q=1"}]
        result = exporter.export(items)
        assert "https://example.com/path?q=1" in result

    # -- code block handling --
    def test_code_block_in_content(self, exporter):
        items = [
            {
                "title": "Code Example",
                "url": "https://example.com",
                "content": "def hello(): pass",
            }
        ]
        result = exporter.export(items)
        assert "def hello" in result

    def test_metadata_rendering(self, exporter):
        items = [
            {
                "title": "With Meta",
                "url": "https://example.com",
                "published_date": "2024-06-01",
                "tags": ["test"],
            }
        ]
        result = exporter.export(items)
        assert "With Meta" in result

    def test_export_returns_string(self, exporter, sample_items):
        result = exporter.export(sample_items)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_export_preserves_order(self, exporter):
        items = [
            {"title": "First", "url": "https://a.com"},
            {"title": "Second", "url": "https://b.com"},
        ]
        result = exporter.export(items)
        first_pos = result.index("First")
        second_pos = result.index("Second")
        assert first_pos < second_pos
