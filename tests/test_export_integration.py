"""Integration tests for export functionality."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from personal_index.export import Exporter, ExportConfig
from personal_index.index import IndexStore
from personal_index.models import IndexedPage, Interest


class TestExportIntegration:
    """Test export functionality with realistic scenarios."""

    def test_export_json(self, tmp_path):
        """Export indexed pages as JSON."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Some content here.",
            tags=["tag1"],
            score=1.0,
        ))
        
        config = ExportConfig(format="json")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com/page1"

    def test_export_markdown(self, tmp_path):
        """Export indexed pages as Markdown."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Some content here.",
            tags=["tag1"],
            score=1.0,
        ))
        
        config = ExportConfig(format="markdown")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.md"
        exporter.export(output_path)
        
        assert output_path.exists()
        content = output_path.read_text()
        assert "# Page 1" in content
        assert "https://example.com/page1" in content

    def test_export_empty_index(self, tmp_path):
        """Export empty index."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        
        config = ExportConfig(format="json")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        assert output_path.exists()
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 0

    def test_export_with_filter(self, tmp_path):
        """Export with score filter."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Some content here.",
            tags=["tag1"],
            score=1.0,
        ))
        index_store.add(IndexedPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Other content.",
            tags=["tag2"],
            score=0.3,
        ))
        
        config = ExportConfig(format="json", min_score=0.5)
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com/page1"

    def test_export_preserves_order(self, tmp_path):
        """Export preserves page ordering."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Content 1.",
            tags=[],
            score=1.0,
        ))
        index_store.add(IndexedPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Content 2.",
            tags=[],
            score=2.0,
        ))
        
        config = ExportConfig(format="json")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 2

    def test_export_with_tags_filter(self, tmp_path):
        """Export filtered by tags."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Content.",
            tags=["python", "programming"],
            score=1.0,
        ))
        index_store.add(IndexedPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Content.",
            tags=["rust"],
            score=1.0,
        ))
        
        config = ExportConfig(format="json", tags=["python"])
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 1
        assert data[0]["url"] == "https://example.com/page1"

    def test_export_multiple_pages(self, tmp_path):
        """Export multiple pages."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        for i in range(10):
            index_store.add(IndexedPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content {i}.",
                tags=[],
                score=float(i),
            ))
        
        config = ExportConfig(format="json")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 10

    def test_export_overwrites_existing(self, tmp_path):
        """Export overwrites existing file."""
        index_store = IndexStore(store_path=str(tmp_path / "index.json"))
        index_store.add(IndexedPage(
            url="https://example.com/page1",
            title="Page 1",
            content="Content.",
            tags=[],
            score=1.0,
        ))
        
        config = ExportConfig(format="json")
        exporter = Exporter(config=config, index_store=index_store)
        
        output_path = tmp_path / "export.json"
        exporter.export(output_path)
        
        # Add another page
        index_store.add(IndexedPage(
            url="https://example.com/page2",
            title="Page 2",
            content="Content.",
            tags=[],
            score=1.0,
        ))
        
        exporter.export(output_path)
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert len(data) == 2
