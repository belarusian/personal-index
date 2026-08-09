"""Tests for content_export_txt module - export saved content as plain text."""

from __future__ import annotations

import os
import tempfile
import pytest
from personal_index.content_export_txt import (
    TXTExporter,
    TXTExportConfig,
    TXTExportResult,
    TXTExportStyle,
)


class TestTXTExportConfig:
    """Tests for TXTExportConfig dataclass."""

    def test_default_config(self):
        config = TXTExportConfig()
        assert config.title == "Content Export"
        assert config.include_title is True
        assert config.include_url is True
        assert config.include_date is True
        assert config.include_tags is True
        assert config.include_description is True
        assert config.include_body is True
        assert config.separator == "=" * 60
        assert config.item_separator == "-" * 40
        assert config.max_line_length == 80
        assert config.wrap_text is True
        assert config.encoding == "utf-8"
        assert config.style == TXTExportStyle.PLAIN

    def test_compact_config(self):
        config = TXTExportConfig(
            include_title=True,
            include_url=False,
            include_date=False,
            include_tags=False,
            include_description=False,
            include_body=False,
        )
        assert config.include_title is True
        assert config.include_url is False
        assert config.include_body is False

    def test_custom_separator(self):
        config = TXTExportConfig(separator="***", item_separator="---")
        assert config.separator == "***"
        assert config.item_separator == "---"

    def test_no_wrap(self):
        config = TXTExportConfig(wrap_text=False, max_line_length=200)
        assert config.wrap_text is False
        assert config.max_line_length == 200

    def test_to_dict(self):
        config = TXTExportConfig(title="My Export", include_body=False)
        d = config.to_dict()
        assert d["title"] == "My Export"
        assert d["include_body"] is False

    def test_from_dict(self):
        d = {
            "title": "Custom Export",
            "include_body": False,
            "separator": "###",
            "wrap_text": False,
        }
        config = TXTExportConfig.from_dict(d)
        assert config.title == "Custom Export"
        assert config.include_body is False
        assert config.separator == "###"
        assert config.wrap_text is False


class TestTXTExportStyle:
    """Tests for TXTExportStyle enum."""

    def test_plain_style(self):
        assert TXTExportStyle.PLAIN.value == "plain"

    def test_markdown_style(self):
        assert TXTExportStyle.MARKDOWN.value == "markdown"

    def test_from_string(self):
        style = TXTExportStyle.from_string("markdown")
        assert style == TXTExportStyle.MARKDOWN

    def test_from_string_invalid(self):
        style = TXTExportStyle.from_string("invalid")
        assert style == TXTExportStyle.PLAIN


class TestTXTExportResult:
    """Tests for TXTExportResult dataclass."""

    def test_default_result(self):
        result = TXTExportResult()
        assert result.items_exported == 0
        assert result.output == ""
        assert result.errors == []
        assert result.exported_at != ""

    def test_result_with_data(self):
        result = TXTExportResult(items_exported=5, output="some text")
        assert result.items_exported == 5
        assert result.output == "some text"

    def test_result_with_errors(self):
        result = TXTExportResult(items_exported=0, errors=["something failed"])
        assert len(result.errors) == 1
        assert result.errors[0] == "something failed"

    def test_to_dict(self):
        result = TXTExportResult(items_exported=10, output="text", style="plain")
        d = result.to_dict()
        assert d["items_exported"] == 10
        assert d["output"] == "text"
        assert d["style"] == "plain"


