"""Tests for search index module (consolidated from indexer.py into search_index.py)."""

import pytest
import tempfile
from pathlib import Path
from personal_index.models import CrawledPage
from personal_index.search_index import SearchIndex


class TestSearchIndex:
    def setup_method(self) -> None:
        self.tmp_dir = tempfile.mkdtemp()
        self.index_path = Path(self.tmp_dir) / "index.json"
        self.index = SearchIndex(index_path=str(self.index_path))

    def test_add_page(self):
        page = CrawledPage(
            url="https://example.com/page1",
            title="Machine Learning Guide",
            content="Machine learning is a subset of artificial intelligence.",
        )
        self.index.add(page)
        assert self.index.count() == 1

    def test_add_multiple_pages(self):
        pages = [
            CrawledPage(url="https://example.com/1", title="ML Guide", content="Machine learning basics"),
            CrawledPage(url="https://example.com/2", title="AI Overview", content="Artificial intelligence overview"),
        ]
        for page in pages:
            self.index.add(page)
        assert self.index.count() == 2

    def test_search_returns_results(self):
        page = CrawledPage(
            url="https://example.com/ml",
            title="Machine Learning",
            content="Machine learning is great for data science.",
        )
        self.index.add(page)
        results = self.index.search("machine learning")
        assert len(results) == 1
        assert results[0][0] == "https://example.com/ml"

    def test_search_no_results(self):
        page = CrawledPage(
            url="https://example.com",
            title="Hello",
            content="Hello world",
        )
        self.index.add(page)
        results = self.index.search("nonexistent term xyz")
        assert len(results) == 0

    def test_search_ranking(self):
        page1 = CrawledPage(
            url="https://example.com/1",
            title="ML Basics",
            content="Machine learning is important.",
        )
        page2 = CrawledPage(
            url="https://example.com/2",
            title="ML Deep Dive",
            content="Machine learning machine learning machine learning deep dive.",
        )
        self.index.add(page1)
        self.index.add(page2)
        results = self.index.search("machine learning")
        assert len(results) == 2
        # Both pages should have positive scores
        for url, score in results:
            assert score > 0

    def test_search_limit(self):
        for i in range(10):
            self.index.add(
                CrawledPage(
                    url=f"https://example.com/{i}",
                    title=f"Page {i}",
                    content="Machine learning test content.",
                )
            )
        results = self.index.search("machine learning", limit=3)
        assert len(results) <= 3

    def test_remove_page(self):
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Test content",
        )
        self.index.add(page)
        assert self.index.count() == 1
        removed = self.index.remove("https://example.com")
        assert removed is True
        assert self.index.count() == 0

    def test_remove_nonexistent_page(self):
        removed = self.index.remove("nonexistent")
        assert removed is False

    def test_save_and_load(self, tmp_path: Path):
        index_path = str(tmp_path / "index.json")
        index = SearchIndex(index_path=index_path)
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="Test content for saving.",
        )
        index.add(page)

        new_index = SearchIndex(index_path=index_path)
        assert new_index.count() == 1
        results = new_index.search("test content")
        assert len(results) == 1

    def test_clear(self):
        self.index.add(CrawledPage(url="https://example.com", content="test"))
        self.index.clear()
        assert self.index.count() == 0

    def test_get_page(self):
        page = CrawledPage(url="https://example.com", title="Test", content="test")
        self.index.add(page)
        retrieved = self.index.get("https://example.com")
        assert retrieved is not None
        assert retrieved.url == "https://example.com"

    def test_get_nonexistent_page(self):
        assert self.index.get("nonexistent") is None

    def test_get_all_pages(self):
        for i in range(3):
            self.index.add(CrawledPage(url=f"https://example.com/{i}", content="test"))
        pages = self.index.urls()
        assert len(pages) == 3

    def test_empty_query(self):
        results = self.index.search("")
        assert results == []
