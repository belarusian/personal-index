"""Tests for personal_index.search_index."""

import pytest

from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex


@pytest.fixture
def index(tmp_path):
    return SearchIndex(index_path=str(tmp_path / "index.json"))


class TestSearchIndex:
    """Tests for SearchIndex."""

    def test_empty_search(self, index: SearchIndex):
        results = index.search("python")
        assert results == []

    def test_add_and_search(self, index: SearchIndex):
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Programming",
            content="Python is a great programming language",
        )
        index.add(page)
        results = index.search("python")
        assert len(results) == 1
        assert results[0][0] == "https://example.com/python"
        assert results[0][1] > 0

    def test_search_relevance_ordering(self, index: SearchIndex):
        index.add(CrawledPage(
            url="https://a.com",
            title="Python Basics",
            content="Python is great for beginners",
        ))
        index.add(CrawledPage(
            url="https://b.com",
            title="Advanced Python",
            content="Python Python Python advanced techniques",
        ))
        results = index.search("python")
        assert results[0][0] == "https://b.com"

    def test_title_boost(self, index: SearchIndex):
        index.add(CrawledPage(
            url="https://a.com",
            title="Python",
            content="Some content about programming",
        ))
        index.add(CrawledPage(
            url="https://b.com",
            title="Programming",
            content="Python is mentioned here",
        ))
        results = index.search("python")
        assert results[0][0] == "https://a.com"

    def test_remove_page(self, index: SearchIndex):
        index.add(CrawledPage(
            url="https://example.com",
            title="Test",
            content="Hello world",
        ))
        assert index.count() == 1
        assert index.remove("https://example.com") is True
        assert index.count() == 0

    def test_remove_nonexistent(self, index: SearchIndex):
        assert index.remove("https://nonexistent.com") is False

    def test_get_page(self, index: SearchIndex):
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Some content",
        )
        index.add(page)
        found = index.get("https://example.com")
        assert found is not None
        assert found.title == "Test Page"

    def test_get_nonexistent(self, index: SearchIndex):
        assert index.get("https://nonexistent.com") is None

    def test_clear_index(self, index: SearchIndex):
        index.add(CrawledPage(url="https://a.com", title="A"))
        index.add(CrawledPage(url="https://b.com", title="B"))
        index.clear()
        assert index.count() == 0

    def test_search_limit(self, index: SearchIndex):
        for i in range(30):
            index.add(CrawledPage(
                url=f"https://example{i}.com",
                title=f"Python page {i}",
                content=f"Python content number {i}",
            ))
        results = index.search("python", limit=5)
        assert len(results) == 5

    def test_persistence(self, tmp_path):
        path = str(tmp_path / "persist.json")
        idx1 = SearchIndex(index_path=path)
        idx1.add(CrawledPage(
            url="https://example.com",
            title="Persistent",
            content="This should persist",
        ))
        idx2 = SearchIndex(index_path=path)
        assert idx2.count() == 1
        assert idx2.get("https://example.com").title == "Persistent"

    def test_urls_list(self, index: SearchIndex):
        index.add(CrawledPage(url="https://a.com", title="A"))
        index.add(CrawledPage(url="https://b.com", title="B"))
        urls = index.urls()
        assert "https://a.com" in urls
        assert "https://b.com" in urls

    def test_tokenize(self):
        tokens = SearchIndex._tokenize("Hello World! Python 3.10 is great.")
        assert tokens == ["hello", "world", "python", "3", "10", "is", "great"]

    def test_tokenize_empty(self):
        assert SearchIndex._tokenize("") == []

    def test_interest_relevance_boost(self, index: SearchIndex):
        index.add(CrawledPage(
            url="https://a.com",
            title="Page A",
            content="Some content",
            relevance_score=10.0,
        ))
        index.add(CrawledPage(
            url="https://b.com",
            title="Page B",
            content="Some content",
            relevance_score=0.0,
        ))
        results = index.search("content")
        assert results[0][0] == "https://a.com"


class TestSearchIndexLoadGuard:
    """Regression tests: non-dict JSON index file must not crash _load."""

    def test_load_null_file(self, tmp_path):
        path = str(tmp_path / "index.json")
        with open(path, "w") as f:
            f.write("null")
        idx = SearchIndex(index_path=path)
        assert idx.count() == 0

    def test_load_list_file(self, tmp_path):
        path = str(tmp_path / "index.json")
        with open(path, "w") as f:
            f.write("[1, 2, 3]")
        idx = SearchIndex(index_path=path)
        assert idx.count() == 0

    def test_load_number_file(self, tmp_path):
        path = str(tmp_path / "index.json")
        with open(path, "w") as f:
            f.write("42")
        idx = SearchIndex(index_path=path)
        assert idx.count() == 0
