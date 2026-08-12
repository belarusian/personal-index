"""Tests for content_export_csv module - export content as CSV."""

from __future__ import annotations

import csv
import io

from personal_index.content_export_csv import (
    CSVExporter,
    ExportFormat,
)


class TestCSVExporter:
    """Tests for CSVExporter."""

    def setup_method(self):
        self.exporter = CSVExporter()

    def test_export_empty(self):
        result = self.exporter.export([])
        assert result == ""

    def test_export_single_item(self):
        items = [{"id": "1", "title": "Test", "url": "http://example.com"}]
        result = self.exporter.export(items)
        lines = result.strip().split("\n")
        assert len(lines) == 2  # header + 1 data row

    def test_export_multiple_items(self):
        items = [
            {"id": "1", "title": "A", "url": "http://a.com"},
            {"id": "2", "title": "B", "url": "http://b.com"},
        ]
        result = self.exporter.export(items)
        lines = result.strip().split("\n")
        assert len(lines) == 3

    def test_export_headers(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items)
        assert "id" in result.split("\n")[0]
        assert "title" in result.split("\n")[0]

    def test_export_with_custom_columns(self):
        items = [{"id": "1", "title": "A", "extra": "X"}]
        result = self.exporter.export(items, columns=["id", "title"])
        assert "extra" not in result

    def test_export_with_custom_delimiter(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, delimiter="\t")
        assert "\t" in result

    def test_export_handles_special_chars(self):
        items = [{"id": "1", "title": "Test, with comma", "desc": "Has \"quotes\""}]
        result = self.exporter.export(items)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 2
        assert rows[1][1] == "Test, with comma"

    def test_export_handles_newlines(self):
        items = [{"id": "1", "title": "Line1\nLine2"}]
        result = self.exporter.export(items)
        reader = csv.reader(io.StringIO(result))
        rows = list(reader)
        assert rows[1][1] == "Line1\nLine2"

    def test_export_with_default_columns(self):
        items = [
            {
                "id": "1",
                "title": "Test",
                "url": "http://example.com",
                "content_type": "article",
                "created_at": "2024-01-01",
            }
        ]
        result = self.exporter.export(items)
        assert "id" in result
        assert "title" in result
        assert "url" in result

    def test_export_preserves_order(self):
        items = [
            {"id": "3", "title": "C"},
            {"id": "1", "title": "A"},
            {"id": "2", "title": "B"},
        ]
        result = self.exporter.export(items)
        lines = result.strip().split("\n")
        assert "C" in lines[1]
        assert "A" in lines[2]
        assert "B" in lines[3]

    def test_export_with_empty_values(self):
        items = [{"id": "1", "title": "", "url": None}]
        result = self.exporter.export(items)
        assert result.strip() != ""

    def test_export_unicode(self):
        items = [{"id": "1", "title": "日本語テスト", "desc": "中文"}]
        result = self.exporter.export(items)
        assert "日本語テスト" in result
        assert "中文" in result

    def test_export_to_file(self, tmp_path):
        items = [{"id": "1", "title": "Test"}]
        filepath = tmp_path / "test.csv"
        self.exporter.export_to_file(items, str(filepath))
        assert filepath.exists()
        content = filepath.read_text()
        assert "Test" in content

    def test_export_to_file_overwrite(self, tmp_path):
        filepath = tmp_path / "test.csv"
        filepath.write_text("old content")
        items = [{"id": "1", "title": "New"}]
        self.exporter.export_to_file(items, str(filepath))
        content = filepath.read_text()
        assert "New" in content
        assert "old" not in content

    def test_export_with_quoting(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, quoting=csv.QUOTE_ALL)
        assert '"' in result

    def test_export_large_dataset(self):
        items = [{"id": str(i), "title": f"Title {i}"} for i in range(1000)]
        result = self.exporter.export(items)
        lines = result.strip().split("\n")
        assert len(lines) == 1001  # header + 1000 rows

    def test_export_with_include_header_false(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, include_header=False)
        lines = result.strip().split("\n")
        assert len(lines) == 1
        assert "id" not in lines[0]

    def test_export_returns_csv_string(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items)
        assert isinstance(result, str)

    def test_export_with_datetime_values(self):
        from datetime import datetime, timezone
        items = [{"id": "1", "title": "Test", "created_at": datetime(2024, 1, 1, tzinfo=timezone.utc)}]
        result = self.exporter.export(items)
        assert "2024" in result

    def test_export_with_boolean_values(self):
        items = [{"id": "1", "title": "Test", "is_favorite": True}]
        result = self.exporter.export(items)
        assert "True" in result

    def test_export_with_numeric_values(self):
        items = [{"id": "1", "title": "Test", "score": 95.5}]
        result = self.exporter.export(items)
        assert "95.5" in result

    def test_export_with_list_values(self):
        items = [{"id": "1", "title": "Test", "tags": ["a", "b", "c"]}]
        result = self.exporter.export(items)
        assert "a" in result
        assert "b" in result

    def test_export_with_dict_values(self):
        items = [{"id": "1", "title": "Test", "metadata": {"key": "value"}}]
        result = self.exporter.export(items)
        assert "key" in result or "value" in result

    def test_export_custom_column_names(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(
            items,
            column_names={"id": "ID", "title": "Title"},
        )
        header = result.split("\n")[0]
        assert "ID" in header
        assert "Title" in header

    def test_export_with_filter(self):
        items = [
            {"id": "1", "title": "A", "type": "article"},
            {"id": "2", "title": "B", "type": "video"},
            {"id": "3", "title": "C", "type": "article"},
        ]
        result = self.exporter.export(items, filter_fn=lambda x: x["type"] == "article")
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 articles

    def test_export_with_sort(self):
        items = [
            {"id": "3", "title": "C"},
            {"id": "1", "title": "A"},
            {"id": "2", "title": "B"},
        ]
        result = self.exporter.export(items, sort_key=lambda x: x["title"])
        lines = result.strip().split("\n")
        assert "A" in lines[1]
        assert "B" in lines[2]
        assert "C" in lines[3]

    def test_export_with_limit(self):
        items = [{"id": str(i), "title": f"T{i}"} for i in range(10)]
        result = self.exporter.export(items, limit=3)
        lines = result.strip().split("\n")
        assert len(lines) == 4  # header + 3 rows

    def test_export_with_offset(self):
        items = [{"id": str(i), "title": f"T{i}"} for i in range(10)]
        result = self.exporter.export(items, offset=5)
        lines = result.strip().split("\n")
        assert len(lines) == 6  # header + 5 rows

    def test_export_format_csv(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, export_format=ExportFormat.CSV)
        assert isinstance(result, str)

    def test_export_format_tsv(self):
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, export_format=ExportFormat.TSV)
        assert "\t" in result

    def test_export_format_json_lines(self):
        import json
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, export_format=ExportFormat.JSON_LINES)
        lines = result.strip().split("\n")
        for line in lines:
            obj = json.loads(line)
            assert isinstance(obj, dict)

    def test_export_format_json(self):
        import json
        items = [{"id": "1", "title": "Test"}]
        result = self.exporter.export(items, export_format=ExportFormat.JSON)
        data = json.loads(result)
        assert isinstance(data, list)
        assert len(data) == 1

    def test_export_get_stats(self):
        items = [{"id": str(i), "title": f"T{i}"} for i in range(10)]
        self.exporter.export(items)
        stats = self.exporter.get_stats(items)
        assert stats["total_items"] == 10
        assert stats["columns"] > 0

    def test_export_get_stats_empty(self):
        stats = self.exporter.get_stats([])
        assert stats["total_items"] == 0

    def test_export_with_encoding(self):
        items = [{"id": "1", "title": "日本語"}]
        result = self.exporter.export(items, encoding="utf-8")
        assert "日本語" in result

    def test_export_roundtrip(self):
        items = [{"id": "1", "title": "Test", "url": "http://example.com"}]
        result = self.exporter.export(items)
        reader = csv.DictReader(io.StringIO(result))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["id"] == "1"
        assert rows[0]["title"] == "Test"
