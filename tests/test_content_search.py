"""Tests for content search module."""

import pytest

from personal_index.content_search.search_engine import SearchEngine
from personal_index.content_search.search_index import SearchIndex
from personal_index.content_search.search_result import SearchResult, SearchResponse
from personal_index.content_search.tokenizer import Tokenizer


class TestTokenizer:
    def test_tokenize_basic(self) -> None:
        t = Tokenizer()
        tokens = t.tokenize("Hello world of Python")
        assert "hello" in tokens
        assert "world" in tokens
        assert "python" in tokens
        assert "of" not in tokens  # stopword

    def test_tokenize_empty(self) -> None:
        t = Tokenizer()
        assert t.tokenize("") == []

    def test_tokenize_min_length(self) -> None:
        t = Tokenizer(min_token_length=3)
        tokens = t.tokenize("a big cat")
        assert "big" in tokens
        assert "cat" in tokens
        assert "a" not in tokens

    def test_tokenize_with_positions(self) -> None:
        t = Tokenizer()
        result = t.tokenize_with_positions("Hello world")
        assert len(result) == 2
        assert result[0] == ("hello", 0)
        assert result[1] == ("world", 1)

    def test_custom_stopwords(self) -> None:
        t = Tokenizer(stopwords={"hello"})
        tokens = t.tokenize("Hello world")
        assert "hello" not in tokens
        assert "world" in tokens


class TestSearchIndex:
    def test_add_and_search(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello", "world"])
        idx.add_document("doc2", ["hello", "python"])
        idx.add_document("doc3", ["goodbye", "world"])

        result = idx.search(["hello", "world"])
        assert result == {"doc1"}

    def test_search_any(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello", "world"])
        idx.add_document("doc2", ["python"])

        result = idx.search_any(["hello", "python"])
        assert result == {"doc1", "doc2"}

    def test_remove_document(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello"])
        idx.remove_document("doc1")
        assert idx.search(["hello"]) == set()

    def test_document_count(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello"])
        idx.add_document("doc2", ["world"])
        assert idx.document_count == 2

    def test_term_count(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello", "world"])
        assert idx.term_count == 2

    def test_get_document(self) -> None:
        idx = SearchIndex()
        idx.add_document("doc1", ["hello"], {"title": "Test"})
        doc = idx.get_document("doc1")
        assert doc == {"title": "Test"}

    def test_search_empty(self) -> None:
        idx = SearchIndex()
        assert idx.search([]) == set()


class TestSearchEngine:
    def setup_method(self) -> None:
        self.engine = SearchEngine()

    def test_index_and_search(self) -> None:
        self.engine.index_document("doc1", "Hello world of Python")
        result = self.engine.search("hello python")
        assert len(result.results) == 1
        assert result.results[0].doc_id == "doc1"

    def test_search_no_match(self) -> None:
        self.engine.index_document("doc1", "Hello world")
        result = self.engine.search("xyzabc")
        assert result.total_matches == 0
        assert result.results == []

    def test_search_match_any(self) -> None:
        self.engine.index_document("doc1", "Hello world")
        self.engine.index_document("doc2", "Python code")
        result = self.engine.search("hello python", match_all=False)
        assert result.total_matches == 2

    def test_search_limit(self) -> None:
        for i in range(10):
            self.engine.index_document(f"doc{i}", f"Hello world test {i}")
        result = self.engine.search("hello", limit=3)
        assert len(result.results) == 3
        assert result.total_matches == 10

    def test_remove_document(self) -> None:
        self.engine.index_document("doc1", "Hello world")
        self.engine.remove_document("doc1")
        result = self.engine.search("hello")
        assert result.total_matches == 0

    def test_index_items(self) -> None:
        items = [
            {"id": "1", "title": "Python tutorial", "content": "Learn Python"},
            {"id": "2", "title": "Web development", "content": "Build websites"},
        ]
        count = self.engine.index_items(items)
        assert count == 2
        result = self.engine.search("python")
        assert result.total_matches == 1

    def test_search_scoring(self) -> None:
        self.engine.index_document("doc1", "Hello world Python")
        self.engine.index_document("doc2", "Hello world")
        result = self.engine.search("hello python")
        assert len(result.results) == 1
        assert result.results[0].score == 1.0

    def test_batch_index(self) -> None:
        items = [
            {"id": str(i), "title": f"Article {i}", "content": "test content"}
            for i in range(100)
        ]
        count = self.engine.index_items(items)
        assert count == 100
        assert self.engine.index.document_count == 100
