"""Tests for content export as JSON."""

import json
import pytest
from datetime import datetime, timezone
from personal_index.content_export_json import (
    JSONExporter,
    JSONExportConfig,
    JSONExportResult,
    JSONExportFormat,
)


class TestJSONExportConfig:
    def test_default_config(self):
        config = JSONExportConfig()
        assert config.pretty_print is True
        assert config.include_metadata is False
        assert config.encoding == "utf-8"

    def test_compact_config(self):
        config = JSONExportConfig(pretty_print=False)
        assert config.pretty_print is False

    def test_exclude_metadata(self):
        config = JSONExportConfig(include_metadata=False)
        assert config.include_metadata is False

    def test_custom_encoding(self):
        config = JSONExportConfig(encoding="ascii")
        assert config.encoding == "ascii"

    def test_include_fields(self):
        config = JSONExportConfig(include_fields=["title", "url"])
        assert config.include_fields == ["title", "url"]

    def test_exclude_fields(self):
        config = JSONExportConfig(exclude_fields=["content"])
        assert config.exclude_fields == ["content"]

    def test_to_dict(self):
        config = JSONExportConfig(pretty_print=False, include_metadata=False)
        d = config.to_dict()
        assert d["pretty_print"] is False
        assert d["include_metadata"] is False

    def test_from_dict(self):
        d = {"pretty_print": False, "include_metadata": False, "encoding": "ascii"}
        config = JSONExportConfig.from_dict(d)
        assert config.pretty_print is False
        assert config.include_metadata is False
        assert config.encoding == "ascii"


class TestJSONExportFormat:
    def test_lines_format(self):
        assert JSONExportFormat.LINES.value == "lines"

    def test_array_format(self):
        assert JSONExportFormat.ARRAY.value == "array"

    def test_object_format(self):
        assert JSONExportFormat.OBJECT.value == "object"

    def test_from_string(self):
        fmt = JSONExportFormat.from_string("lines")
        assert fmt == JSONExportFormat.LINES

    def test_from_string_invalid(self):
        fmt = JSONExportFormat.from_string("invalid")
        assert fmt == JSONExportFormat.ARRAY


class TestJSONExportResult:
    def test_default_result(self):
        result = JSONExportResult()
        assert result.items_exported == 0
        assert result.output is None
        assert result.errors == []

    def test_result_with_data(self):
        result = JSONExportResult(items_exported=5, output='{"test": true}')
        assert result.items_exported == 5
        assert result.output == '{"test": true}'

    def test_result_with_errors(self):
        result = JSONExportResult(items_exported=3, errors=["error1"])
        assert len(result.errors) == 1
        assert result.errors[0] == "error1"

    def test_to_dict(self):
        result = JSONExportResult(items_exported=10, format="array")
        d = result.to_dict()
        assert d["items_exported"] == 10
        assert d["format"] == "array"


