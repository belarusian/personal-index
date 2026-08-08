"""Tests for personal_index.search."""

import pytest
import tempfile
import shutil
from pathlib import Path

from personal_index.models import CrawledPage, Interest
from personal_index.search import SearchIndex


@pytest.fixture
def temp_index_dir():
    """Create a temporary directory for the search index."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def search_index(temp_index_dir):
    """Create a SearchIndex instance with a temp directory."""
    return SearchIndex(index_dir=temp_index_dir)


@pytest.fixture
def sample_pages():
    """Create sample crawled pages for testing."""
    return [
        CrawledPage(
            url="https://example.com/python",
            title="Python Programming Guide",
            content="Python is a versatile programming language used for web development, data science, and AI.",
            meta_description="Learn Python programming from basics to advanced.",
            matched_interests=["python"],
            word_count=15,
        ),
        CrawledPage(
            url="https://example.com/javascript",
            title="JavaScript Tutorial",
            content="JavaScript is the language of the web. Learn to build interactive websites.",
            meta_description="Complete JavaScript tutorial for beginners.",
            matched_interests=["javascript"],
            word_count=14,
        ),
        CrawledPage(
            url="https://example.com/machine-learning",
            title="Machine Learning with Python",
            content="Machine learning uses Python libraries like TensorFlow and PyTorch for AI development.",
            meta_description="Introduction to machine learning and AI.",
            matched_interests=["ai", "python"],
            word_count=14,
        ),
    ]


class TestSearchIndex:
    def test_create_index(self, search_index):
        assert search_index.get_document_count() == 0

    def test_add_document(self, search_index, sample_pages):
        search_index.add_document(sample_pages[0])
        assert search_index.get_document_count() == 1

    def test_add_multiple_documents(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        assert search_index.get_document_count() == 3

    def test_search_returns_results(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("python")
        assert len(results) > 0

    def test_search_relevance_ordering(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("python programming")
        # Results should be ordered by relevance
        assert results[0].score >= results[-1].score

    def test_search_with_interest_filter(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("python", interest_filter="ai")
        for result in results:
            assert "ai" in result.page.matched_interests

    def test_search_limit(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("language", limit=1)
        assert len(results) <= 1

    def test_search_no_results(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("xyznonexistent123")
        assert len(results) == 0

    def test_search_with_highlights(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search_with_highlights("python")
        assert len(results) > 0
        # At least some results should have highlights
        has_highlights = any(r.highlights for r in results)
        assert has_highlights

    def test_remove_document(self, search_index, sample_pages):
        search_index.add_document(sample_pages[0])
        assert search_index.get_document_count() == 1
        search_index.remove_document(sample_pages[0].id)
        assert search_index.get_document_count() == 0

    def test_remove_nonexistent_document(self, search_index):
        result = search_index.remove_document("nonexistent-id")
        assert result is False

    def test_clear_index(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        assert search_index.get_document_count() == 3
        search_index.clear()
        assert search_index.get_document_count() == 0

    def test_rebuild_index(self, search_index, sample_pages):
        search_index.rebuild(sample_pages)
        assert search_index.get_document_count() == 3

    def test_search_result_has_score(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("python")
        for result in results:
            assert result.score > 0

    def test_search_result_has_page(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("python")
        for result in results:
            assert isinstance(result.page, CrawledPage)
            assert result.page.url.startswith("https://")

    def test_search_title_boost(self, search_index, sample_pages):
        """Test that title matches get higher scores."""
        for page in sample_pages:
            search_index.add_document(page)
        results = search_index.search("Python Programming Guide")
        assert len(results) > 0
        # The page with matching title should rank high
        top_result = results[0]
        assert "Python" in top_result.page.title or "python" in top_result.page.title.lower()

    def test_optimize(self, search_index, sample_pages):
        for page in sample_pages:
            search_index.add_document(page)
        search_index.optimize()
        # Should not raise
        assert search_index.get_document_count() == 3
