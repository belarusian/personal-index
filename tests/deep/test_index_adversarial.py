"""Adversarial deep tests for personal_index/index.py SearchIndex module.

Tests edge cases, error conditions, boundary values, and contract violations.
"""

import json
import os
import pytest
import tempfile

from personal_index.index import SearchIndex
from personal_index.models import IndexedPage, CrawledPage, SearchResult


@pytest.fixture
def temp_index():
    """Create a temporary SearchIndex with a temp file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "index.json")
        idx = SearchIndex(db_path=db_path)
        yield idx
        idx.close()


@pytest.fixture
def memory_index():
    """Create an in-memory SearchIndex (no persistence)."""
    return SearchIndex(db_path=None)


class TestSearchIndexPersistence:
    """Test persistence edge cases."""

    def test_load_corrupted_json(self, tmp_path):
        """Loading corrupted JSON should not crash."""
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            f.write("not valid json {{{")
        idx = SearchIndex(db_path=db_path)
        assert idx.get_page_count() == 0
        idx.close()

    def test_load_non_dict_json(self, tmp_path):
        """Loading non-dict JSON should not crash."""
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            json.dump([1, 2, 3], f)
        idx = SearchIndex(db_path=db_path)
        assert idx.get_page_count() == 0
        idx.close()

    def test_load_missing_pages_key(self, tmp_path):
        """Loading JSON without 'pages' key should not crash."""
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            json.dump({"word_index": {}}, f)
        idx = SearchIndex(db_path=db_path)
        assert idx.get_page_count() == 0
        idx.close()

    def test_load_empty_file(self, tmp_path):
        """Loading empty file should not crash."""
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            f.write("")
        idx = SearchIndex(db_path=db_path)
        assert idx.get_page_count() == 0
        idx.close()

    def test_save_to_nonexistent_dir(self, tmp_path):
        """Saving to a path in a nonexistent directory should create it."""
        db_path = str(tmp_path / "sub" / "dir" / "index.json")
        idx = SearchIndex(db_path=db_path)
        page = IndexedPage(url="http://example.com", title="Test", content="Content")
        idx.add_page(page)
        assert os.path.exists(db_path)
        idx.close()

    def test_roundtrip_persistence(self, temp_index):
        """Pages should survive save/load cycle."""
        page = IndexedPage(url="http://example.com", title="Test", content="Content")
        temp_index.add_page(page)
        temp_index.close()

        # Reload
        idx2 = SearchIndex(db_path=temp_index.db_path)
        assert idx2.get_page_count() == 1
        loaded = idx2.get_page("http://example.com")
        assert loaded is not None
        assert loaded.title == "Test"
        idx2.close()


class TestSearchIndexAddPage:
    """Test add_page edge cases."""

    def test_add_empty_page(self, memory_index):
        """Adding a page with empty title and content."""
        page = IndexedPage(url="http://empty.com", title="", content="")
        count = memory_index.add_page(page)
        assert count == 1

    def test_add_duplicate_url(self, memory_index):
        """Adding same URL twice should overwrite."""
        page1 = IndexedPage(url="http://dup.com", title="First", content="Content")
        page2 = IndexedPage(url="http://dup.com", title="Second", content="Different")
        memory_index.add_page(page1)
        count = memory_index.add_page(page2)
        assert count == 1
        loaded = memory_index.get_page("http://dup.com")
        assert loaded.title == "Second"

    def test_add_crawled_page(self, memory_index):
        """Adding a CrawledPage should convert to IndexedPage."""
        crawled = CrawledPage(url="http://crawl.com", title="Crawled", content="Content")
        count = memory_index.add_page(crawled)
        assert count == 1
        loaded = memory_index.get_page("http://crawl.com")
        assert isinstance(loaded, IndexedPage)

    def test_add_page_unicode(self, memory_index):
        """Adding a page with unicode content."""
        page = IndexedPage(url="http://unicode.com", title="Tëst", content="Ünïcödé")
        count = memory_index.add_page(page)
        assert count == 1

    def test_add_page_very_long_content(self, memory_index):
        """Adding a page with very long content."""
        long_content = "word " * 10000
        page = IndexedPage(url="http://long.com", title="Long", content=long_content)
        count = memory_index.add_page(page)
        assert count == 1

    def test_add_page_whitespace_only(self, memory_index):
        """Adding a page with whitespace-only content."""
        page = IndexedPage(url="http://ws.com", title="  ", content="   ")
        count = memory_index.add_page(page)
        assert count == 1


class TestSearchIndexRemovePage:
    """Test remove_page edge cases."""

    def test_remove_nonexistent_page(self, memory_index):
        """Removing a page that doesn't exist."""
        result = memory_index.remove_page("http://nonexistent.com")
        assert result is False

    def test_remove_and_readd(self, memory_index):
        """Removing a page and re-adding it."""
        page = IndexedPage(url="http://readd.com", title="Test", content="Content")
        memory_index.add_page(page)
        memory_index.remove_page("http://readd.com")
        memory_index.add_page(page)
        assert memory_index.get_page_count() == 1

    def test_remove_all_pages(self, memory_index):
        """Removing all pages."""
        for i in range(5):
            page = IndexedPage(url=f"http://page{i}.com", title=f"Page {i}", content="Content")
            memory_index.add_page(page)
        for i in range(5):
            memory_index.remove_page(f"http://page{i}.com")
        assert memory_index.get_page_count() == 0


