"""Tests for content similarity detection."""

import pytest
from personal_index.similarity import SimilarityEngine, SimilarityResult


class TestSimilarityResult:
    def test_creation(self):
        result = SimilarityResult(score=0.5, method="jaccard")
        assert result.score == 0.5
        assert result.method == "jaccard"
        assert result.details == {}


class TestSimilarityEngine:
    def test_identical_texts(self):
        engine = SimilarityEngine()
        result = engine.compare("hello world", "hello world")
        assert result.score == 1.0

    def test_completely_different(self):
        engine = SimilarityEngine()
        result = engine.compare("abc def ghi", "xyz uvw rst")
        assert result.score == 0.0

    def test_partial_overlap(self):
        engine = SimilarityEngine()
        result = engine.compare("hello world foo", "hello world bar")
        assert 0.0 < result.score < 1.0

    def test_is_similar_true(self):
        engine = SimilarityEngine(threshold=0.5)
        assert engine.is_similar("hello world foo", "hello world bar") is True

    def test_is_similar_false(self):
        engine = SimilarityEngine(threshold=0.9)
        assert engine.is_similar("hello world foo", "hello world bar") is False

    def test_empty_texts(self):
        engine = SimilarityEngine()
        result = engine.compare("", "")
        assert result.score == 1.0

    def test_jaccard_method(self):
        engine = SimilarityEngine()
        result = engine.compare("a b c", "a b d", method="jaccard")
        assert result.method == "jaccard"
        assert result.score == pytest.approx(2/3, rel=0.01)

    def test_cosine_method(self):
        engine = SimilarityEngine()
        result = engine.compare("a b c", "a b d", method="cosine")
        assert result.method == "cosine"
        assert 0.0 < result.score < 1.0

    def test_overlap_method(self):
        engine = SimilarityEngine()
        result = engine.compare("a b c", "a b", method="overlap")
        assert result.method == "overlap"
        assert result.score == 1.0

    def test_levenshtein_method(self):
        engine = SimilarityEngine()
        result = engine.compare("kitten", "sitting", method="levenshtein")
        assert result.method == "levenshtein"
        assert 0.0 < result.score < 1.0

    def test_find_duplicates(self):
        engine = SimilarityEngine(threshold=0.5)
        texts = ["hello world", "hello there", "completely different"]
        duplicates = engine.find_duplicates(texts)
        assert len(duplicates) >= 1

    def test_find_no_duplicates(self):
        engine = SimilarityEngine(threshold=0.9)
        texts = ["abc", "xyz", "123"]
        duplicates = engine.find_duplicates(texts)
        assert len(duplicates) == 0

    def test_unknown_method(self):
        engine = SimilarityEngine()
        with pytest.raises(ValueError):
            engine.compare("a", "b", method="unknown")

    def test_auto_method_short_texts(self):
        engine = SimilarityEngine()
        result = engine.compare("cat", "car")
        assert result.method == "levenshtein"

    def test_auto_method_long_texts(self):
        engine = SimilarityEngine()
        long1 = "word " * 50
        long2 = "word " * 49 + "other"
        result = engine.compare(long1, long2)
        assert result.method == "cosine"

    def test_jaccard_details(self):
        engine = SimilarityEngine()
        result = engine.compare("a b c", "a b d", method="jaccard")
        assert "intersection" in result.details
        assert "union" in result.details
