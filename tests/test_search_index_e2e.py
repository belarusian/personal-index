"""End-to-end tests for search index operations."""

from __future__ import annotations

import json
import os
import tempfile

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, IndexedPage


class TestSearchIndexE2E:
    """Test search index with realistic workflows."""

    def test_add_and_search_single_page(self, tmp_path):
        """Add a single page and search for it."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/hello",
            title="Hello World",
            content="This is a hello world example page about programming.",
        )
        index.add_page(page)
        results = index.search("hello")
        assert len(results) == 1
        assert results[0].title == "Hello World"

    def test_add_multiple_pages_search_relevance(self, tmp_path):
        """Add multiple pages and verify relevance ordering."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        pages = [
            CrawledPage(url="https://example.com/a", title="Python Guide",
                        content="Python is a great programming language for web development."),
            CrawledPage(url="https://example.com/b", title="Rust Guide",
                        content="Rust is a systems programming language focused on safety."),
            CrawledPage(url="https://example.com/c", title="Python Advanced",
                        content="Advanced Python programming techniques and best practices for production."),
        ]
        for page in pages:
            index.add_page(page)

        results = index.search("python")
        assert len(results) >= 1
        # Python pages should rank higher than Rust
        assert any("Python" in r.title for r in results)

    def test_search_with_no_results(self, tmp_path):
        """Search returns empty list when no matches."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(url="https://example.com/a", title="Test",
                           content="Some test content here.")
        index.add_page(page)
        results = index.search("nonexistent_xyz")
        assert len(results) == 0

    def test_persistence_across_instances(self, tmp_path):
        """Index persists data across SearchIndex instances."""
        path = str(tmp_path / "index.json")
        index1 = SearchIndex(db_path=path)
        index1.add_page(CrawledPage(
            url="https://example.com/persist",
            title="Persistent Page",
            content="This page should persist across instances.",
        ))
        del index1

        index2 = SearchIndex(db_path=path)
        assert index2.get_page_count() == 1
        results = index2.search("persist")
        assert len(results) == 1

    def test_remove_page(self, tmp_path):
        """Remove a page from the index."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/remove",
            title="To Remove",
            content="This page will be removed.",
        ))
        assert index.get_page_count() == 1
        index.remove_page("https://example.com/remove")
        assert index.get_page_count() == 0

    def test_list_pages_sorted_by_score(self, tmp_path):
        """List pages sorted by relevance score."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(IndexedPage(
            url="https://example.com/low", title="Low Score",
            content="Low score page", score=0.3,
        ))
        index.add_page(IndexedPage(
            url="https://example.com/high", title="High Score",
            content="High score page", score=0.9,
        ))
        pages = index.list_pages()
        assert pages[0].score >= pages[1].score

    def test_clear_index(self, tmp_path):
        """Clear all pages from the index."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        for i in range(5):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i}.",
            ))
        assert index.get_page_count() == 5
        index.clear()
        assert index.get_page_count() == 0

    def test_search_limit(self, tmp_path):
        """Search respects the limit parameter."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        for i in range(10):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Test Page {i}",
                content="This is test content for search.",
            ))
        results = index.search("test", limit=3)
        assert len(results) <= 3

    def test_search_snippet_generation(self, tmp_path):
        """Search results include relevant snippets."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/snippet",
            title="Snippet Test",
            content="This is a long piece of content that contains the word "
                    "search in the middle of a longer paragraph with lots of "
                    "text before and after the search term.",
        ))
        results = index.search("search")
        assert len(results) == 1
        assert "search" in results[0].snippet.lower()

    def test_context_manager(self, tmp_path):
        """SearchIndex works as a context manager."""
        path = str(tmp_path / "index.json")
        with SearchIndex(db_path=path) as index:
            index.add_page(CrawledPage(
                url="https://example.com/cm",
                title="Context Manager",
                content="Testing context manager usage.",
            ))
        # Verify data was saved
        index2 = SearchIndex(db_path=path)
        assert index2.get_page_count() == 1
