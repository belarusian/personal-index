"""Tests for the JSON export module."""

import json
from pathlib import Path

import pytest

from personal_index.content_export.json_export import (
    JsonExportOptions,
    JsonExporter,
)


class TestJsonExportOptions:
    def test_defaults(self) -> None:
        opts = JsonExportOptions()
        assert opts.indent == 2
        assert opts.sort_keys is True
        assert opts.include_metadata is True
        assert opts.include_tags is True
        assert opts.include_scores is False
        assert opts.fields is None
        assert opts.exclude_fields == []


class TestJsonExporter:
    def setup_method(self) -> None:
        self.exporter = JsonExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "tags": ["python", "web"],
                "metadata": {"author": "Alice"},
                "score": 0.85,
                "bookmarked": True,
            },
            {
                "id": "2",
                "title": "Another Article",
                "url": "https://example.com/other",
                "tags": ["javascript"],
                "metadata": {"author": "Bob"},
                "score": 0.72,
                "bookmarked": False,
            },
        ]

    def test_export_single_item(self) -> None:
        result = self.exporter.export_item(self.items[0])
        data = json.loads(result)
        assert data["id"] == "1"
        assert data["title"] == "Test Article"

    def test_export_multiple_items(self) -> None:
        result = self.exporter.export_items(self.items)
        data = json.loads(result)
        assert len(data) == 2
        assert data[0]["id"] == "1"
        assert data[1]["id"] == "2"

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.json"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        data = json.loads(filepath.read_text())
        assert len(data) == 2

    def test_export_to_file_creates_dirs(self, tmp_path: Path) -> None:
        filepath = tmp_path / "sub" / "dir" / "export.json"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()

    def test_export_collection(self) -> None:
        result = self.exporter.export_collection(
            "My Collection", self.items,
            metadata={"created_by": "test"},
        )
        data = json.loads(result)
        assert data["collection_name"] == "My Collection"
        assert data["item_count"] == 2
        assert data["metadata"]["created_by"] == "test"

    def test_exclude_scores(self) -> None:
        opts = JsonExportOptions(include_scores=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "score" not in data

    def test_include_scores(self) -> None:
        opts = JsonExportOptions(include_scores=True)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "score" in data
        assert data["score"] == 0.85

    def test_exclude_tags(self) -> None:
        opts = JsonExportOptions(include_tags=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "tags" not in data

    def test_exclude_metadata(self) -> None:
        opts = JsonExportOptions(include_metadata=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "metadata" not in data

    def test_field_selection(self) -> None:
        opts = JsonExportOptions(fields=["id", "title"])
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert set(data.keys()) == {"id", "title"}

    def test_exclude_fields(self) -> None:
        opts = JsonExportOptions(exclude_fields=["tags", "metadata"])
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert "tags" not in data
        assert "metadata" not in data

    def test_compact_output(self) -> None:
        opts = JsonExportOptions(indent=None)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        assert "\n" not in result

    def test_export_summary(self) -> None:
        result = self.exporter.export_summary(self.items)
        data = json.loads(result)
        assert data["total_items"] == 2
        assert data["tagged_items"] == 2
        assert data["bookmarked_items"] == 1
        assert data["unique_domains"] == 1

    def test_export_empty_items(self) -> None:
        result = self.exporter.export_items([])
        data = json.loads(result)
        assert data == []

    def test_export_preserves_order(self) -> None:
        opts = JsonExportOptions(sort_keys=False)
        exporter = JsonExporter(options=opts)
        result = exporter.export_item(self.items[0])
        data = json.loads(result)
        assert list(data.keys())[0] == "id"
