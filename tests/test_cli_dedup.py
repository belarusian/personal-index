"""Tests for dedup CLI command."""

from __future__ import annotations

import os

from click.testing import CliRunner

from personal_index.cli import main
from personal_index.index import SearchIndex
from personal_index.models import IndexedPage


class TestDedupCLI:
    def test_dedup_command_exists(self):
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert "dedup" in result.output

    def test_dedup_no_content(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", str(tmp_path), "dedup"],
        )
        assert "No indexed content found" in result.output or result.exit_code == 0

    def test_dedup_with_duplicates(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        # Add duplicate content
        idx.add_page(IndexedPage(
            url="https://a.com",
            title="Page A",
            content="This is the exact same content",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://b.com",
            title="Page B",
            content="This is the exact same content",
            score=7.0,
        ))
        idx.add_page(IndexedPage(
            url="https://c.com",
            title="Page C",
            content="Different content here",
            score=6.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "dedup", "--dry-run"],
        )
        assert result.exit_code == 0
        assert "Duplicates found: 1" in result.output

    def test_dedup_method_option(self, tmp_path):
        dd = str(tmp_path)
        os.makedirs(dd, exist_ok=True)

        idx_path = os.path.join(dd, "search_index.json")
        idx = SearchIndex(db_path=idx_path)

        idx.add_page(IndexedPage(
            url="https://example.com/",
            title="Page A",
            content="Content A",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://example.com",
            title="Page B",
            content="Content B",
            score=7.0,
        ))
        idx._save()

        runner = CliRunner()
        result = runner.invoke(
            main,
            ["--data-dir", dd, "dedup", "--method", "url"],
        )
        assert result.exit_code == 0


class TestDedupHelpers:
    """Test the extracted helper functions from cli_dedup refactor."""

    def test_load_indexed_content_returns_pages_and_index(self, tmp_path):
        from personal_index.cli_dedup import _load_indexed_content

        dd = str(tmp_path)
        idx_path = f"{dd}/search_index.json"
        idx = SearchIndex(db_path=idx_path)
        idx.add_page(IndexedPage(
            url="https://example.com",
            title="Test",
            content="Some content",
            score=5.0,
        ))
        idx._save()

        pages, _ = _load_indexed_content(dd)
        assert len(pages) == 1
        assert pages[0].url == "https://example.com"

    def test_load_indexed_content_empty(self, tmp_path):
        from personal_index.cli_dedup import _load_indexed_content

        dd = str(tmp_path)
        pages, _ = _load_indexed_content(dd)
        assert pages == []

    def test_build_dedup_items(self, tmp_path):
        from personal_index.cli_dedup import _build_dedup_items

        dd = str(tmp_path)
        idx_path = f"{dd}/search_index.json"
        idx = SearchIndex(db_path=idx_path)
        idx.add_page(IndexedPage(
            url="https://a.com",
            title="Page A",
            content="Content A",
            score=8.0,
        ))
        idx.add_page(IndexedPage(
            url="https://b.com",
            title="Page B",
            content=None,
            score=7.0,
        ))
        idx._save()

        pages, _ = idx.list_pages(), idx
        pages = idx.list_pages()
        items = _build_dedup_items(pages)
        assert len(items) == 2
        assert items[0]["url"] == "https://a.com"
        assert items[0]["content"] == "Content A"
        assert items[1]["content"] == ""

    def test_dispatch_dedup_hash(self):
        from personal_index.cli_dedup import _dispatch_dedup

        items = [
            {"url": "https://a.com", "title": "A", "content": "same content"},
            {"url": "https://b.com", "title": "B", "content": "same content"},
        ]
        result = _dispatch_dedup(items, "hash", 0.9)
        assert result is not None

    def test_dispatch_dedup_url(self):
        from personal_index.cli_dedup import _dispatch_dedup

        items = [
            {"url": "https://example.com/", "title": "A", "content": "A"},
            {"url": "https://example.com", "title": "B", "content": "B"},
        ]
        result = _dispatch_dedup(items, "url", 0.9)
        assert result is not None

    def test_dispatch_dedup_similarity(self):
        from personal_index.cli_dedup import _dispatch_dedup

        items = [
            {"url": "https://a.com", "title": "A", "content": "hello world"},
            {"url": "https://b.com", "title": "B", "content": "hello world"},
        ]
        result = _dispatch_dedup(items, "similarity", 0.9)
        assert result is not None

    def test_dispatch_dedup_all(self):
        from personal_index.cli_dedup import _dispatch_dedup

        items = [
            {"url": "https://a.com", "title": "A", "content": "content"},
        ]
        result = _dispatch_dedup(items, "all", 0.9)
        assert result is not None
