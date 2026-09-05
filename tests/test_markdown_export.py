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


class TestExportItemPinning:
    """Pinning tests for MarkdownExporter.export_item conditional rendering."""

    def setup_method(self) -> None:
        self.exporter = MarkdownExporter()

    def test_heading_default_untitled(self) -> None:
        """Step 1: level-2 heading with default 'Untitled' when title absent."""
        result = self.exporter.export_item({"id": "1"})
        assert "## Untitled" in result

    def test_heading_with_title(self) -> None:
        """Step 1: level-2 heading uses the item title."""
        result = self.exporter.export_item({"id": "1", "title": "My Title"})
        assert "## My Title" in result

    def test_url_link_rendered_when_present(self) -> None:
        """Step 2: markdown link rendered when url is non-empty."""
        result = self.exporter.export_item(
            {"id": "1", "title": "T", "url": "https://example.com/x"}
        )
        assert "[T](https://example.com/x)" in result

    def test_url_link_absent_when_no_url(self) -> None:
        """Step 2: no markdown link when url is absent/empty."""
        result = self.exporter.export_item({"id": "1", "title": "T"})
        assert "](" not in result

    def test_description_rendered_when_present(self) -> None:
        """Step 3: description paragraph rendered when present."""
        result = self.exporter.export_item(
            {"id": "1", "title": "T", "description": "Some description."}
        )
        assert "Some description." in result

    def test_description_absent_when_missing(self) -> None:
        """Step 3: no description text when absent."""
        result = self.exporter.export_item({"id": "1", "title": "T"})
        assert "description" not in result.lower()

    def test_tags_rendered_when_present(self) -> None:
        """Step 4: tags section with backtick-wrapped comma-separated tags."""
        result = self.exporter.export_item(
            {"id": "1", "title": "T", "tags": ["a", "b"]}
        )
        assert "**Tags:**" in result
        assert "`a`, `b`" in result

    def test_tags_absent_when_missing(self) -> None:
        """Step 4: no tags section when tags absent."""
        result = self.exporter.export_item({"id": "1", "title": "T"})
        assert "**Tags:**" not in result

    def test_bookmarked_rendered_when_truthy(self) -> None:
        """Step 5: italic *Bookmarked* marker when bookmarked."""
        result = self.exporter.export_item({"id": "1", "title": "T", "bookmarked": True})
        assert "*Bookmarked*" in result

    def test_bookmarked_absent_when_falsy(self) -> None:
        """Step 5: no bookmarked marker when not bookmarked."""
        result = self.exporter.export_item({"id": "1", "title": "T", "bookmarked": False})
        assert "*Bookmarked*" not in result

    def test_score_rendered_when_not_none(self) -> None:
        """Step 6: bold Score line with 2-decimal when score is not None."""
        result = self.exporter.export_item({"id": "1", "title": "T", "score": 0.85})
        assert "**Score:** 0.85" in result

    def test_score_absent_when_none(self) -> None:
        """Step 6: no Score line when score is None/absent."""
        result = self.exporter.export_item({"id": "1", "title": "T", "score": None})
        assert "**Score:**" not in result

    def test_metadata_rendered_when_present(self) -> None:
        """Step 7: metadata section with key-value bullets when present."""
        result = self.exporter.export_item(
            {"id": "1", "title": "T", "metadata": {"author": "Alice"}}
        )
        assert "### Metadata" in result
        assert "- **author:** Alice" in result

    def test_metadata_absent_when_missing(self) -> None:
        """Step 7: no metadata section when metadata absent."""
        result = self.exporter.export_item({"id": "1", "title": "T"})
        assert "### Metadata" not in result

    def test_full_item_all_sections(self) -> None:
        """All 7 sections rendered in order for a fully-populated item."""
        item = {
            "id": "1",
            "title": "Full",
            "url": "https://example.com/full",
            "description": "Full description.",
            "tags": ["x"],
            "score": 1.0,
            "bookmarked": True,
            "metadata": {"k": "v"},
        }
        result = self.exporter.export_item(item)
        # Verify ordering: heading first, then link, description, tags, bookmarked, score, metadata
        idx_heading = result.index("## Full")
        idx_link = result.index("[Full](https://example.com/full)")
        idx_desc = result.index("Full description.")
        idx_tags = result.index("**Tags:**")
        idx_bookmark = result.index("*Bookmarked*")
        idx_score = result.index("**Score:** 1.00")
        idx_meta = result.index("### Metadata")
        assert idx_heading < idx_link < idx_desc < idx_tags < idx_bookmark < idx_score < idx_meta