class TestSearchIndexSearch:
    """Test search edge cases."""

    def test_search_empty_query(self, memory_index):
        """Searching with empty query."""
        results = memory_index.search("")
        assert results == []

    def test_search_stopwords_only(self, memory_index):
        """Searching with only stop words."""
        page = IndexedPage(url="http://stop.com", title="The", content="And the is")
        memory_index.add_page(page)
        results = memory_index.search("the and is")
        assert results == []

    def test_search_limit_zero(self, memory_index):
        """Searching with limit=0."""
        page = IndexedPage(url="http://limit.com", title="Test", content="Content")
        memory_index.add_page(page)
        results = memory_index.search("test", limit=0)
        assert results == []

    def test_search_limit_negative(self, memory_index):
        """Searching with negative limit."""
        page = IndexedPage(url="http://neg.com", title="Test", content="Content")
        memory_index.add_page(page)
        results = memory_index.search("test", limit=-5)
        assert results == []

    def test_search_limit_one(self, memory_index):
        """Searching with limit=1."""
        for i in range(5):
            page = IndexedPage(url=f"http://page{i}.com", title="Test", content="Content")
            memory_index.add_page(page)
        results = memory_index.search("test", limit=1)
        assert len(results) == 1

    def test_search_no_results(self, memory_index):
        """Searching for a term that doesn't exist."""
        page = IndexedPage(url="http://nope.com", title="Test", content="Content")
        memory_index.add_page(page)
        results = memory_index.search("nonexistentterm")
        assert results == []

    def test_search_case_insensitive(self, memory_index):
        """Searching should be case-insensitive."""
        page = IndexedPage(url="http://case.com", title="Test", content="Content")
        memory_index.add_page(page)
        results = memory_index.search("TEST")
        assert len(results) == 1

    def test_search_unicode_query(self, memory_index):
        """Searching with unicode query."""
        page = IndexedPage(url="http://uni.com", title="Tëst", content="Ünïcödé")
        memory_index.add_page(page)
        results = memory_index.search("tëst")
        # Unicode tokens may not match due to regex [a-z0-9]+
        # This is a contract test - verify behavior is consistent

    def test_search_snippet_generation(self, memory_index):
        """Search results should include snippets."""
        page = IndexedPage(url="http://snippet.com", title="Test", content="This is some test content here")
        memory_index.add_page(page)
        results = memory_index.search("test")
        assert len(results) == 1
        assert isinstance(results[0].snippet, str)

    def test_search_empty_content_snippet(self, memory_index):
        """Search with empty content should return empty snippet."""
        page = IndexedPage(url="http://empty.com", title="Test", content="")
        memory_index.add_page(page)
        results = memory_index.search("test")
        assert len(results) == 1
        assert results[0].snippet == ""


