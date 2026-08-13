"""Tests for similarity engine."""

from personal_index.content_linker.similarity import (
    SimilarityEngine,
    _tokenize,
)


class TestTokenize:
    def test_basic(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_empty(self):
        assert _tokenize("") == []



    def test_special_chars(self):
        tokens = _tokenize("Hello, World!")
        assert "hello" in tokens
        assert "world" in tokens
        assert "," not in tokens

    def test_numbers(self):
        assert _tokenize("item 123") == ["item", "123"]


class TestSimilarityEngine:
    def test_identical(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello world", "hello world") == 1.0

    def test_no_overlap(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello", "world") == 0.0

    def test_partial_overlap(self):
        eng = SimilarityEngine()
        score = eng.similarity("hello world foo", "hello world bar")
        assert 0.0 < score < 1.0

    def test_empty_a(self):
        eng = SimilarityEngine()
        assert eng.similarity("", "hello") == 0.0

    def test_empty_b(self):
        eng = SimilarityEngine()
        assert eng.similarity("hello", "") == 0.0

    def test_cache_used(self):
        eng = SimilarityEngine()
        s1 = eng.similarity("aaa bbb", "aaa ccc")
        s2 = eng.similarity("aaa bbb", "aaa ccc")
        assert s1 == s2
        assert len(eng._cache) == 1

    def test_cache_key_order_independent(self):
        eng = SimilarityEngine()
        eng.similarity("zzz", "aaa")
        assert ("aaa", "zzz") in eng._cache

    def test_find_similar(self):
        eng = SimilarityEngine()
        items = [
            ("id1", "hello world"),
            ("id2", "goodbye world"),
            ("id3", "completely different"),
        ]
        results = eng.find_similar("hello world", items, threshold=0.3)
        assert len(results) >= 1
        assert results[0]["id"] == "id1"

    def test_find_similar_threshold(self):
        eng = SimilarityEngine()
        items = [("id1", "hello world"), ("id2", "aaa bbb")]
        results = eng.find_similar("hello world", items, threshold=0.9)
        assert len(results) == 1
        assert results[0]["id"] == "id1"

    def test_find_similar_limit(self):
        eng = SimilarityEngine()
        items = [(f"id{i}", "hello world") for i in range(10)]
        results = eng.find_similar("hello world", items, limit=3)
        assert len(results) == 3

    def test_find_similar_sorted(self):
        eng = SimilarityEngine()
        items = [("id1", "hello world foo"), ("id2", "hello world")]
        results = eng.find_similar("hello world", items)
        assert results[0]["score"] >= results[1]["score"]

    def test_find_similar_empty_items(self):
        eng = SimilarityEngine()
        results = eng.find_similar("hello", [])
        assert results == []

    def test_jaccard_calculation(self):
        eng = SimilarityEngine()
        score = eng.similarity("a b c", "c d e")
        assert score == 1 / 5
