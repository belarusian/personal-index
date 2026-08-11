"""Integration tests for content export functionality."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp


class TestExportIntegration:
    """Test content export end-to-end."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_export_markdown(self):
        """Exporting to markdown should produce valid output."""
        from personal_index.export_markdown import export_to_md

        items = [
            {"title": "Test Article", "url": "https://example.com/1", "score": 0.9},
            {"title": "Another Article", "url": "https://example.com/2", "score": 0.7},
        ]
        md = export_to_md(items)
        assert "# Personal Index" in md
        assert "Test Article" in md
        assert "Another Article" in md

    def test_export_csv(self):
        """Exporting to CSV should produce valid output."""
        from personal_index.content_export_csv import export_to_csv

        items = [
            {"title": "Test", "url": "https://example.com/1", "score": 0.9},
        ]
        csv_data = export_to_csv(items)
        assert "title" in csv_data
        assert "Test" in csv_data

    def test_export_json(self):
        """Exporting to JSON should produce valid output."""
        import json
        from personal_index.export import export_items

        items = [
            {"title": "Test", "url": "https://example.com/1", "score": 0.9},
        ]
        json_data = export_items(items)
        parsed = json.loads(json_data)
        assert len(parsed) == 1
        assert parsed[0]["title"] == "Test"

    def test_export_empty(self):
        """Exporting empty list should produce valid output."""
        from personal_index.export_markdown import export_to_md
        md = export_to_md([])
        assert "# Personal Index" in md

    def test_export_preserves_order(self):
        """Export should preserve item order."""
        from personal_index.export_markdown import export_to_md

        items = [
            {"title": f"Article {i}", "url": f"https://example.com/{i}", "score": 1.0 - i * 0.1}
            for i in range(5)
        ]
        md = export_to_md(items)
        # Check that articles appear in order
        pos1 = md.index("Article 0")
        pos2 = md.index("Article 4")
        assert pos1 < pos2

    def test_export_with_tags(self):
        """Export should include tags if present."""
        from personal_index.export_markdown import export_to_md

        items = [
            {"title": "Tagged Article", "url": "https://example.com/1", "score": 0.9,
             "tags": ["python", "tutorial"]},
        ]
        md = export_to_md(items)
        assert "python" in md
        assert "tutorial" in md