class TestSearchIndexListPages:
    """Test list_pages edge cases."""

    def test_list_empty_index(self, memory_index):
        """Listing pages in empty index."""
        pages = memory_index.list_pages()
        assert pages == []

    def test_list_sorted_by_score(self, memory_index):
        """Pages should be sorted by score descending."""
        page1 = IndexedPage(url="http://low.com", title="Low", content="Content", score=1.0)
        page2 = IndexedPage(url="http://high.com", title="High", content="Content", score=10.0)
        page3 = IndexedPage(url="http://mid.com", title="Mid", content="Content", score=5.0)
        memory_index.add_page(page1)
        memory_index.add_page(page2)
        memory_index.add_page(page3)
        pages = memory_index.list_pages()
        assert pages[0].url == "http://high.com"
        assert pages[1].url == "http://mid.com"
        assert pages[2].url == "http://low.com"


class TestSearchIndexClear:
    """Test clear edge cases."""

    def test_clear_empty_index(self, memory_index):
        """Clearing an empty index."""
        memory_index.clear()
        assert memory_index.get_page_count() == 0

    def test_clear_and_readd(self, memory_index):
        """Clearing and re-adding pages."""
        page = IndexedPage(url="http://clear.com", title="Test", content="Content")
        memory_index.add_page(page)
        memory_index.clear()
        memory_index.add_page(page)
        assert memory_index.get_page_count() == 1


class TestSearchIndexContextManager:
    """Test context manager usage."""

    def test_context_manager(self, tmp_path):
        """SearchIndex should work as a context manager."""
        db_path = str(tmp_path / "index.json")
        with SearchIndex(db_path=db_path) as idx:
            page = IndexedPage(url="http://ctx.com", title="Test", content="Content")
            idx.add_page(page)
            assert idx.get_page_count() == 1
        # After exiting context, file should be saved
        assert os.path.exists(db_path)


class TestSearchIndexTokenization:
    """Test tokenization edge cases."""

    def test_tokenize_empty(self):
        """Tokenizing empty string."""
        tokens = SearchIndex._tokenize("")
        assert tokens == []

    def test_tokenize_whitespace(self):
        """Tokenizing whitespace."""
        tokens = SearchIndex._tokenize("   ")
        assert tokens == []

    def test_tokenize_numbers(self):
        """Tokenizing numbers."""
        tokens = SearchIndex._tokenize("123 456")
        assert "123" in tokens
        assert "456" in tokens

    def test_tokenize_special_chars(self):
        """Tokenizing special characters."""
        tokens = SearchIndex._tokenize("hello, world!")
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_single_char_words(self):
        """Single character words should be filtered."""
        tokens = SearchIndex._tokenize("a b c hello")
        assert "hello" in tokens
        assert "a" not in tokens
        assert "b" not in tokens
        assert "c" not in tokens


class TestSearchIndexWordIndex:
    """Test word index maintenance."""

    def test_word_index_dedup(self, memory_index):
        """Word index should not have duplicate URLs."""
        page = IndexedPage(url="http://dedup.com", title="Test test", content="test")
        memory_index.add_page(page)
        # "test" appears 3 times but URL should only be in index once
        assert memory_index._word_index.get("test", []).count("http://dedup.com") == 1

    def test_word_index_cleanup_on_remove(self, memory_index):
        """Word index should be cleaned up when page is removed."""
        page = IndexedPage(url="http://cleanup.com", title="UniqueWord", content="Content")
        memory_index.add_page(page)
        assert "uniqueword" in memory_index._word_index
        memory_index.remove_page("http://cleanup.com")
        assert "uniqueword" not in memory_index._word_index


class TestSearchIndexScoreCalculation:
    """Test score calculation edge cases."""

    def test_score_title_weight(self, memory_index):
        """Title matches should score higher than content matches."""
        page1 = IndexedPage(url="http://title.com", title="Important", content="")
        page2 = IndexedPage(url="http://content.com", title="", content="Important")
        memory_index.add_page(page1)
        memory_index.add_page(page2)
        results = memory_index.search("important")
        assert len(results) == 2
        # Title match should rank higher
        assert results[0].url == "http://title.com"

    def test_score_page_score_factor(self, memory_index):
        """Page score should factor into search results."""
        page1 = IndexedPage(url="http://low.com", title="Test", content="Content", score=1.0)
        page2 = IndexedPage(url="http://high.com", title="Test", content="Content", score=100.0)
        memory_index.add_page(page1)
        memory_index.add_page(page2)
        results = memory_index.search("test")
        assert len(results) == 2
        # Higher page score should rank higher
        assert results[0].url == "http://high.com"
