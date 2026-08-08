"""Tests for search index module."""

import pytest
from pathlib import Path
from personal_index.models import Page
from personal_index.indexer import SearchIndex


class TestSearchIndex:
    def setup_method(self) -> None:
        self.index = SearchIndex()

    def test_add_page(self):
        page = Page(
            url="https://example.com/page1",
            title="Machine Learning Guide",
            content="Machine learning is a subset of artificial intelligence.",
        )
        self.index.add_page(page)
        assert self.index.num_documents == 1

    def test_add_multiple_pages(self):
        pages = [
            Page(url="https://example.com/1", title="ML Guide", content="Machine learning basics"),
            Page(url="https://example.com/2", title="AI Overview", content="Artificial intelligence overview"),
        ]
        for page in pages:
            self.index.add_page(page)
        assert self.index.num_documents == 2

    def test_search_returns_results(self):
        page = Page(
            url="https://example.com/ml",
            title="Machine Learning",
            content="Machine learning is great for data science.",
        )
        self.index.add_page(page)
        results = self.index.search("machine learning")
        assert len(results) == 1
        assert results[0].page.url == "https://example.com/ml"

    def test_search_no_results(self):
        page = Page(
            url="https://example.com",
            title="Hello",
            content="Hello world",
        )
        self.index.add_page(page)
        results = self.index.search("nonexistent term xyz")
        assert len(results) == 0

    def test_search_ranking(self):
        # Page with more relevant content should rank higher
        page1 = Page(
            url="https://example.com/1",
            title="ML Basics",
            content="Machine learning is important.",
        )
        page2 = Page(
            url="https://example.com/2",
            title="ML Deep Dive",
            content="Machine learning machine learning machine learning deep dive.",
        )
        self.index.add_page(page1)
        self.index.add_page(page2)
        results = self.index.search("machine learning")
        assert len(results) == 2
        # page2 should rank higher due to more mentions
        assert results[0].page.url == "https://example.com/2"

    def test_search_limit(self):
        for i in range(10):
            self.index.add_page(
                Page(
                    url=f"https://example.com/{i}",
                    title=f"Page {i}",
                    content="Machine learning test content.",
                )
            )
        results = self.index.search("machine learning", limit=3)
        assert len(results) <= 3

    def test_search_min_score(self):
        page = Page(
            url="https://example.com",
            title="Test",
            content="Some test content here.",
        )
        self.index.add_page(page)
        results = self.index.search("test", min_score=1000.0)
        assert len(results) == 0

    def test_search_interest_filter(self):
        page1 = Page(
            url="https://example.com/1",
            title="ML",
            content="Machine learning content",
            matched_interests=["machine learning"],
        )
        page2 = Page(
            url="https://example.com/2",
            title="Cooking",
            content="Cooking recipe content",
            matched_interests=["cooking"],
        )
        self.index.add_page(page1)
        self.index.add_page(page2)
        results = self.index.search("content", interest_filter=["machine learning"])
        assert len(results) == 1
        assert results[0].page.url == "https://example.com/1"

    def test_remove_page(self):
        page = Page(
            url="https://example.com",
            title="Test",
            content="Test content",
        )
        self.index.add_page(page)
        assert self.index.num_documents == 1
        removed = self.index.remove_page(page.id)
        assert removed is True
        assert self.index.num_documents == 0

    def test_remove_nonexistent_page(self):
        removed = self.index.remove_page("nonexistent")
        assert removed is False

    def test_save_and_load(self, tmp_path: Path):
        page = Page(
            url="https://example.com",
            title="Test Page",
            content="Test content for saving.",
        )
        self.index.add_page(page)
        self.index.index_dir = tmp_path
        self.index.save()

        new_index = SearchIndex(index_dir=tmp_path)
        new_index.load()
        assert new_index.num_documents == 1
        results = new_index.search("test content")
        assert len(results) == 1

    def test_clear(self):
        self.index.add_page(Page(url="https://example.com", content="test"))
        self.index.clear()
        assert self.index.num_documents == 0
        assert self.index.num_terms == 0

    def test_get_page(self):
        page = Page(url="https://example.com", title="Test", content="test")
        self.index.add_page(page)
        retrieved = self.index.get_page(page.id)
        assert retrieved is not None
        assert retrieved.url == "https://example.com"

    def test_get_nonexistent_page(self):
        assert self.index.get_page("nonexistent") is None

    def test_get_all_pages(self):
        for i in range(3):
            self.index.add_page(Page(url=f"https://example.com/{i}", content="test"))
        pages = self.index.get_all_pages()
        assert len(pages) == 3

    def test_empty_query(self):
        results = self.index.search("")
        assert results == []

    def test_num_terms(self):
        page = Page(
            url="https://example.com",
            content="hello world foo bar",
        )
        self.index.add_page(page)
        assert self.index.num_terms == 4
