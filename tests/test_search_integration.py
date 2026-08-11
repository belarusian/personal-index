"""Integration tests for search functionality across the full pipeline."""

from __future__ import annotations

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, SearchResult


class TestSearchIntegration:
    """Test search integration with the index."""

    def test_search_single_term(self, tmp_path):
        """Test searching for a single term."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Python is a great programming language for web development.",
        ))
        results = index.search("python")
        assert len(results) == 1
        assert isinstance(results[0], SearchResult)

    def test_search_multiple_terms(self, tmp_path):
        """Test searching for multiple terms."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page1",
            title="Python and JavaScript",
            content="Python and JavaScript are both popular programming languages.",
        ))
        results = index.search("python javascript")
        assert len(results) == 1

    def test_search_ranking_by_relevance(self, tmp_path):
        """Test that search results are ranked by relevance."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        # Page with more matches should rank higher
        index.add_page(CrawledPage(
            url="https://example.com/less-relevant",
            title="Brief Python Mention",
            content="Python is mentioned once in this article about other topics.",
        ))
        index.add_page(CrawledPage(
            url="https://example.com/more-relevant",
            title="Python Deep Dive",
            content="Python Python Python. This article is all about Python programming with Python.",
        ))
        results = index.search("python")
        assert len(results) == 2
        # More relevant page should be first
        assert "more-relevant" in results[0].url

    def test_search_with_snippets(self, tmp_path):
        """Test that search results include snippets."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/snippet",
            title="Snippet Test",
            content=(
                "This is a long article about Python programming. "
                "Python is used for web development, data science, "
                "and machine learning applications."
            ),
        ))
        results = index.search("python")
        assert len(results) == 1
        assert len(results[0].snippet) > 0

    def test_search_empty_query(self, tmp_path):
        """Test searching with empty query returns no results."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Page",
            content="Some content here.",
        ))
        results = index.search("")
        assert len(results) == 0

    def test_search_no_results(self, tmp_path):
        """Test searching for non-existent term."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Page",
            content="Some content about Python.",
        ))
        results = index.search("rust")
        assert len(results) == 0

    def test_search_limit(self, tmp_path):
        """Test search limit parameter."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        for i in range(20):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"This is page {i} about Python programming.",
            ))
        results = index.search("python", limit=5)
        assert len(results) == 5

    def test_search_case_insensitive(self, tmp_path):
        """Test that search is case insensitive."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python is a programming language.",
        ))
        for query in ["python", "Python", "PYTHON", "PyThOn"]:
            results = index.search(query)
            assert len(results) == 1

    def test_search_with_stop_words(self, tmp_path):
        """Test that stop words are handled correctly."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python is a great programming language.",
        ))
        # "is" and "a" are stop words, should still find via "python"
        results = index.search("python is a great")
        assert len(results) == 1

    def test_search_after_remove(self, tmp_path):
        """Test search after removing a page."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        index.add_page(CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Python is a programming language.",
        ))
        assert len(index.search("python")) == 1
        index.remove_page("https://example.com/page")
        assert len(index.search("python")) == 0

    def test_search_persistence(self, tmp_path):
        """Test that search works after index reload."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)
        index.add_page(CrawledPage(
            url="https://example.com/persist",
            title="Persistent Page",
            content="This page should persist across index reloads.",
        ))
        index.close()

        # Reload
        index2 = SearchIndex(db_path=db_path)
        results = index2.search("persist")
        assert len(results) == 1
        assert "Persistent Page" in results[0].title

    def test_search_multiple_pages_same_term(self, tmp_path):
        """Test searching across multiple pages with same term."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        for i in range(5):
            index.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Python Page {i}",
                content=f"This is Python page number {i} about programming.",
            ))
        results = index.search("python")
        assert len(results) == 5

    def test_search_title_boost(self, tmp_path):
        """Test that terms in title are weighted higher."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        # Term only in content
        index.add_page(CrawledPage(
            url="https://example.com/content-only",
            title="General Article",
            content="Python is discussed in this article about programming.",
        ))
        # Term in title
        index.add_page(CrawledPage(
            url="https://example.com/title-match",
            title="Python Programming Guide",
            content="This article covers various programming topics.",
        ))
        results = index.search("python")
        assert len(results) == 2
        # Title match should rank higher
        assert "title-match" in results[0].url
