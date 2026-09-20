"""Adversarial deep tests for the index subsystem (SearchIndex).

Tests edge cases, error conditions, boundary values, and contract
compliance for SearchIndex operations.
"""

import json
import os
import tempfile
from datetime import datetime

import pytest

from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, IndexedPage


@pytest.fixture
def temp_index():
    """Create a temporary SearchIndex with a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "index.json")
        index = SearchIndex(db_path=db_path)
        yield index
        index.close()


@pytest.fixture
def sample_page():
    """Create a sample IndexedPage."""
    return IndexedPage(
        url="https://example.com/page1",
        title="Example Page",
        content="This is example content for testing.",
        score=1.0,
        crawled_at=datetime.now().isoformat(),
        domain="example.com",
        status_code=200,
        content_length=35,
        language="en",
        keywords=["example", "test"],
        matched_interests=[],
    )


@pytest.fixture
def sample_crawled_page():
    """Create a sample CrawledPage."""
    return CrawledPage(
        url="https://example.com/crawled",
        title="Crawled Page",
        content="Content from crawling.",
        status_code=200,
        relevance_score=0.8,
        language="en",
        keywords=["crawl"],
        matched_interests=[],
    )


class TestSearchIndexEmptyState:
    """Tests for empty index state."""

    def test_search_empty_index(self, temp_index):
        """Search on empty index returns empty list."""
        results = temp_index.search("anything")
        assert results == []

    def test_search_empty_query(self, temp_index, sample_page):
        """Search with empty query returns empty list."""
        temp_index.add_page(sample_page)
        results = temp_index.search("")
        assert results == []

    def test_search_whitespace_query(self, temp_index, sample_page):
        """Search with whitespace-only query returns empty list."""
        temp_index.add_page(sample_page)
        results = temp_index.search("   ")
        assert results == []

    def test_search_stopwords_only(self, temp_index, sample_page):
        """Search with only stop words returns empty list."""
        temp_index.add_page(sample_page)
        results = temp_index.search("the is a")
        assert results == []

    def test_get_page_count_empty(self, temp_index):
        """Page count on empty index is 0."""
        assert temp_index.get_page_count() == 0

    def test_list_pages_empty(self, temp_index):
        """List pages on empty index returns empty list."""
        assert temp_index.list_pages() == []

    def test_remove_page_empty(self, temp_index):
        """Remove page from empty index returns False."""
        assert temp_index.remove_page("https://example.com") is False

    def test_get_page_empty(self, temp_index):
        """Get page from empty index returns None."""
        assert temp_index.get_page("https://example.com") is None


class TestSearchIndexAddPage:
    """Tests for add_page operations."""

    def test_add_indexed_page(self, temp_index, sample_page):
        """Add an IndexedPage and verify it's stored."""
        count = temp_index.add_page(sample_page)
        assert count == 1
        assert temp_index.get_page_count() == 1

    def test_add_crawled_page(self, temp_index, sample_crawled_page):
        """Add a CrawledPage and verify conversion to IndexedPage."""
        count = temp_index.add_page(sample_crawled_page)
        assert count == 1
        page = temp_index.get_page(sample_crawled_page.url)
        assert page is not None
        assert page.title == "Crawled Page"
        assert page.domain == "example.com"

    def test_add_duplicate_page(self, temp_index, sample_page):
        """Add same page twice - should not duplicate."""
        temp_index.add_page(sample_page)
        count = temp_index.add_page(sample_page)
        assert count == 1
        assert temp_index.get_page_count() == 1

    def test_add_page_empty_content(self, temp_index):
        """Add page with empty content."""
        page = IndexedPage(
            url="https://example.com/empty",
            title="Empty Content",
            content="",
            score=0.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=0,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        count = temp_index.add_page(page)
        assert count == 1

    def test_add_page_unicode_content(self, temp_index):
        """Add page with unicode content."""
        page = IndexedPage(
            url="https://example.com/unicode",
            title="Ünïcödé",
            content="Héllo Wörld 你好世界",
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=20,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        count = temp_index.add_page(page)
        assert count == 1

    def test_add_page_very_long_content(self, temp_index):
        """Add page with very long content."""
        long_content = "word " * 10000
        page = IndexedPage(
            url="https://example.com/long",
            title="Long Page",
            content=long_content,
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=len(long_content),
            language="en",
            keywords=[],
            matched_interests=[],
        )
        count = temp_index.add_page(page)
        assert count == 1


class TestSearchIndexSearch:
    """Tests for search operations."""

    def test_search_basic(self, temp_index, sample_page):
        """Basic search finds matching page."""
        temp_index.add_page(sample_page)
        results = temp_index.search("example")
        assert len(results) == 1
        assert results[0].url == sample_page.url

    def test_search_no_match(self, temp_index, sample_page):
        """Search for non-existent term returns empty."""
        temp_index.add_page(sample_page)
        results = temp_index.search("nonexistentterm")
        assert results == []

    def test_search_limit_zero(self, temp_index, sample_page):
        """Search with limit=0 returns empty list."""
        temp_index.add_page(sample_page)
        results = temp_index.search("example", limit=0)
        assert results == []

    def test_search_limit_negative(self, temp_index, sample_page):
        """Search with negative limit returns empty list."""
        temp_index.add_page(sample_page)
        results = temp_index.search("example", limit=-5)
        assert results == []

    def test_search_limit_one(self, temp_index, sample_page):
        """Search with limit=1 returns at most one result."""
        temp_index.add_page(sample_page)
        results = temp_index.search("example", limit=1)
        assert len(results) <= 1

    def test_search_multiple_pages(self, temp_index):
        """Search across multiple pages."""
        page1 = IndexedPage(
            url="https://example.com/1",
            title="First Page",
            content="This is the first page content.",
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=30,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        page2 = IndexedPage(
            url="https://example.com/2",
            title="Second Page",
            content="This is the second page content.",
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=31,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        temp_index.add_page(page1)
        temp_index.add_page(page2)
        results = temp_index.search("page")
        assert len(results) == 2

    def test_search_relevance_ordering(self, temp_index):
        """Search results are ordered by relevance."""
        # Page with term in title should rank higher
        page1 = IndexedPage(
            url="https://example.com/title",
            title="Important Keyword",
            content="Some content here.",
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=18,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        page2 = IndexedPage(
            url="https://example.com/content",
            title="Different Title",
            content="The keyword appears in content.",
            score=1.0,
            crawled_at=datetime.now().isoformat(),
            domain="example.com",
            status_code=200,
            content_length=33,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        temp_index.add_page(page1)
        temp_index.add_page(page2)
        results = temp_index.search("keyword")
        assert len(results) == 2
        # Title match should rank higher
        assert results[0].url == page1.url


class TestSearchIndexPersistence:
    """Tests for index persistence."""

    def test_save_and_reload(self, temp_index, sample_page):
        """Index persists and reloads correctly."""
        temp_index.add_page(sample_page)
        db_path = temp_index.db_path

        # Create new index from same file
        index2 = SearchIndex(db_path=db_path)
        assert index2.get_page_count() == 1
        page = index2.get_page(sample_page.url)
        assert page is not None
        assert page.title == sample_page.title
        index2.close()

    def test_reload_corrupted_file(self):
        """Index handles corrupted JSON file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "index.json")
            with open(db_path, "w") as f:
                f.write("not valid json")
            index = SearchIndex(db_path=db_path)
            assert index.get_page_count() == 0
            index.close()

    def test_reload_empty_file(self):
        """Index handles empty file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "index.json")
            with open(db_path, "w") as f:
                f.write("")
            index = SearchIndex(db_path=db_path)
            assert index.get_page_count() == 0
            index.close()

    def test_reload_non_dict_json(self):
        """Index handles non-dict JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "index.json")
            with open(db_path, "w") as f:
                json.dump([1, 2, 3], f)
            index = SearchIndex(db_path=db_path)
            assert index.get_page_count() == 0
            index.close()


class TestSearchIndexRemovePage:
    """Tests for remove_page operations."""

    def test_remove_existing_page(self, temp_index, sample_page):
        """Remove an existing page."""
        temp_index.add_page(sample_page)
        removed = temp_index.remove_page(sample_page.url)
        assert removed is True
        assert temp_index.get_page_count() == 0

    def test_remove_nonexistent_page(self, temp_index):
        """Remove a page that doesn't exist."""
        removed = temp_index.remove_page("https://example.com/missing")
        assert removed is False

    def test_remove_updates_word_index(self, temp_index, sample_page):
        """Removing a page updates the word index."""
        temp_index.add_page(sample_page)
        temp_index.remove_page(sample_page.url)
        # Search should not find the removed page
        results = temp_index.search("example")
        assert len(results) == 0


class TestSearchIndexClear:
    """Tests for clear operation."""

    def test_clear_index(self, temp_index, sample_page):
        """Clear all pages from index."""
        temp_index.add_page(sample_page)
        temp_index.clear()
        assert temp_index.get_page_count() == 0
        assert temp_index.search("example") == []


class TestSearchIndexContextManager:
    """Tests for context manager protocol."""

    def test_context_manager(self):
        """SearchIndex works as context manager."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "index.json")
            with SearchIndex(db_path=db_path) as index:
                page = IndexedPage(
                    url="https://example.com/cm",
                    title="Context Manager",
                    content="Testing context manager.",
                    score=1.0,
                    crawled_at=datetime.now().isoformat(),
                    domain="example.com",
                    status_code=200,
                    content_length=23,
                    language="en",
                    keywords=[],
                    matched_interests=[],
                )
                index.add_page(page)
                assert index.get_page_count() == 1


class TestSearchIndexEdgeCases:
    """Edge case tests."""

    def test_tokenize_empty_string(self):
        """Tokenize empty string returns empty list."""
        assert SearchIndex._tokenize("") == []

    def test_tokenize_none(self):
        """Tokenize None returns empty list."""
        assert SearchIndex._tokenize(None) == []

    def test_tokenize_single_char_words(self):
        """Single character words are filtered."""
        tokens = SearchIndex._tokenize("a b c d e")
        assert tokens == []

    def test_tokenize_numbers(self):
        """Numbers are included in tokens."""
        tokens = SearchIndex._tokenize("test 123 abc")
        assert "123" in tokens
        assert "test" in tokens
        assert "abc" in tokens

    def test_tokenize_special_chars(self):
        """Special characters are removed."""
        tokens = SearchIndex._tokenize("hello, world! test.")
        assert tokens == ["hello", "world", "test"]

    def test_search_case_insensitive(self, temp_index, sample_page):
        """Search is case-insensitive."""
        temp_index.add_page(sample_page)
        results = temp_index.search("EXAMPLE")
        assert len(results) == 1

    def test_add_page_none_url(self, temp_index):
        """Add page with None url."""
        page = IndexedPage(
            url=None,
            title="No URL",
            content="Content",
            score=0.0,
            crawled_at=datetime.now().isoformat(),
            domain="",
            status_code=200,
            content_length=7,
            language="en",
            keywords=[],
            matched_interests=[],
        )
        # Should not crash
        temp_index.add_page(page)

    def test_search_after_remove_all(self, temp_index, sample_page):
        """Search after removing all pages."""
        temp_index.add_page(sample_page)
        temp_index.remove_page(sample_page.url)
        results = temp_index.search("example")
        assert results == []

    def test_multiple_searches_idempotent(self, temp_index, sample_page):
        """Multiple searches return consistent results."""
        temp_index.add_page(sample_page)
        results1 = temp_index.search("example")
        results2 = temp_index.search("example")
        assert len(results1) == len(results2)
        assert results1[0].url == results2[0].url
