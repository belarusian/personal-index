"""Tests for content_search_fulltext module - full-text search with ranking."""

from __future__ import annotations

import pytest
from personal_index.content_search_fulltext import (
    SearchIndex,
    SearchResult,
    SearchQuery,
    Tokenizer,
    BM25Ranker,
)


class TestTokenizer:
    """Tests for Tokenizer."""

    def test_tokenize_basic(self):
        tokens = Tokenizer.tokenize("Hello world")
        assert tokens == ["hello", "world"]

    def test_tokenize_with_punctuation(self):
        tokens = Tokenizer.tokenize("Hello, world! How are you?")
        assert "hello" in tokens
        assert "world" in tokens
        assert "how" in tokens

    def test_tokenize_removes_stopwords(self):
        tokens = Tokenizer.tokenize("The quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_tokenize_empty_string(self):
        tokens = Tokenizer.tokenize("")
        assert tokens == []

    def test_tokenize_numbers(self):
        tokens = Tokenizer.tokenize("Version 2.0 release")
        assert "version" in tokens
        assert "release" in tokens

    def test_tokenize_mixed_case(self):
        tokens = Tokenizer.tokenize("Hello WORLD")
        assert "hello" in tokens
        assert "world" in tokens

    def test_tokenize_special_chars(self):
        tokens = Tokenizer.tokenize("test@example.com")
        assert "test" in tokens
        assert "example" in tokens
        assert "com" in tokens


class TestSearchResult:
    """Tests for SearchResult."""

    def test_create_result(self):
        r = SearchResult(content_id="c1", score=0.95, title="Test")
        assert r.content_id == "c1"
        assert r.score == 0.95
        assert r.title == "Test"

    def test_result_to_dict(self):
        r = SearchResult(content_id="c1", score=0.5, title="T", snippet="S")
        d = r.to_dict()
        assert d["content_id"] == "c1"
        assert d["score"] == 0.5
        assert d["title"] == "T"
        assert d["snippet"] == "S"

    def test_result_ranking(self):
        r1 = SearchResult(content_id="c1", score=0.9)
        r2 = SearchResult(content_id="c2", score=0.3)
        assert r1.score > r2.score


class TestSearchQuery:
    """Tests for SearchQuery."""

    def test_create_query(self):
        q = SearchQuery(query="test search")
        assert q.query == "test search"
        assert q.limit == 20
        assert q.offset == 0

    def test_create_query_with_params(self):
        q = SearchQuery(
            query="test",
            limit=10,
            offset=5,
            content_type="article",
            date_from="2024-01-01",
            date_to="2024-12-31",
        )
        assert q.limit == 10
        assert q.offset == 5
        assert q.content_type == "article"

    def test_query_to_dict(self):
        q = SearchQuery(query="test", limit=5)
        d = q.to_dict()
        assert d["query"] == "test"
        assert d["limit"] == 5

    def test_query_from_dict(self):
        data = {"query": "test", "limit": 10, "offset": 20}
        q = SearchQuery.from_dict(data)
        assert q.query == "test"
        assert q.limit == 10
        assert q.offset == 20


class TestBM25Ranker:
    """Tests for BM25Ranker."""

    def test_compute_score_basic(self):
        ranker = BM25Ranker()
        doc_freq = {"hello": 2, "world": 1}
        total_docs = 10
        doc_len = 5
        avg_len = 10
        score = ranker.compute_score(
            tokens=["hello", "world"],
            doc_freq=doc_freq,
            total_docs=total_docs,
            doc_len=doc_len,
            avg_len=avg_len,
        )
        assert score > 0

    def test_compute_score_no_match(self):
        ranker = BM25Ranker()
        doc_freq = {"hello": 2}
        score = ranker.compute_score(
            tokens=["xyz"],
            doc_freq=doc_freq,
            total_docs=10,
            doc_len=5,
            avg_len=10,
        )
        assert score == 0

    def test_compute_score_empty_tokens(self):
        ranker = BM25Ranker()
        score = ranker.compute_score(
            tokens=[],
            doc_freq={"hello": 2},
            total_docs=10,
            doc_len=5,
            avg_len=10,
        )
        assert score == 0

    def test_compute_score_high_frequency(self):
        ranker = BM25Ranker()
        doc_freq = {"hello": 10, "world": 5}
        score = ranker.compute_score(
            tokens=["hello", "world"],
            doc_freq=doc_freq,
            total_docs=100,
            doc_len=20,
            avg_len=15,
        )
        assert score > 0


class TestSearchIndex:
    """Tests for SearchIndex."""

    def setup_method(self):
        self.index = SearchIndex()

    def test_add_document(self):
        self.index.add_document("c1", "Hello world", title="Test Doc")
        assert self.index.doc_count() == 1

    def test_add_multiple_documents(self):
        self.index.add_document("c1", "Hello world", title="Doc 1")
        self.index.add_document("c2", "Python programming", title="Doc 2")
        self.index.add_document("c3", "Machine learning", title="Doc 3")
        assert self.index.doc_count() == 3

    def test_search_basic(self):
        self.index.add_document("c1", "Hello world", title="Test")
        self.index.add_document("c2", "Goodbye world", title="Test 2")
        results = self.index.search("world")
        assert len(results) == 2

    def test_search_no_results(self):
        self.index.add_document("c1", "Hello world", title="Test")
        results = self.index.search("xyz")
        assert len(results) == 0

    def test_search_ranking(self):
        self.index.add_document("c1", "Python Python Python", title="Python Doc")
        self.index.add_document("c2", "Python", title="Other Doc")
        results = self.index.search("python")
        assert len(results) == 2
        assert results[0].score >= results[1].score

    def test_search_with_limit(self):
        for i in range(10):
            self.index.add_document(f"c{i}", f"Document number {i}", title=f"Doc {i}")
        results = self.index.search("document", limit=3)
        assert len(results) <= 3

    def test_search_with_offset(self):
        for i in range(10):
            self.index.add_document(f"c{i}", f"Document number {i}", title=f"Doc {i}")
        all_results = self.index.search("document", limit=100)
        assert len(all_results) == 10

    def test_search_by_title(self):
        self.index.add_document("c1", "Some content", title="Python Guide")
        self.index.add_document("c2", "Other content", title="Ruby Guide")
        results = self.index.search("python")
        assert len(results) == 1
        assert results[0].title == "Python Guide"

    def test_remove_document(self):
        self.index.add_document("c1", "Hello world", title="Test")
        self.index.remove_document("c1")
        assert self.index.doc_count() == 0

    def test_remove_nonexistent_document(self):
        self.index.remove_document("nonexistent")
        assert self.index.doc_count() == 0

    def test_search_result_has_snippet(self):
        self.index.add_document("c1", "This is a test document with content", title="Test")
        results = self.index.search("test")
        assert len(results) == 1
        assert results[0].snippet is not None

    def test_search_multiple_terms(self):
        self.index.add_document("c1", "Python and JavaScript", title="Languages")
        self.index.add_document("c2", "Python programming", title="Python")
        self.index.add_document("c3", "JavaScript framework", title="JS")
        results = self.index.search("python javascript")
        assert len(results) >= 1

    def test_search_case_insensitive(self):
        self.index.add_document("c1", "Hello World", title="Test")
        results = self.index.search("hello")
        assert len(results) == 1

    def test_search_empty_index(self):
        results = self.index.search("test")
        assert len(results) == 0

    def test_get_document(self):
        self.index.add_document("c1", "Hello world", title="Test")
        doc = self.index.get_document("c1")
        assert doc is not None
        assert doc["content_id"] == "c1"

    def test_get_nonexistent_document(self):
        doc = self.index.get_document("nonexistent")
        assert doc is None

    def test_get_all_document_ids(self):
        self.index.add_document("c1", "A", title="A")
        self.index.add_document("c2", "B", title="B")
        ids = self.index.get_all_ids()
        assert "c1" in ids
        assert "c2" in ids

    def test_clear_index(self):
        self.index.add_document("c1", "A", title="A")
        self.index.add_document("c2", "B", title="B")
        self.index.clear()
        assert self.index.doc_count() == 0

    def test_search_with_content_type_filter(self):
        self.index.add_document("c1", "Python article", title="Article", content_type="article")
        self.index.add_document("c2", "Python video", title="Video", content_type="video")
        results = self.index.search("python", content_type="article")
        assert len(results) == 1
        assert results[0].content_type == "article"

    def test_search_with_date_filter(self):
        self.index.add_document("c1", "Old content", title="Old", date="2023-01-01")
        self.index.add_document("c2", "New content", title="New", date="2024-06-01")
        results = self.index.search("content", date_from="2024-01-01")
        assert len(results) == 1
        assert results[0].title == "New"

    def test_search_with_query_object(self):
        self.index.add_document("c1", "Test search query", title="Test")
        q = SearchQuery(query="test", limit=5)
        results = self.index.search_query(q)
        assert len(results) == 1

    def test_search_total_count(self):
        for i in range(5):
            self.index.add_document(f"c{i}", f"Search test {i}", title=f"Doc {i}")
        results = self.index.search("search")
        assert results.total_count == 5

    def test_search_has_next(self):
        for i in range(10):
            self.index.add_document(f"c{i}", f"Search test {i}", title=f"Doc {i}")
        results = self.index.search("search", limit=5)
        assert results.has_next is True

    def test_search_no_next(self):
        for i in range(3):
            self.index.add_document(f"c{i}", f"Search test {i}", title=f"Doc {i}")
        results = self.index.search("search", limit=10)
        assert results.has_next is False

    def test_search_result_to_dict(self):
        self.index.add_document("c1", "Test content", title="Test")
        results = self.index.search("test")
        d = results.to_dict()
        assert "results" in d
        assert "total_count" in d

    def test_index_stats(self):
        self.index.add_document("c1", "Hello world", title="Test")
        self.index.add_document("c2", "Python programming", title="Python")
        stats = self.index.get_stats()
        assert stats["total_documents"] == 2
        assert stats["total_terms"] > 0

    def test_serialize_deserialize(self):
        self.index.add_document("c1", "Hello world", title="Test")
        self.index.add_document("c2", "Python code", title="Python")
        data = self.index.serialize()
        new_index = SearchIndex()
        new_index.deserialize(data)
        assert new_index.doc_count() == 2
        results = new_index.search("python")
        assert len(results) == 1

    def test_update_document(self):
        self.index.add_document("c1", "Original content", title="Original")
        self.index.update_document("c1", "Updated content", title="Updated")
        doc = self.index.get_document("c1")
        assert doc["title"] == "Updated"
        assert doc["content"] == "Updated content"

    def test_update_nonexistent_document(self):
        result = self.index.update_document("nonexistent", "content", title="T")
        assert result is False

    def test_search_with_boost_fields(self):
        self.index.add_document("c1", "python in content", title="Python Title")
        self.index.add_document("c2", "python in content", title="Other Title")
        results = self.index.search("python", boost_title=2.0)
        assert len(results) == 2
        # Title match should rank higher
        assert results[0].title == "Python Title"

    def test_search_stopwords_ignored(self):
        self.index.add_document("c1", "The quick brown fox", title="Fox")
        results = self.index.search("the")
        assert len(results) == 0

    def test_search_special_characters(self):
        self.index.add_document("c1", "test@example.com", title="Email")
        results = self.index.search("test")
        assert len(results) == 1

    def test_add_document_with_metadata(self):
        self.index.add_document(
            "c1", "Content", title="Test",
            content_type="article",
            url="http://example.com",
            metadata={"author": "alice"},
        )
        doc = self.index.get_document("c1")
        assert doc["content_type"] == "article"
        assert doc["url"] == "http://example.com"

    def test_search_with_url_filter(self):
        self.index.add_document("c1", "Content", title="A", url="http://example.com/a")
        self.index.add_document("c2", "Content", title="B", url="http://example.com/b")
        results = self.index.search("content", url_pattern="example.com/a")
        assert len(results) == 1
