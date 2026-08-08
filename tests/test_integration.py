"""Integration tests for personal-index.

Tests the full workflow: adding interests, crawling, filtering, indexing, and searching.
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from personal_index.models import CrawledPage, Interest, CrawlConfig
from personal_index.storage import InterestStore, PageStore
from personal_index.filter import ContentFilter
from personal_index.search import SearchIndex
from personal_index.crawler import PageParser, LinkExtractor


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


class TestFullWorkflow:
    """Test the complete workflow of personal-index."""

    def test_add_interest_and_search(self, temp_data_dir):
        """Test adding an interest, indexing a page, and searching."""
        # Setup
        interest_store = InterestStore(data_dir=temp_data_dir)
        search_index = SearchIndex(index_dir=f"{temp_data_dir}/index")

        # Add interest
        interest = Interest(
            topic="python",
            keywords=["python", "programming"],
        )
        interest_store.add_interest(interest)

        # Verify interest stored
        stored = interest_store.get_interest("python")
        assert stored is not None
        assert stored.keywords == ["python", "programming"]

        # Create and index a page
        page = CrawledPage(
            url="https://example.com/python-guide",
            title="Python Programming Guide",
            content="Learn python programming and build great applications.",
            matched_interests=["python"],
        )
        search_index.add_document(page)

        # Search
        results = search_index.search("python programming")
        assert len(results) > 0
        assert "Python" in results[0].page.title

    def test_content_filtering_pipeline(self, temp_data_dir):
        """Test that content filtering correctly filters pages."""
        interest_store = InterestStore(data_dir=temp_data_dir)
        interest_store.add_interest(Interest(
            topic="python",
            keywords=["python", "programming"],
        ))

        interests = interest_store.list_interests()
        content_filter = ContentFilter(interests)

        # Matching page
        matching_page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming tutorial",
        )
        result = content_filter.filter_page(matching_page)
        assert result.passed is True

        # Non-matching page
        non_matching = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Guide",
            content="How to cook pasta",
        )
        result = content_filter.filter_page(non_matching)
        assert result.passed is False

    def test_page_parsing_and_indexing(self, temp_data_dir):
        """Test parsing HTML and indexing the result."""
        html = """
        <html>
        <head>
            <title>Test Page</title>
            <meta name="description" content="A test page for indexing">
        </head>
        <body>
            <h1>Welcome</h1>
            <p>This is test content about python programming.</p>
        </body>
        </html>
        """
        page = PageParser.parse(html, "https://example.com/test")
        assert page.title == "Test Page"
        assert "test content" in page.content
        assert page.word_count > 0

        # Index the page
        search_index = SearchIndex(index_dir=f"{temp_data_dir}/index")
        search_index.add_document(page)

        # Search for it
        results = search_index.search("python programming")
        assert len(results) > 0

    def test_link_extraction_and_dedup(self, temp_data_dir):
        """Test that link extraction works and deduplicates."""
        html = """
        <html><body>
        <a href="https://example.com/page1">Link 1</a>
        <a href="https://example.com/page1">Link 1 dup</a>
        <a href="https://example.com/page2">Link 2</a>
        <a href="javascript:void(0)">JS Link</a>
        <a href="mailto:test@example.com">Email</a>
        </body></html>
        """
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert len(links) == 2  # Deduplicated, no JS/mailto

    def test_multiple_interests_and_search(self, temp_data_dir):
        """Test with multiple interests and cross-interest search."""
        interest_store = InterestStore(data_dir=temp_data_dir)
        search_index = SearchIndex(index_dir=f"{temp_data_dir}/index")

        # Add multiple interests
        interest_store.add_interest(Interest(
            topic="python",
            keywords=["python", "programming"],
        ))
        interest_store.add_interest(Interest(
            topic="ai",
            keywords=["artificial intelligence", "machine learning"],
        ))

        # Index pages for both interests
        search_index.add_document(CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming language",
            matched_interests=["python"],
        ))
        search_index.add_document(CrawledPage(
            url="https://example.com/ai",
            title="AI Overview",
            content="Artificial intelligence and machine learning",
            matched_interests=["ai"],
        ))

        # Search across all
        results = search_index.search("programming")
        assert len(results) >= 1

        # Search with interest filter
        results = search_index.search("intelligence", interest_filter="ai")
        assert len(results) >= 1
        for r in results:
            assert "ai" in r.page.matched_interests

    def test_page_store_and_retrieval(self, temp_data_dir):
        """Test saving and retrieving pages from storage."""
        page_store = PageStore(data_dir=temp_data_dir)

        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="Test content here",
            matched_interests=["python"],
            word_count=3,
        )
        page_store.save_page(page)

        retrieved = page_store.get_page(page.id)
        assert retrieved is not None
        assert retrieved.url == page.url
        assert retrieved.title == page.title
        assert retrieved.matched_interests == ["python"]

    def test_search_with_highlights(self, temp_data_dir):
        """Test search with highlighted fragments."""
        search_index = SearchIndex(index_dir=f"{temp_data_dir}/index")

        search_index.add_document(CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Python is a great programming language for beginners and experts alike.",
            matched_interests=["python"],
        ))

        results = search_index.search_with_highlights("python programming")
        assert len(results) > 0
        assert results[0].score > 0
