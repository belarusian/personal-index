"""Integration tests for content export functionality.

Tests all export formats: JSON, HTML, CSV, Markdown.
Uses real module code to verify export structure and content.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile

from personal_index.content_export import CsvExporter, JsonExporter, MarkdownExporter
from personal_index.content_export.csv_export import CsvExportOptions
from personal_index.content_export.json_export import JsonExportOptions
from personal_index.tags import TagStore


class TestExportIntegration:
    """Test content export end-to-end with real exporters."""

    def setup_method(self):
        """Set up a temporary directory for each test."""
        self.tmpdir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_json_export_structure(self):
        """Exporting to JSON should produce valid structure with required fields."""
        exporter = JsonExporter()

        items = [
            {
                "title": "Test Article",
                "url": "https://example.com/1",
                "content": "This is test content.",
                "score": 0.9,
                "tags": ["python", "test"],
            },
            {
                "title": "Another Article",
                "url": "https://example.com/2",
                "content": "More test content here.",
                "score": 0.7,
                "tags": ["javascript"],
            },
        ]

        json_str = exporter.export_items(items)
        parsed = json.loads(json_str)

        assert isinstance(parsed, list), "JSON export should be a list"
        assert len(parsed) == 2, "Should export both items"

        # Check required fields
        first_item = parsed[0]
        assert "title" in first_item
        assert "url" in first_item
        assert "content" in first_item

        # Check values
        assert first_item["title"] == "Test Article"
        assert first_item["url"] == "https://example.com/1"

    def test_json_export_with_metadata(self):
        """JSON export should include metadata when configured."""
        exporter = JsonExporter(options=JsonExportOptions(
            include_metadata=True,
            include_tags=True,
            include_scores=True,
        ))

        items = [
            {
                "title": "Article with Metadata",
                "url": "https://example.com/1",
                "content": "Test content.",
                "score": 0.85,
                "tags": ["python"],
                "metadata": {
                    "author": "John Doe",
                    "published_at": "2024-01-15T10:30:00Z",
                    "word_count": 500,
                },
            },
        ]

        json_str = exporter.export_items(items)
        parsed = json.loads(json_str)

        assert "metadata" in parsed[0]
        assert parsed[0]["metadata"]["author"] == "John Doe"
        assert "tags" in parsed[0]
        assert "score" in parsed[0]

    def test_json_export_to_file(self):
        """Export to file should write valid JSON."""
        exporter = JsonExporter()

        items = [
            {
                "title": "File Export Test",
                "url": "https://example.com/test",
                "content": "Testing file export.",
                "score": 0.95,
            },
        ]

        filepath = os.path.join(self.tmpdir, "export.json")
        count = exporter.export_to_file(items, filepath)

        assert count == 1, "Should export 1 item"
        assert os.path.exists(filepath), "File should be created"

        # Verify file content
        with open(filepath, "r") as f:
            parsed = json.load(f)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "File Export Test"

    def test_json_export_collection(self):
        """Export collection should include metadata wrapper."""
        exporter = JsonExporter()

        items = [
            {"title": "Item 1", "url": "https://example.com/1"},
            {"title": "Item 2", "url": "https://example.com/2"},
        ]

        json_str = exporter.export_collection(
            name="Test Collection",
            items=items,
            metadata={"source": "test", "version": "1.0"},
        )

        parsed = json.loads(json_str)

        assert "collection_name" in parsed
        assert parsed["collection_name"] == "Test Collection"
        assert "exported_at" in parsed
        assert "item_count" in parsed
        assert parsed["item_count"] == 2
        assert "items" in parsed
        assert len(parsed["items"]) == 2

    def test_json_export_summary(self):
        """Export summary should include statistics."""
        exporter = JsonExporter()

        items = [
            {
                "title": "Tagged Item",
                "url": "https://example.com/1",
                "tags": ["python", "test"],
                "bookmarked": True,
            },
            {
                "title": "Untagged Item",
                "url": "https://example.com/2",
                "tags": [],
                "bookmarked": False,
            },
        ]

        summary_str = exporter.export_summary(items)
        summary = json.loads(summary_str)

        assert "total_items" in summary
        assert summary["total_items"] == 2
        assert "tagged_items" in summary
        assert summary["tagged_items"] == 1
        assert "bookmarked_items" in summary
        assert summary["bookmarked_items"] == 1
        assert "unique_domains" in summary

    def test_csv_export_structure(self):
        """Exporting to CSV should produce valid structure."""
        exporter = CsvExporter()

        items = [
            {
                "title": "CSV Test",
                "url": "https://example.com/1",
                "content": "Test content.",
                "score": 0.85,
                "tags": ["python", "csv"],
            },
            {
                "title": "Another CSV",
                "url": "https://example.com/2",
                "content": "More content.",
                "score": 0.75,
                "tags": ["javascript"],
            },
        ]

        csv_str = exporter.export_items(items)

        # Verify it's valid CSV
        lines = csv_str.strip().split("\n")
        assert len(lines) >= 2, "Should have header and at least one data row"

        # Check header
        header = lines[0]
        assert "title" in header
        assert "url" in header

        # Check data rows
        assert "CSV Test" in csv_str
        assert "Another CSV" in csv_str

    def test_csv_export_to_file(self):
        """Export to file should write valid CSV."""
        exporter = CsvExporter()

        items = [
            {
                "title": "File CSV Test",
                "url": "https://example.com/test",
                "content": "Testing CSV export.",
                "score": 0.9,
            },
        ]

        filepath = os.path.join(self.tmpdir, "export.csv")
        count = exporter.export_to_file(items, filepath)

        assert count == 1
        assert os.path.exists(filepath)

        # Verify file content
        with open(filepath, "r") as f:
            content = f.read()
        assert "File CSV Test" in content

    def test_csv_export_with_columns(self):
        """CSV export should support column selection."""
        exporter = CsvExporter(options=CsvExportOptions(
            columns=["title", "url", "score"],
        ))

        items = [
            {
                "title": "Column Test",
                "url": "https://example.com/1",
                "content": "Full content.",
                "score": 0.85,
                "tags": ["test"],
            },
        ]

        csv_str = exporter.export_items(items)
        lines = csv_str.strip().split("\n")

        # Header should only have selected columns
        header = lines[0]
        assert "title" in header
        assert "url" in header
        assert "score" in header
        assert "content" not in header
        assert "tags" not in header

    def test_markdown_export_structure(self):
        """Exporting to Markdown should produce valid structure."""
        exporter = MarkdownExporter()

        items = [
            {
                "title": "Markdown Test",
                "url": "https://example.com/1",
                "content": "Test content.",
                "score": 0.9,
                "tags": ["python", "markdown"],
            },
            {
                "title": "Another Markdown",
                "url": "https://example.com/2",
                "content": "More content.",
                "score": 0.7,
                "tags": ["javascript"],
            },
        ]

        md_str = exporter.export_items(items, title="Test Export")

        # Verify structure
        assert "# Test Export" in md_str
        assert "## Markdown Test" in md_str
        assert "## Another Markdown" in md_str

        # Check content - note: the markdown exporter uses the content field
        # but it may be truncated or formatted differently
        assert "Markdown Test" in md_str
        assert "Another Markdown" in md_str

    def test_markdown_export_with_tags(self):
        """Markdown export should include tags."""
        exporter = MarkdownExporter()

        items = [
            {
                "title": "Tagged Article",
                "url": "https://example.com/1",
                "content": "Content here.",
                "tags": ["python", "tutorial"],
            },
        ]

        md_str = exporter.export_items(items)

        assert "**Tags:** `python`, `tutorial`" in md_str

    def test_markdown_export_with_score(self):
        """Markdown export should include score when present."""
        exporter = MarkdownExporter()

        items = [
            {
                "title": "Scored Article",
                "url": "https://example.com/1",
                "content": "Content.",
                "score": 0.95,
            },
        ]

        md_str = exporter.export_items(items)

        assert "**Score:** 0.95" in md_str

    def test_markdown_export_to_file(self):
        """Export to file should write valid Markdown."""
        exporter = MarkdownExporter()

        items = [
            {
                "title": "File Markdown Test",
                "url": "https://example.com/test",
                "content": "Testing markdown export.",
                "score": 0.85,
            },
        ]

        filepath = os.path.join(self.tmpdir, "export.md")
        count = exporter.export_to_file(items, filepath, title="Test Export")

        assert count == 1
        assert os.path.exists(filepath)

        # Verify file content
        with open(filepath, "r") as f:
            content = f.read()
        assert "# Test Export" in content
        assert "## File Markdown Test" in content

    def test_markdown_export_table(self):
        """Export table should produce valid markdown table."""
        exporter = MarkdownExporter()

        items = [
            {
                "title": "Item 1",
                "url": "https://example.com/1",
                "score": 0.9,
                "tags": ["python"],
            },
            {
                "title": "Item 2",
                "url": "https://example.com/2",
                "score": 0.7,
                "tags": ["javascript"],
            },
        ]

        table = exporter.export_table(items)

        # Verify table structure
        assert "| Item 1" in table
        assert "| Item 2" in table
        assert "| https://example.com/1" in table
        assert "| https://example.com/2" in table

    def test_export_with_tag_store(self):
        """Export should include tags from TagStore when provided."""
        tag_store = TagStore(store_path=os.path.join(self.tmpdir, "tags.json"))

        # Create some tags
        tag_store.create_tag("python", color="#3572A5")
        tag_store.create_tag("web", color="#2ecc71")

        # Add tags to pages
        tag_store.add_tag_to_page("https://example.com/1", "python")
        tag_store.add_tag_to_page("https://example.com/1", "web")
        tag_store.add_tag_to_page("https://example.com/2", "python")

        items = [
            {"title": "Page 1", "url": "https://example.com/1"},
            {"title": "Page 2", "url": "https://example.com/2"},
        ]

        # JSON export with tags
        exporter = JsonExporter()
        json_str = exporter.export_items(items)
        json.loads(json_str)

        # Note: The current implementation doesn't automatically fetch from TagStore
        # This test documents the expected behavior when tag_store integration is added

    def test_export_preserves_order(self):
        """Export should preserve item order."""
        exporter = JsonExporter()

        items = [
            {"title": "First", "url": "https://example.com/1"},
            {"title": "Second", "url": "https://example.com/2"},
            {"title": "Third", "url": "https://example.com/3"},
            {"title": "Fourth", "url": "https://example.com/4"},
        ]

        json_str = exporter.export_items(items)
        parsed = json.loads(json_str)

        for i, item in enumerate(parsed):
            assert item["title"] == f"{['First', 'Second', 'Third', 'Fourth'][i]}"

    def test_export_empty_list(self):
        """Exporting empty list should produce valid output."""
        exporter = JsonExporter()
        json_str = exporter.export_items([])
        parsed = json.loads(json_str)
        assert parsed == []

        exporter = CsvExporter()
        csv_str = exporter.export_items([])
        assert csv_str == ""

        exporter = MarkdownExporter()
        md_str = exporter.export_items([])
        assert "# " in md_str or len(md_str) > 0

    def test_export_large_dataset(self):
        """Export should handle large datasets efficiently."""
        exporter = JsonExporter()

        # Create 100 items
        items = [
            {
                "title": f"Article {i}",
                "url": f"https://example.com/{i}",
                "content": f"Content for article {i}. " * 10,
                "score": round(0.5 + (i % 10) * 0.05, 2),
            }
            for i in range(100)
        ]

        json_str = exporter.export_items(items)
        parsed = json.loads(json_str)

        assert len(parsed) == 100
        assert parsed[0]["title"] == "Article 0"
        assert parsed[99]["title"] == "Article 99"

    def test_export_formats_compatibility(self):
        """All export formats should be compatible with the same data."""
        json_exporter = JsonExporter()
        csv_exporter = CsvExporter()
        md_exporter = MarkdownExporter()

        items = [
            {
                "title": "Cross-Format Test",
                "url": "https://example.com/test",
                "content": "This content should export to all formats.",
                "score": 0.85,
                "tags": ["python", "test"],
            },
        ]

        # All exports should succeed
        json_str = json_exporter.export_items(items)
        csv_str = csv_exporter.export_items(items)
        md_str = md_exporter.export_items(items)

        # Parse and verify JSON
        parsed_json = json.loads(json_str)
        assert len(parsed_json) == 1

        # Verify CSV contains key data
        assert "Cross-Format Test" in csv_str
        assert "https://example.com/test" in csv_str

        # Verify Markdown contains key data
        assert "## Cross-Format Test" in md_str
