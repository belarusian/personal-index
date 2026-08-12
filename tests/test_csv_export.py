"""Tests for the CSV export module."""

from pathlib import Path

from personal_index.content_export.csv_export import (
    CsvExporter,
    CsvExportOptions,
)


class TestCsvExportOptions:
    def test_defaults(self) -> None:
        opts = CsvExportOptions()
        assert opts.delimiter == ","
        assert opts.quotechar == '"'
        assert opts.include_header is True
        assert opts.flatten_nested is True


class TestCsvExporter:
    def setup_method(self) -> None:
        self.exporter = CsvExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "tags": ["python", "web"],
                "metadata": {"author": "Alice", "date": "2024-01-01"},
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

    def test_export_basic(self) -> None:
        result = self.exporter.export_items(self.items)
        lines = result.strip().split("\n")
        assert len(lines) == 3  # header + 2 items
        assert "id" in lines[0]
        assert "title" in lines[0]

    def test_export_no_header(self) -> None:
        opts = CsvExportOptions(include_header=False)
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        lines = result.strip().split("\n")
        assert len(lines) == 2

    def test_export_flattened_nested(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "metadata.author" in result

    def test_export_no_flatten(self) -> None:
        opts = CsvExportOptions(flatten_nested=False)
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "metadata" in result
        assert "metadata.author" not in result

    def test_export_tags_as_string(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "python; web" in result

    def test_export_boolean(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "true" in result.lower()

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.csv"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        content = filepath.read_text()
        assert "id" in content

    def test_export_empty(self) -> None:
        result = self.exporter.export_items([])
        assert result == ""

    def test_custom_delimiter(self) -> None:
        opts = CsvExportOptions(delimiter="\t")
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "\t" in result

    def test_column_selection(self) -> None:
        opts = CsvExportOptions(columns=["id", "title"])
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        lines = result.strip().split("\n")
        assert "url" not in lines[0]
        assert "id" in lines[0]
        assert "title" in lines[0]

    def test_none_values(self) -> None:
        items = [{"id": "1", "title": None}]
        result = self.exporter.export_items(items)
        assert result.strip().split("\n")[1] == '1,""'

    def test_custom_separator_nested(self) -> None:
        opts = CsvExportOptions(separator_nested="_")
        exporter = CsvExporter(options=opts)
        result = exporter.export_items(self.items)
        assert "metadata_author" in result
