"""Tests for search index module."""

import pytest
from pathlib import Path
from personal_index.content import ExtractedContent
from personal_index.index import SearchIndex, SearchResult, DocumentEntry


@pytest.fixture
def temp_index(tmp_path):
    """Create a temporary search index."""
    return SearchIndex(index_dir=tmp_path / "test_index")


@pytest.fixture
def sample_content():
    """Create sample extracted content."""
    return ExtractedContent(
        url="http://example.com/page1",
        title="Python Programming Tutorial",
        text="Python is a great programming language. It is used for web development, data science, and machine learning.",
        meta_description="Learn Python programming from scratch",
        meta_keywords=["python", "programming", "tutorial"],
        headings=["h1: Python Tutorial", "h2: Getting Started"],
    )


class TestDocumentEntry:
    def test_creation(self):
        entry = DocumentEntry(url="http://example.com")
        assert entry.url == "http://example.com"
        assert entry.title == ""
        assert entry.token_count == 0

    def test_to_dict(self):
        entry = DocumentEntry(
            url="http://example.com",
            title="Test",
            interest_topics=["AI"],
        )
        d = entry.to_dict()
        assert d["url"] == "http://example.com"
        assert d["title"] == "Test"
        assert d["interest_topics"] == ["AI"]

    def test_from_dict(self):
        data = {
            "url": "http://example.com",
            "title": "Test",
            "text": "Some text",
            "meta_description": "",
            "keywords": [],
            "token_count": 10,
            "indexed_at": "",
            "interest_topics": ["AI"],
        }
        entry = DocumentEntry.from_dict(data)
        assert entry.url == "http://example.com"
        assert entry.interest_topics == ["AI"]


class TestSearchResult:
    def test_creation(self):
        result = SearchResult(url="http://example.com", title="Test", score=1.0)
        assert result.url == "http://example.com"
        assert result.score == 1.0

    def test_to_dict(self):
        result = SearchResult(
            url="http://example.com",
            title="Test",
            score=1.5,
            matched_terms=["python"],
        )
        d = result.to_dict()
        assert d["score"] == 1.5
        assert d["matched_terms"] == ["python"]


class TestSearchIndex:
    def test_create_index(self, temp_index):
        assert temp_index.get_document_count() == 0
        assert temp_index.get_term_count() == 0

    def test_add_document(self, temp_index, sample_content):
        temp_index.add_document(sample_content, interest_topics=["programming"])
        assert temp_index.get_document_count() == 1
        assert temp_index.get_term_count() > 0

    def test_add_multiple_documents(self, temp_index):
        content1 = ExtractedContent(
            url="http://example.com/page1",
            title="Python Tutorial",
            text="Python is a great language for programming.",
        )
        content2 = ExtractedContent(
            url="http://example.com/page2",
            title="JavaScript Guide",
            text="JavaScript is used for web development.",
        )
        temp_index.add_document(content1)
        temp_index.add_document(content2)
        assert temp_index.get_document_count() == 2

    def test_search_basic(self, temp_index, sample_content):
        temp_index.add_document(sample_content)
        results = temp_index.search("python programming")
        assert len(results) > 0
        assert results[0].url == "http://example.com/page1"
        assert results[0].score > 0

    def test_search_no_results(self, temp_index):
        results = temp_index.search("nonexistent term xyz123")
        assert len(results) == 0

    def test_search_limit(self, temp_index):
        for i in range(10):
            content = ExtractedContent(
                url=f"http://example.com/page{i}",
                title=f"Page {i}",
                text=f"This is page number {i} with some content.",
            )
            temp_index.add_document(content)
        results = temp_index.search("page", limit=3)
        assert len(results) <= 3

    def test_search_relevance(self, temp_index):
        # Page with more relevant terms should rank higher
        content1 = ExtractedContent(
            url="http://example.com/relevant",
            title="Python Deep Learning",
            text="Python is great for deep learning and machine learning with neural networks.",
        )
        content2 = ExtractedContent(
            url="http://example.com/less_relevant",
            title="Python Basics",
            text="Python has basic syntax.",
        )
        temp_index.add_document(content1)
        temp_index.add_document(content2)
        results = temp_index.search("deep learning neural")
        assert len(results) >= 1
        # The more relevant page should rank higher
        assert results[0].url == "http://example.com/relevant"

    def test_remove_document(self, temp_index, sample_content):
        temp_index.add_document(sample_content)
        assert temp_index.get_document_count() == 1
        removed = temp_index.remove_document("http://example.com/page1")
        assert removed is True
        assert temp_index.get_document_count() == 0

    def test_remove_nonexistent(self, temp_index):
        removed = temp_index.remove_document("http://nonexistent.com")
        assert removed is False

    def test_get_document(self, temp_index, sample_content):
        temp_index.add_document(sample_content)
        doc = temp_index.get_document("http://example.com/page1")
        assert doc is not None
        assert doc.title == "Python Programming Tutorial"

    def test_get_document_not_found(self, temp_index):
        doc = temp_index.get_document("http://nonexistent.com")
        assert doc is None

    def test_clear_index(self, temp_index, sample_content):
        temp_index.add_document(sample_content)
        temp_index.clear()
        assert temp_index.get_document_count() == 0
        assert temp_index.get_term_count() == 0

    def test_get_urls(self, temp_index):
        content1 = ExtractedContent(url="http://example.com/a", title="A", text="Text A")
        content2 = ExtractedContent(url="http://example.com/b", title="B", text="Text B")
        temp_index.add_document(content1)
        temp_index.add_document(content2)
        urls = temp_index.get_urls()
        assert "http://example.com/a" in urls
        assert "http://example.com/b" in urls

    def test_get_stats(self, temp_index, sample_content):
        temp_index.add_document(sample_content)
        stats = temp_index.get_stats()
        assert stats["document_count"] == 1
        assert stats["term_count"] > 0

    def test_save_and_load(self, tmp_path, sample_content):
        index_dir = tmp_path / "persist_index"
        index = SearchIndex(index_dir=index_dir)
        index.add_document(sample_content)
        index.save()

        # Load new instance
        loaded = SearchIndex(index_dir=index_dir)
        assert loaded.get_document_count() == 1
        results = loaded.search("python")
        assert len(results) > 0

    def test_interest_boost(self, temp_index):
        content1 = ExtractedContent(
            url="http://example.com/ai",
            title="AI Research",
            text="Artificial intelligence and machine learning research.",
        )
        content2 = ExtractedContent(
            url="http://example.com/cooking",
            title="Cooking Tips",
            text="Artificial flavors in cooking and recipes.",
        )
        temp_index.add_document(content1, interest_topics=["AI"])
        temp_index.add_document(content2, interest_topics=["cooking"])
        results = temp_index.search("artificial intelligence")
        assert len(results) > 0
        # AI page should rank higher due to interest boost
        assert results[0].url == "http://example.com/ai"

    def test_snippet_generation(self, temp_index):
        content = ExtractedContent(
            url="http://example.com/long",
            title="Long Page",
            text="This is a very long page with lots of content. "
                 "It discusses many topics including python programming. "
                 "More and more text follows here.",
        )
        temp_index.add_document(content)
        results = temp_index.search("python programming")
        assert len(results) > 0
        assert "python" in results[0].snippet.lower()
