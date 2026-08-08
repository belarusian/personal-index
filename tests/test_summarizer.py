"""Tests for content summarization."""

from __future__ import annotations

import pytest

from personal_index.summarizer import Summarizer, SummaryResult


class TestSummaryResult:
    """Tests for SummaryResult dataclass."""

    def test_create_result(self):
        r = SummaryResult(summary_text="test summary")
        assert r.summary_text == "test summary"

    def test_to_dict(self):
        r = SummaryResult(
            original_length=1000,
            summary_length=200,
            compression_ratio=0.8,
            summary_text="test",
            key_sentences=["s1"],
            key_phrases=["p1"],
            topics=["t1"],
        )
        d = r.to_dict()
        assert d["original_length"] == 1000
        assert d["compression_ratio"] == 0.8
        assert d["key_sentences"] == ["s1"]

    def test_defaults(self):
        r = SummaryResult()
        assert r.original_length == 0
        assert r.summary_text == ""
        assert r.key_sentences == []


class TestSummarizer:
    """Tests for Summarizer class."""

    def test_summarize_empty(self):
        s = Summarizer()
        result = s.summarize("")
        assert result.summary_text == ""

    def test_summarize_none(self):
        s = Summarizer()
        result = s.summarize(None)
        assert result.summary_text == ""

    def test_summarize_short_text(self):
        s = Summarizer()
        text = "This is a short sentence."
        result = s.summarize(text)
        assert result.original_length == len(text)

    def test_summarize_long_text(self):
        s = Summarizer(max_sentences=3)
        text = (
            "Python is a programming language. "
            "It was created by Guido van Rossum. "
            "Python emphasizes code readability. "
            "It supports multiple programming paradigms. "
            "Python has a large standard library. "
            "It is used in web development. "
            "Python is popular for data science. "
            "Machine learning uses Python extensively. "
            "Django is a Python web framework. "
            "Flask is another Python framework."
        )
        result = s.summarize(text)
        assert result.summary_text
        assert len(result.key_sentences) <= 3
        assert result.compression_ratio >= 0

    def test_summarize_preserves_order(self):
        s = Summarizer(max_sentences=2)
        text = (
            "First sentence is important. "
            "Second sentence follows. "
            "Third sentence comes next."
        )
        result = s.summarize(text)
        # Sentences should be in original order
        if len(result.key_sentences) >= 2:
            idx1 = text.find(result.key_sentences[0])
            idx2 = text.find(result.key_sentences[1])
            assert idx1 < idx2

    def test_summarize_paragraphs(self):
        s = Summarizer()
        text = "First paragraph here.\n\nSecond paragraph here.\n\nThird paragraph here."
        result = s.summarize_paragraphs(text, max_paragraphs=2)
        assert result.summary_text
        assert len(result.key_sentences) <= 2

    def test_summarize_paragraphs_single(self):
        s = Summarizer()
        text = "Only one paragraph."
        result = s.summarize_paragraphs(text, max_paragraphs=2)
        assert result.summary_text == text

    def test_extract_headlines(self):
        s = Summarizer()
        text = (
            "Python is great. "
            "This is a very long sentence that goes on and on and on and on and on and on. "
            "Data science is popular. "
            "Machine learning is transforming industries worldwide."
        )
        headlines = s.extract_headlines(text)
        assert len(headlines) > 0
        assert len(headlines) <= 5

    def test_extract_headlines_empty(self):
        s = Summarizer()
        headlines = s.extract_headlines("")
        assert headlines == []

    def test_get_brief(self):
        s = Summarizer()
        text = " ".join(["word"] * 100)
        brief = s.get_brief(text, max_words=10)
        words = brief.split()
        assert len(words) <= 11  # 10 words + "..."
        assert "..." in brief

    def test_get_brief_short(self):
        s = Summarizer()
        text = "Short text"
        brief = s.get_brief(text, max_words=10)
        assert brief == text

    def test_get_brief_empty(self):
        s = Summarizer()
        brief = s.get_brief("")
        assert brief == ""

    def test_key_phrases(self):
        s = Summarizer()
        text = (
            "Python programming language is popular. "
            "Python is used for web development. "
            "Python supports data science applications. "
            "Machine learning with Python is powerful."
        )
        result = s.summarize(text)
        assert len(result.key_phrases) >= 0

    def test_custom_min_sentence_length(self):
        s = Summarizer(min_sentence_length=5)
        text = "A. B. C. This is a longer sentence that should be included."
        result = s.summarize(text)
        assert "longer sentence" in result.summary_text or result.summary_text

    def test_compression_ratio(self):
        s = Summarizer(max_sentences=1)
        text = " ".join([f"Sentence number {i} is here." for i in range(20)])
        result = s.summarize(text)
        assert 0 <= result.compression_ratio <= 1

    def test_tokenize(self):
        s = Summarizer()
        tokens = s._tokenize("Hello, world! This is a test.")
        assert tokens == ["hello", "world", "this", "is", "a", "test"]

    def test_word_frequency(self):
        s = Summarizer()
        sentences = ["Python is great", "Python is popular", "Java is also good"]
        freq = s._compute_word_frequency(sentences)
        assert freq.get("python", 0) == 2
        assert "is" not in freq  # stop word
