"""Tests for the search index module."""

import pytest
from personal_index.index import Document, SearchResult, SearchIndex


class TestDocument:
    def test_create_document(self):
        doc = Document(url="https://example.com")
        assert doc.url == "https://example.com"
        assert doc.title == ""
        assert doc.content == ""

    def test_searchable_text(self):
        doc = Document(url="https://example.com", title="Hello", content="World")
        assert doc.searchable_text == "Hello World"

    def test_searchable_text_empty(self):
        doc = Document(url="https://example.com")
        assert doc.searchable_text == " "


class TestSearchIndex:
    def test_tokenize(self):
        tokens = SearchIndex.tokenize("Hello World! This is a TEST.")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_tokenize_html(self):
        tokens = SearchIndex.tokenize("<p>Hello</p> <b>World</b>")
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_short_words(self):
        tokens = SearchIndex.tokenize("a b I am")
        assert "am" in tokens
        assert "a" not in tokens
        assert "b" not in tokens

    def test_tokenize_empty(self):
        tokens = SearchIndex.tokenize("")
        assert tokens == []

    def test_add_document(self):
        index = SearchIndex()
        doc = Document(url="https://example.com", title="Test", content="Hello world")
        index.add_document(doc)
        assert len(index.documents) == 1

    def test_add_duplicate_document(self):
        index = SearchIndex()
        doc1 = Document(url="https://example.com", content="First")
        doc2 = Document(url="https://example.com", content="Second")
        index.add_document(doc1)
        index.add_document(doc2)
        assert len(index.documents) == 1
        assert index.documents["https://example.com"].content == "Second"

    def test_remove_document(self):
        index = SearchIndex()
        doc = Document(url="https://example.com", content="Hello world")
        index.add_document(doc)
        index.remove_document("https://example.com")
        assert len(index.documents) == 0

    def test_remove_nonexistent(self):
        index = SearchIndex()
        index.remove_document("https://nonexistent.com")  # Should not raise

    def test_search_basic(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="python programming"))
        index.add_document(Document(url="https://b.com", content="java programming"))
        results = index.search("python")
        assert len(results) == 1
        assert results[0].document.url == "https://a.com"

    def test_search_relevance(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="python python python"))
        index.add_document(Document(url="https://b.com", content="python"))
        results = index.search("python")
        assert results[0].document.url == "https://a.com"
        assert results[0].score > results[1].score

    def test_search_no_results(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="hello"))
        results = index.search("nonexistent")
        assert len(results) == 0

    def test_search_limit(self):
        index = SearchIndex()
        for i in range(10):
            index.add_document(Document(url=f"https://{i}.com", content="test"))
        results = index.search("test", limit=3)
        assert len(results) == 3

    def test_search_matched_terms(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="python java"))
        results = index.search("python java")
        assert "python" in results[0].matched_terms
        assert "java" in results[0].matched_terms

    def test_get_document(self):
        index = SearchIndex()
        doc = Document(url="https://example.com", content="test")
        index.add_document(doc)
        retrieved = index.get_document("https://example.com")
        assert retrieved is not None
        assert retrieved.content == "test"

    def test_get_document_not_found(self):
        index = SearchIndex()
        assert index.get_document("https://nonexistent.com") is None

    def test_stats(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="hello world"))
        stats = index.get_stats()
        assert stats["total_documents"] == 1
        assert stats["total_terms"] >= 2

    def test_clear(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="test"))
        index.clear()
        assert len(index.documents) == 0
        assert index._num_docs == 0

    def test_search_empty_query(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", content="test"))
        results = index.search("")
        assert len(results) == 0

    def test_search_title_and_content(self):
        index = SearchIndex()
        index.add_document(Document(url="https://a.com", title="Python Guide", content="Learn coding"))
        results = index.search("python")
        assert len(results) == 1
        assert results[0].document.url == "https://a.com"