class TestTXTExporter:
    """Tests for TXTExporter class."""

    def setup_method(self):
        self.exporter = TXTExporter()

    def test_export_empty(self):
        result = self.exporter.export([])
        assert result.items_exported == 0
        assert result.output == ""

    def test_export_single_item(self):
        items = [
            {
                "title": "Test Article",
                "url": "http://example.com/article",
                "created_at": "2024-01-15T10:30:00",
                "description": "A test article",
                "body": "This is the body text of the article.",
                "tags": ["test", "example"],
            }
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 1
        assert "Test Article" in result.output
        assert "http://example.com/article" in result.output

    def test_export_multiple_items(self):
        items = [
            {
                "title": "Article A",
                "url": "http://example.com/a",
                "body": "Body A",
            },
            {
                "title": "Article B",
                "url": "http://example.com/b",
                "body": "Body B",
            },
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 2
        assert "Article A" in result.output
        assert "Article B" in result.output

    def test_export_with_title_only(self):
        config = TXTExportConfig(
            include_title=True,
            include_url=False,
            include_date=False,
            include_tags=False,
            include_description=False,
            include_body=False,
        )
        items = [
            {
                "title": "Only Title",
                "url": "http://example.com",
                "body": "Should not appear",
            }
        ]
        result = self.exporter.export(items, config=config)
        assert "Only Title" in result.output
        assert "Should not appear" not in result.output
        assert "http://example.com" not in result.output

    def test_export_with_body_only(self):
        config = TXTExportConfig(
            include_title=False,
            include_url=False,
            include_date=False,
            include_tags=False,
            include_description=False,
            include_body=True,
        )
        items = [
            {
                "title": "Hidden Title",
                "body": "Visible body text",
            }
        ]
        result = self.exporter.export(items, config=config)
        assert "Hidden Title" not in result.output
        assert "Visible body text" in result.output

    def test_export_with_tags(self):
        items = [
            {
                "title": "Tagged Article",
                "tags": ["python", "testing", "export"],
            }
        ]
        result = self.exporter.export(items)
        assert "python" in result.output
        assert "testing" in result.output
        assert "export" in result.output

    def test_export_with_description(self):
        items = [
            {
                "title": "Article",
                "description": "A brief description",
            }
        ]
        result = self.exporter.export(items)
        assert "A brief description" in result.output

    def test_export_without_description(self):
        items = [
            {
                "title": "Article",
            }
        ]
        result = self.exporter.export(items)
        assert "Article" in result.output

    def test_export_handles_missing_fields(self):
        items = [
            {
                "title": "Incomplete",
            }
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 1
        assert "Incomplete" in result.output

    def test_export_handles_empty_body(self):
        items = [
            {
                "title": "No Body",
                "body": "",
            }
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 1

    def test_export_handles_none_values(self):
        items = [
            {
                "title": None,
                "url": None,
                "body": None,
            }
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 1
        assert result.errors == []

    def test_export_with_custom_separator(self):
        config = TXTExportConfig(separator="***", item_separator="---")
        items = [
            {"title": "A", "body": "Body A"},
            {"title": "B", "body": "Body B"},
        ]
        result = self.exporter.export(items, config=config)
        assert "***" in result.output
        assert "---" in result.output

    def test_export_with_custom_title(self):
        config = TXTExportConfig(title="My Custom Export")
        items = [{"title": "Item"}]
        result = self.exporter.export(items, config=config)
        assert "My Custom Export" in result.output

    def test_export_unicode_content(self):
        items = [
            {
                "title": "日本語記事",
                "body": "これはテストです。中文内容。",
            }
        ]
        result = self.exporter.export(items)
        assert "日本語記事" in result.output
        assert "これはテストです" in result.output

    def test_export_preserves_item_order(self):
        items = [
            {"title": "First", "body": "1"},
            {"title": "Second", "body": "2"},
            {"title": "Third", "body": "3"},
        ]
        result = self.exporter.export(items)
        first_pos = result.output.index("First")
        second_pos = result.output.index("Second")
        third_pos = result.output.index("Third")
        assert first_pos < second_pos < third_pos

    def test_export_with_date(self):
        items = [
            {
                "title": "Dated Article",
                "created_at": "2024-06-15T12:00:00",
            }
        ]
        result = self.exporter.export(items)
        assert "2024-06-15" in result.output

    def test_export_without_date(self):
        config = TXTExportConfig(include_date=False)
        items = [
            {
                "title": "Article",
                "created_at": "2024-06-15T12:00:00",
            }
        ]
        result = self.exporter.export(items, config=config)
        assert "2024-06-15" not in result.output

    def test_export_with_sort(self):
        config = TXTExportConfig(sort_by="title")
        items = [
            {"title": "Charlie", "body": "C"},
            {"title": "Alpha", "body": "A"},
            {"title": "Bravo", "body": "B"},
        ]
        result = self.exporter.export(items, config=config)
        alpha_pos = result.output.index("Alpha")
        bravo_pos = result.output.index("Bravo")
        charlie_pos = result.output.index("Charlie")
        assert alpha_pos < bravo_pos < charlie_pos

    def test_export_with_sort_reverse(self):
        config = TXTExportConfig(sort_by="title", sort_reverse=True)
        items = [
            {"title": "Charlie", "body": "C"},
            {"title": "Alpha", "body": "A"},
            {"title": "Bravo", "body": "B"},
        ]
        result = self.exporter.export(items, config=config)
        alpha_pos = result.output.index("Alpha")
        bravo_pos = result.output.index("Bravo")
        charlie_pos = result.output.index("Charlie")
        assert charlie_pos < bravo_pos < alpha_pos

    def test_export_with_limit(self):
        config = TXTExportConfig(title="Export", limit=2)
        items = [
            {"title": "Item Alpha", "body": "1"},
            {"title": "Item Beta", "body": "2"},
            {"title": "Item Gamma", "body": "3"},
        ]
        result = self.exporter.export(items, config=config)
        assert result.items_exported == 2
        assert "Item Alpha" in result.output
        assert "Item Beta" in result.output
        assert "Item Gamma" not in result.output

    def test_export_with_offset(self):
        config = TXTExportConfig(title="Export", offset=1, limit=1)
        items = [
            {"title": "Item Alpha", "body": "1"},
            {"title": "Item Beta", "body": "2"},
            {"title": "Item Gamma", "body": "3"},
        ]
        result = self.exporter.export(items, config=config)
        assert result.items_exported == 1
        assert "Item Beta" in result.output
        assert "Item Alpha" not in result.output
        assert "Item Gamma" not in result.output

    def test_export_markdown_style(self):
        config = TXTExportConfig(style=TXTExportStyle.MARKDOWN)
        items = [
            {"title": "Markdown Article", "body": "Some content here."}
        ]
        result = self.exporter.export(items, config=config)
        assert "# Markdown Article" in result.output

    def test_export_plain_style(self):
        config = TXTExportConfig(style=TXTExportStyle.PLAIN)
        items = [
            {"title": "Plain Article", "body": "Some content here."}
        ]
        result = self.exporter.export(items, config=config)
        assert "Plain Article" in result.output

    def test_export_to_file(self):
        items = [{"title": "File Test", "body": "Written to file"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filepath = f.name
        try:
            result = self.exporter.export_to_file(items, filepath)
            assert result.items_exported == 1
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            assert "File Test" in content
            assert "Written to file" in content
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_export_to_file_with_encoding(self):
        config = TXTExportConfig(encoding="utf-8")
        items = [{"title": "Unicode 测试", "body": "中文内容"}]
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            filepath = f.name
        try:
            result = self.exporter.export_to_file(items, filepath, config=config)
            assert result.items_exported == 1
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
            assert "Unicode 测试" in content
        finally:
            if os.path.exists(filepath):
                os.unlink(filepath)

    def test_export_large_dataset(self):
        items = [{"title": f"Article {i}", "body": f"Body content {i}"} for i in range(500)]
        result = self.exporter.export(items)
        assert result.items_exported == 500

    def test_export_with_long_lines_no_wrap(self):
        config = TXTExportConfig(wrap_text=False, max_line_length=200)
        long_text = "A" * 300
        items = [{"title": "Long", "body": long_text}]
        result = self.exporter.export(items, config=config)
        assert long_text in result.output

    def test_export_with_tags_as_list(self):
        items = [
            {
                "title": "Tagged",
                "tags": ["one", "two", "three"],
            }
        ]
        result = self.exporter.export(items)
        assert "one" in result.output
        assert "two" in result.output
        assert "three" in result.output

    def test_export_with_tags_as_string(self):
        items = [
            {
                "title": "Tagged",
                "tags": "one, two, three",
            }
        ]
        result = self.exporter.export(items)
        assert "one" in result.output

    def test_export_with_filter_fn(self):
        items = [
            {"title": "Keep", "score": 10},
            {"title": "Skip", "score": 1},
            {"title": "Keep Too", "score": 8},
        ]
        result = self.exporter.export(
            items,
            filter_fn=lambda item: item.get("score", 0) >= 5,
        )
        assert result.items_exported == 2
        assert "Keep" in result.output
        assert "Skip" not in result.output
        assert "Keep Too" in result.output

    def test_export_with_sort_key(self):
        items = [
            {"title": "Item Charlie", "score": 3},
            {"title": "Item Alpha", "score": 1},
            {"title": "Item Bravo", "score": 2},
        ]
        result = self.exporter.export(
            items,
            sort_key=lambda item: item.get("score", 0),
        )
        alpha_pos = result.output.index("Item Alpha")
        bravo_pos = result.output.index("Item Bravo")
        charlie_pos = result.output.index("Item Charlie")
        assert alpha_pos < bravo_pos < charlie_pos

    def test_export_result_has_style(self):
        result = self.exporter.export([{"title": "Test"}])
        assert result.style == "plain"

    def test_export_markdown_result_has_style(self):
        config = TXTExportConfig(style=TXTExportStyle.MARKDOWN)
        result = self.exporter.export([{"title": "Test"}], config=config)
        assert result.style == "markdown"

    def test_export_with_include_fields(self):
        config = TXTExportConfig(include_fields=["title", "body"])
        items = [
            {
                "title": "Filtered",
                "url": "http://example.com",
                "body": "Body text",
                "secret": "hidden",
            }
        ]
        result = self.exporter.export(items, config=config)
        assert "Filtered" in result.output
        assert "Body text" in result.output
        assert "hidden" not in result.output

    def test_export_with_exclude_fields(self):
        config = TXTExportConfig(exclude_fields=["secret"])
        items = [
            {
                "title": "Filtered",
                "body": "Body text",
                "secret": "hidden",
            }
        ]
        result = self.exporter.export(items, config=config)
        assert "Filtered" in result.output
        assert "hidden" not in result.output

    def test_export_handles_multiline_body(self):
        items = [
            {
                "title": "Multiline",
                "body": "First line.\nSecond line.\nThird line.",
            }
        ]
        result = self.exporter.export(items)
        assert "First line" in result.output
        assert "Second line" in result.output
        assert "Third line" in result.output

    def test_export_with_content_field(self):
        items = [
            {
                "title": "Content Field",
                "content": "Using content field instead of body",
            }
        ]
        result = self.exporter.export(items)
        assert "Using content field instead of body" in result.output

    def test_export_with_text_field(self):
        items = [
            {
                "title": "Text Field",
                "text": "Using text field instead of body",
            }
        ]
        result = self.exporter.export(items)
        assert "Using text field instead of body" in result.output

    def test_export_empty_items_list(self):
        result = self.exporter.export([])
        assert result.items_exported == 0
        assert result.output == ""
        assert result.errors == []

    def test_export_items_with_no_title(self):
        items = [
            {
                "body": "Untitled article",
            }
        ]
        result = self.exporter.export(items)
        assert result.items_exported == 1
        assert "Untitled article" in result.output

    def test_export_with_created_at_datetime(self):
        from datetime import datetime, timezone
        items = [
            {
                "title": "Datetime Test",
                "created_at": datetime(2024, 3, 15, 10, 30, 0, tzinfo=timezone.utc),
            }
        ]
        result = self.exporter.export(items)
        assert "2024-03-15" in result.output

    def test_export_with_updated_at(self):
        items = [
            {
                "title": "Updated Article",
                "created_at": "2024-01-01T00:00:00",
                "updated_at": "2024-06-01T00:00:00",
            }
        ]
        result = self.exporter.export(items)
        assert "2024-06-01" in result.output
