"""Tests for the search index module."""

import pytest

from personal_index.index import IndexedPage, SearchIndex


@pytest.fixture
def search_index(tmp_path):
    db_path = str(tmp_path / "test_index.db")
    idx = SearchIndex(db_path=db_path)
    yield idx
    idx.close()


def _make_page(url: str, title: str, content: str, keywords: list | None = None, score: float = 1.0) -> IndexedPage:
    return IndexedPage(
        url=url,
        title=title,
        content=content,
        keywords=keywords or [],
        score=score,
        indexed_at="2024-01-01T00:00:00",
        source_interest="test",
        word_count=len(content.split()),
    )


class TestSearchIndex:
    def test_create_index(self, tmp_path):
        db_path = str(tmp_path / "test.db")
        idx = SearchIndex(db_path=db_path)
        assert idx.get_page_count() == 0
        idx.close()

    def test_add_page(self, search_index):
        page = _make_page("https://example.com/1", "Page One", "Hello world this is a test page")
        page_id = search_index.add_page(page)
        assert page_id > 0
        assert search_index.get_page_count() == 1

    def test_add_duplicate_page(self, search_index):
        page1 = _make_page("https://example.com/1", "Page One", "Original content")
        page2 = _make_page("https://example.com/1", "Page One Updated", "Updated content here")
        search_index.add_page(page1)
        search_index.add_page(page2)
        assert search_index.get_page_count() == 1
        retrieved = search_index.get_page("https://example.com/1")
        assert retrieved.title == "Page One Updated"

    def test_remove_page(self, search_index):
        page = _make_page("https://example.com/1", "Page One", "Some content")
        search_index.add_page(page)
        assert search_index.remove_page("https://example.com/1") is True
        assert search_index.get_page_count() == 0

    def test_remove_nonexistent_page(self, search_index):
        assert search_index.remove_page("https://nonexistent.com") is False

    def test_search_basic(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Python Guide", "Learn Python programming"))
        search_index.add_page(_make_page("https://example.com/2", "Java Guide", "Learn Java programming"))
        results = search_index.search("python")
        assert len(results) == 1
        assert results[0].url == "https://example.com/1"

    def test_search_multiple_results(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Python Basics", "Python is great for web development"))
        search_index.add_page(_make_page("https://example.com/2", "Python Advanced", "Python is also great for data science"))
        results = search_index.search("python")
        assert len(results) == 2

    def test_search_no_results(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Python Guide", "Learn Python"))
        results = search_index.search("cooking")
        assert len(results) == 0

    def test_search_relevance_ordering(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Python", "Python Python Python"))
        search_index.add_page(_make_page("https://example.com/2", "Python", "Python is nice"))
        results = search_index.search("python")
        assert results[0].url == "https://example.com/1"
        assert results[0].relevance_score >= results[1].relevance_score

    def test_search_limit(self, search_index):
        for i in range(30):
            search_index.add_page(_make_page(f"https://example.com/{i}", f"Page {i}", f"Content about topic {i}"))
        results = search_index.search("topic", limit=10)
        assert len(results) <= 10

    def test_get_page(self, search_index):
        page = _make_page("https://example.com/1", "Test Page", "Test content here")
        search_index.add_page(page)
        retrieved = search_index.get_page("https://example.com/1")
        assert retrieved is not None
        assert retrieved.title == "Test Page"

    def test_get_nonexistent_page(self, search_index):
        assert search_index.get_page("https://nonexistent.com") is None

    def test_list_pages(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Page 1", "Content 1", score=2.0))
        search_index.add_page(_make_page("https://example.com/2", "Page 2", "Content 2", score=1.0))
        pages = search_index.list_pages()
        assert len(pages) == 2
        assert pages[0].score >= pages[1].score

    def test_clear_index(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Page 1", "Content"))
        search_index.clear()
        assert search_index.get_page_count() == 0

    def test_search_result_fields(self, search_index):
        search_index.add_page(_make_page("https://example.com/1", "Test Title", "Test content"))
        results = search_index.search("test")
        assert len(results) == 1
        result = results[0]
        assert result.url == "https://example.com/1"
        assert result.title == "Test Title"
        assert result.snippet is not None
        assert result.relevance_score > 0

    def test_tokenization(self, search_index):
        tokens = search_index._tokenize("Hello World! This is a TEST.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens
        assert len(tokens) == 3

    def test_empty_tokenization(self, search_index):
        assert search_index._tokenize("") == []
        assert search_index._tokenize(None) == []

    def test_create_snippet_does_not_mark_up_terms(self, search_index):
        # Pins the corrected docstring claim: _create_snippet windows around
        # the first query term and returns PLAIN text — it does not mark up
        # / highlight the matched terms.
        content = "The quick brown fox jumps over the lazy dog near the river bank"
        snippet = search_index._create_snippet(content, "fox", length=40)
        # The matched term appears verbatim in the snippet...
        assert "fox" in snippet
        # ...but no highlight markup of any common kind is applied.
        assert "<mark>" not in snippet
        assert "</mark>" not in snippet
        assert "*" not in snippet
        assert "**" not in snippet
        assert "<b>" not in snippet
        assert "<strong>" not in snippet
        # The snippet is a substring-window of the original (plain text).
        stripped = snippet.strip(".")
        assert stripped in content

    def test_context_manager(self, tmp_path):
        db_path = str(tmp_path / "ctx.db")
        with SearchIndex(db_path=db_path) as idx:
            idx.add_page(_make_page("https://example.com/1", "Test", "Content"))
            assert idx.get_page_count() == 1


class TestSearchIndexLoadNonePath:
    """Tests for TICKET-28: _load() guards against None path."""

    def test_load_with_none_path_does_not_crash(self):
        """_load() should return early when db_path is None."""
        idx = SearchIndex(db_path=None)
        # Explicitly call _load() - should not raise TypeError
        idx._load()
        assert idx._pages == {}

    def test_load_with_none_path_after_init(self):
        """_load() called manually after init with None path should be safe."""
        idx = SearchIndex()
        idx._load()
        assert idx._pages == {}

    def test_save_with_none_path_does_not_crash(self):
        """_save() should return early when db_path is None."""
        idx = SearchIndex(db_path=None)
        idx._save()
        # Should not raise any error


class TestRemovePageNoUnusedVariable:
    """Tests for TICKET-32: No unused variable in remove_page()."""

    def test_remove_page_no_unused_variable(self, search_index):
        """remove_page should not assign unused variable page."""
        import inspect
        source = inspect.getsource(search_index.remove_page)
        assert 'page = self._pages.pop' not in source,             'remove_page should not assign unused variable page'

    def test_remove_page_cleans_word_index(self, search_index):
        """remove_page should clean up word index entries."""
        page = _make_page('https://example.com/1', 'Page One', 'Hello world test')
        search_index.add_page(page)
        # Verify word index has entries
        assert 'hello' in search_index._word_index
        assert 'world' in search_index._word_index
        # Remove page
        result = search_index.remove_page('https://example.com/1')
        assert result is True
        # Verify word index is cleaned up
        assert 'hello' not in search_index._word_index
        assert 'world' not in search_index._word_index
        assert search_index.get_page_count() == 0


class TestSearchIndexNonDictJSON:
    """Regression tests for TICKET-264: non-dict top-level JSON in storage."""

    def test_null_storage_resets_to_empty(self, tmp_path):
        import json
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            json.dump(None, f)
        idx = SearchIndex(db_path=db_path)
        assert idx._pages == {}
        assert idx._word_index == {}

    def test_list_storage_resets_to_empty(self, tmp_path):
        import json
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            json.dump([1, 2, 3], f)
        idx = SearchIndex(db_path=db_path)
        assert idx._pages == {}
        assert idx._word_index == {}

    def test_number_storage_resets_to_empty(self, tmp_path):
        import json
        db_path = str(tmp_path / "index.json")
        with open(db_path, "w") as f:
            json.dump(42, f)
        idx = SearchIndex(db_path=db_path)
        assert idx._pages == {}
        assert idx._word_index == {}
