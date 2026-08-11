"""Tests for the Markdown export module."""

from pathlib import Path

from personal_index.content_export.markdown_export import MarkdownExporter


class TestMarkdownExporter:
    def setup_method(self) -> None:
        self.exporter = MarkdownExporter()
        self.items = [
            {
                "id": "1",
                "title": "Test Article",
                "url": "https://example.com/article",
                "description": "A test article about Python.",
                "tags": ["python", "web"],
                "score": 0.85,
                "bookmarked": True,
                "metadata": {"author": "Alice", "date": "2024-01-01"},
            },
            {
                "id": "2",
                "title": "Another Article",
                "url": "https://example.com/other",
                "tags": ["javascript"],
                "score": 0.72,
                "bookmarked": False,
            },
        ]

    def test_export_single_item(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "## Test Article" in result
        assert "[Test Article](https://example.com/article)" in result
        assert "A test article about Python." in result

    def test_export_item_tags(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "`python`" in result
        assert "`web`" in result

    def test_export_item_bookmarked(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "*Bookmarked*" in result

    def test_export_item_score(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "Score" in result

    def test_export_item_metadata(self) -> None:
        result = self.exporter.export_item(self.items[0])
        assert "### Metadata" in result
        assert "author" in result

    def test_export_multiple_items(self) -> None:
        result = self.exporter.export_items(self.items)
        assert "# Content Export" in result
        assert "## Test Article" in result
        assert "## Another Article" in result

    def test_export_to_file(self, tmp_path: Path) -> None:
        filepath = tmp_path / "export.md"
        count = self.exporter.export_to_file(self.items, filepath)
        assert count == 2
        assert filepath.exists()
        content = filepath.read_text()
        assert "## Test Article" in content

    def test_export_table(self) -> None:
        result = self.exporter.export_table(self.items)
        lines = result.split("\n")
        assert len(lines) == 4  # header + separator + 2 rows
        assert "|" in lines[0]
        assert "---" in lines[1]

    def test_export_table_custom_columns(self) -> None:
        result = self.exporter.export_table(
            self.items, columns=["title", "score"],
        )
        lines = result.split("\n")
        assert "title" in lines[0]
        assert "score" in lines[0]
        assert "url" not in lines[0]

    def test_export_table_boolean(self) -> None:
        result = self.exporter.export_table(self.items)
        assert "Yes" in result or "No" in result

    def test_export_table_empty(self) -> None:
        result = self.exporter.export_table([])
        assert result == ""

    def test_export_untitled_item(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.exporter.export_item(item)
        assert "## Untitled" in result

    def test_export_item_no_url(self) -> None:
        item = {"id": "1", "title": "No URL"}
        result = self.exporter.export_item(item)
        assert "http" not in result