class TestJSONExporterExportArray:
    def test_export_empty(self):
        exporter = JSONExporter()
        result = exporter.export([])
        assert result.items_exported == 0
        assert result.output == "[]"

    def test_export_single_item(self):
        items = [{"title": "Test", "url": "http://example.com"}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["title"] == "Test"

    def test_export_multiple_items(self):
        items = [
            {"title": "A", "url": "http://a.com"},
            {"title": "B", "url": "http://b.com"},
        ]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert len(data) == 2

    def test_export_preserves_fields(self):
        items = [{"title": "Test", "score": 5.0, "tags": ["python"]}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert data[0]["score"] == 5.0
        assert data[0]["tags"] == ["python"]

    def test_export_with_metadata(self):
        items = [{"title": "Test"}]
        exporter = JSONExporter()
        config = JSONExportConfig(include_metadata=True)
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert "metadata" in data
        assert "exported_at" in data["metadata"]

    def test_export_without_metadata(self):
        items = [{"title": "Test"}]
        exporter = JSONExporter()
        config = JSONExportConfig(include_metadata=False)
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert "metadata" not in data


class TestJSONExporterExportLines:
    def test_export_lines_empty(self):
        exporter = JSONExporter()
        result = exporter.export([], format=JSONExportFormat.LINES)
        assert result.output == ""

    def test_export_lines_single(self):
        items = [{"title": "Test"}]
        exporter = JSONExporter()
        result = exporter.export(items, format=JSONExportFormat.LINES)
        lines = result.output.strip().split("\n")
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["title"] == "Test"

    def test_export_lines_multiple(self):
        items = [{"title": "A"}, {"title": "B"}, {"title": "C"}]
        exporter = JSONExporter()
        result = exporter.export(items, format=JSONExportFormat.LINES)
        lines = result.output.strip().split("\n")
        assert len(lines) == 3


class TestJSONExporterExportObject:
    def test_export_object(self):
        items = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
        exporter = JSONExporter()
        result = exporter.export(items, format=JSONExportFormat.OBJECT)
        data = json.loads(result.output)
        assert "1" in data
        assert "2" in data
        assert data["1"]["title"] == "A"

    def test_export_object_no_id(self):
        items = [{"title": "A"}, {"title": "B"}]
        exporter = JSONExporter()
        result = exporter.export(items, format=JSONExportFormat.OBJECT)
        data = json.loads(result.output)
        assert "0" in data
        assert "1" in data


class TestJSONExporterFilterFields:
    def test_include_fields(self):
        items = [{"title": "Test", "url": "http://x.com", "content": "body"}]
        exporter = JSONExporter()
        config = JSONExportConfig(include_fields=["title", "url"])
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert "title" in data[0]
        assert "url" in data[0]
        assert "content" not in data[0]

    def test_exclude_fields(self):
        items = [{"title": "Test", "url": "http://x.com", "content": "body"}]
        exporter = JSONExporter()
        config = JSONExportConfig(exclude_fields=["content"])
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert "title" in data[0]
        assert "content" not in data[0]

    def test_include_takes_precedence(self):
        items = [{"title": "Test", "url": "http://x.com", "content": "body"}]
        exporter = JSONExporter()
        config = JSONExportConfig(
            include_fields=["title", "url"],
            exclude_fields=["url"],
        )
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert "title" in data[0]
        assert "url" not in data[0]


class TestJSONExporterCompact:
    def test_compact_output(self):
        items = [{"title": "Test"}]
        exporter = JSONExporter()
        config = JSONExportConfig(pretty_print=False)
        result = exporter.export(items, config=config)
        assert "\n" not in result.output.replace(" ", "") or len(result.output.strip().split()) == 1

    def test_pretty_output(self):
        items = [{"title": "Test"}]
        exporter = JSONExporter()
        config = JSONExportConfig(pretty_print=True)
        result = exporter.export(items, config=config)
        assert "\n" in result.output or "  " in result.output


class TestJSONExporterEdgeCases:
    def test_export_unicode(self):
        items = [{"title": "日本語テスト", "content": "中文内容"}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert data[0]["title"] == "日本語テスト"

    def test_export_null_values(self):
        items = [{"title": None, "url": "http://x.com"}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert data[0]["title"] is None

    def test_export_nested_objects(self):
        items = [{"title": "Test", "meta": {"key": "value"}}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert data[0]["meta"]["key"] == "value"

    def test_export_datetime(self):
        now = datetime.now(timezone.utc)
        items = [{"title": "Test", "created_at": now.isoformat()}]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert "created_at" in data[0]

    def test_export_large_dataset(self):
        items = [{"title": f"Item {i}", "score": float(i)} for i in range(1000)]
        exporter = JSONExporter()
        result = exporter.export(items)
        data = json.loads(result.output)
        assert len(data) == 1000

    def test_export_with_sort(self):
        items = [
            {"title": "C", "score": 3.0},
            {"title": "A", "score": 1.0},
            {"title": "B", "score": 2.0},
        ]
        exporter = JSONExporter()
        config = JSONExportConfig(sort_by="score")
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert data[0]["title"] == "A"
        assert data[2]["title"] == "C"

    def test_export_with_limit(self):
        items = [{"title": f"Item {i}"} for i in range(100)]
        exporter = JSONExporter()
        config = JSONExportConfig(limit=10)
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert len(data) == 10

    def test_export_with_offset(self):
        items = [{"title": f"Item {i}"} for i in range(100)]
        exporter = JSONExporter()
        config = JSONExportConfig(offset=5, limit=10)
        result = exporter.export(items, config=config)
        data = json.loads(result.output)
        assert len(data) == 10
        assert data[0]["title"] == "Item 5"
