"""Tests for keyword extraction module."""

from __future__ import annotations

import pytest

from personal_index.keyword_extractor import KeywordExtractor, Keyword


class TestKeywordExtractor:
    """Tests for KeywordExtractor class."""

    def setup_method(self):
        self.extractor = KeywordExtractor()

    def test_extract_returns_keywords(self):
        text = "python is great python programming"
        keywords = self.extractor.extract(text)
        assert len(keywords) > 0
        assert all(isinstance(kw, Keyword) for kw in keywords)

    def test_extract_empty_text(self):
        keywords = self.extractor.extract("")
        assert keywords == []

    def test_extract_none_text(self):
        keywords = self.extractor.extract(None)
        assert keywords == []

    def test_extract_filters_stopwords(self):
        text = "the quick brown fox jumps over the lazy dog"
        keywords = self.extractor.extract(text)
        keyword_texts = [kw.text for kw in keywords]
        assert "the" not in keyword_texts
        assert "over" not in keyword_texts

    def test_extract_min_length(self):
        extractor = KeywordExtractor(min_length=5)
        text = "hi hello world testing"
        keywords = extractor.extract(text)
        keyword_texts = [kw.text for kw in keywords]
        assert "hi" not in keyword_texts
        assert "hello" in keyword_texts

    def test_extract_max_keywords(self):
        extractor = KeywordExtractor(max_keywords=3)
        text = "one two three four five six seven eight nine ten"
        keywords = extractor.extract(text)
        assert len(keywords) <= 3

    def test_extract_frequency(self):
        text = "python python python java java"
        keywords = self.extractor.extract(text)
        kw_dict = {kw.text: kw.frequency for kw in keywords}
        assert kw_dict.get("python", 0) == 3
        assert kw_dict.get("java", 0) == 2

    def test_extract_score_ordering(self):
        text = "python python python java java"
        keywords = self.extractor.extract(text)
        if len(keywords) >= 2:
            assert keywords[0].score >= keywords[1].score

    def test_extract_positions(self):
        text = "hello world hello"
        keywords = self.extractor.extract(text)
        hello_kw = next((kw for kw in keywords if kw.text == "hello"), None)
        if hello_kw:
            assert len(hello_kw.positions) == 2

    def test_extract_phrases(self):
        text = "machine learning is a subset of artificial intelligence"
        phrases = self.extractor.extract_phrases(text, n=2)
        assert len(phrases) > 0
        assert all(isinstance(p, tuple) and len(p) == 2 for p in phrases)

    def test_extract_phrases_empty(self):
        assert self.extractor.extract_phrases("") == []

    def test_extract_phrases_none(self):
        assert self.extractor.extract_phrases(None) == []

    def test_extract_phrases_short_text(self):
        phrases = self.extractor.extract_phrases("hello", n=2)
        assert phrases == []

    def test_extract_top_n(self):
        text = "python python java java javascript"
        top = self.extractor.extract_top_n(text, n=2)
        assert len(top) <= 2
        assert isinstance(top, list)

    def test_compute_term_frequency(self):
        text = "hello hello world"
        tf = self.extractor.compute_term_frequency(text)
        assert "hello" in tf
        assert "world" in tf
        assert tf["hello"] > tf["world"]

    def test_compute_term_frequency_empty(self):
        assert self.extractor.compute_term_frequency("") == {}

    def test_compute_term_frequency_total(self):
        text = "hello hello world"
        tf = self.extractor.compute_term_frequency(text)
        total = sum(tf.values())
        assert abs(total - 1.0) < 0.01

    def test_compare_keywords(self):
        text1 = "python programming language"
        text2 = "python scripting language"
        shared = self.extractor.compare_keywords(text1, text2)
        assert "python" in shared
        assert "language" in shared

    def test_compare_keywords_no_overlap(self):
        text1 = "python programming"
        text2 = "cooking recipes"
        shared = self.extractor.compare_keywords(text1, text2)
        assert shared == {}

    def test_min_frequency_filter(self):
        extractor = KeywordExtractor(min_frequency=2)
        text = "python python java javascript"
        keywords = extractor.extract(text)
        keyword_texts = [kw.text for kw in keywords]
        assert "python" in keyword_texts
        assert "java" not in keyword_texts
        assert "javascript" not in keyword_texts
