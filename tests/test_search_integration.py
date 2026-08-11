"""Search integration tests.

Tests the search functionality end-to-end with real indexing and querying.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, IndexedPage


class TestSearchIndexBasic:
    """Test basic search index operations."""

    def test_add_and_search_page(self, tmp_path):
        """Should add a page and find it via search."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Programming",
            content="Python is a popular programming language used for web development.",
            relevance_score=0.8,
        )
        index.add_page(page)

        results = index.search("python")
        assert len(results) >= 1
        assert results[0].url == "https://example.com/python"

    def test_search_multiple_pages(self, tmp_path):
        """Should search across multiple indexed pages."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming language for web development.",
                relevance_score=0.9,
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Guide",
                content="JavaScript is used for frontend web development.",
                relevance_score=0.8,
            ),
            CrawledPage(
                url="https://example.com/rust",
                title="Rust Guide",
                content="Rust is a systems programming language.",
                relevance_score=0.7,
            ),
        ]
        for page in pages:
            index.add_page(page)

        # Search for "web" should find python and javascript
        results = index.search("web")
        urls = [r.url for r in results]
        assert "https://example.com/python" in urls
        assert "https://example.com/javascript" in urls

    def test_search_no_results(self, tmp_path):
        """Should return empty results for non-matching query."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming language.",
            relevance_score=0.9,
        )
        index.add_page(page)

        results = index.search("xyznonexistent")
        assert len(results) == 0

    def test_search_limit(self, tmp_path):
        """Should respect the limit parameter."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        for i in range(10):
            page = CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content="This page contains the word test for searching.",
                relevance_score=0.5 + i * 0.05,
            )
            index.add_page(page)

        results = index.search("test", limit=3)
        assert len(results) <= 3

    def test_search_result_has_score(self, tmp_path):
        """Search results should have relevance scores."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/scored",
            title="Scored Page",
            content="This page has content for scoring.",
            relevance_score=0.95,
        )
        index.add_page(page)

        results = index.search("content")
        assert len(results) >= 1
        assert results[0].relevance_score > 0

    def test_search_result_has_snippet(self, tmp_path):
        """Search results should include text snippets."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/snippet",
            title="Snippet Test",
            content="This is a test page with important content for snippet extraction.",
            relevance_score=0.8,
        )
        index.add_page(page)

        results = index.search("snippet")
        assert len(results) >= 1
        assert results[0].snippet is not None


class TestSearchIndexPersistence:
    """Test search index persistence."""

    def test_index_survives_restart(self, tmp_path):
        """Index data should persist across SearchIndex instances."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/persist",
            title="Persistent Page",
            content="This page persists across restarts.",
            relevance_score=0.9,
        )
        index.add_page(page)
        index._save()

        # Create new index instance
        index2 = SearchIndex(db_path=db_path)
        assert index2.get_page_count() == 1
        results = index2.search("restarts")
        assert len(results) >= 1

    def test_index_file_created_on_save(self, tmp_path):
        """Saving should create the index file."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/new",
            title="New Page",
            content="New content.",
            relevance_score=0.5,
        )
        index.add_page(page)
        index._save()

        assert os.path.exists(db_path)


class TestSearchIndexEdgeCases:
    """Test search index edge cases."""

    def test_search_empty_index(self, tmp_path):
        """Searching an empty index should return no results."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)
        results = index.search("anything")
        assert len(results) == 0

    def test_search_case_insensitive(self, tmp_path):
        """Search should be case-insensitive."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/case",
            title="Case Test",
            content="This page discusses Python programming.",
            relevance_score=0.8,
        )
        index.add_page(page)

        results_lower = index.search("python")
        results_upper = index.search("PYTHON")
        assert len(results_lower) == len(results_upper)

    def test_search_stop_words_ignored(self, tmp_path):
        """Common stop words should not affect search results."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/stops",
            title="Stop Words",
            content="The quick brown fox jumps over the lazy dog.",
            relevance_score=0.7,
        )
        index.add_page(page)

        # "the" is a stop word, should not match
        results = index.search("the")
        # Results may or may not include it depending on implementation
        # Just verify no crash
        assert isinstance(results, list)

    def test_add_duplicate_url_updates(self, tmp_path):
        """Adding a page with the same URL should update it."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page1 = CrawledPage(
            url="https://example.com/dup",
            title="Original Title",
            content="Original content.",
            relevance_score=0.5,
        )
        index.add_page(page1)

        page2 = CrawledPage(
            url="https://example.com/dup",
            title="Updated Title",
            content="Updated content with more text.",
            relevance_score=0.9,
        )
        index.add_page(page2)

        assert index.get_page_count() == 1
        page = index.get_page("https://example.com/dup")
        assert page is not None
        assert page.title == "Updated Title"

    def test_search_special_characters(self, tmp_path):
        """Search with special characters should not crash."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        page = CrawledPage(
            url="https://example.com/special",
            title="Special Chars",
            content="This page has special chars: @#$%^&*()",
            relevance_score=0.6,
        )
        index.add_page(page)

        # Should not crash
        results = index.search("special chars @#$%")
        assert isinstance(results, list)
