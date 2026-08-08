"""Tests for content summarization module."""

import pytest
from personal_index.summarizer import TextSummarizer, SummaryResult


class TestTextSummarizer:
    def test_summarize_empty(self):
        s = TextSummarizer()
        result = s.summarize("")
        assert result.summary == ""
        assert result.original_length == 0

    def test_summarize_short_text(self):
        s = TextSummarizer()
        result = s.summarize("Hello world.")
        assert result.summary == "Hello world."

    def test_frequency_method(self):
        text = "Python is great. Python is powerful. Python is versatile. Java is old."
        s = TextSummarizer(max_sentences=2)
        result = s.summarize(text, method="frequency")
        assert len(result.key_sentences) == 2
        assert any("Python" in sent for sent in result.key_sentences)

    def test_first_n_method(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        s = TextSummarizer(max_sentences=2)
        result = s.summarize(text, method="first_n")
        assert "First sentence" in result.summary
        assert "Second sentence" in result.summary

    def test_last_n_method(self):
        text = "First sentence. Second sentence. Third sentence. Fourth sentence."
        s = TextSummarizer(max_sentences=2)
        result = s.summarize(text, method="last_n")
        assert "Third sentence" in result.summary
        assert "Fourth sentence" in result.summary

    def test_middle_method(self):
        text = "First. Second. Third. Fourth. Fifth. Sixth. Seventh. Eighth."
        s = TextSummarizer(max_sentences=2, min_sentence_length=1)
        result = s.summarize(text, method="middle")
        assert len(result.key_sentences) == 2

    def test_unknown_method(self):
        s = TextSummarizer()
        # Use text long enough to pass min_sentence_length filter
        text = "This is a longer text that will be processed properly."
        with pytest.raises(ValueError):
            s.summarize(text, method="unknown")

    def test_compression_ratio(self):
        text = " ".join([f"Sentence number {i} with some words." for i in range(20)])
        s = TextSummarizer(max_sentences=5)
        result = s.summarize(text)
        assert 0 < result.compression_ratio < 1.0

    def test_key_phrases(self):
        text = "Machine learning is great. Machine learning is powerful. Deep learning is fun."
        s = TextSummarizer()
        result = s.summarize(text)
        assert len(result.key_phrases) > 0
        assert any("machine learning" in p for p in result.key_phrases)

    def test_truncate_short(self):
        s = TextSummarizer()
        assert s.truncate("Short", max_length=100) == "Short"

    def test_truncate_long(self):
        s = TextSummarizer()
        result = s.truncate("This is a long text that needs truncation", max_length=20)
        assert len(result) <= 23  # 20 + "..."
        assert result.endswith("...")

    def test_min_sentence_length(self):
        text = "Hi. This is a longer sentence. Go. Another long sentence here."
        s = TextSummarizer(min_sentence_length=10, max_sentences=2)
        result = s.summarize(text, method="first_n")
        assert len(result.key_sentences) == 2
        assert all(len(sent) >= 10 for sent in result.key_sentences)

    def test_summary_result_fields(self):
        s = TextSummarizer()
        result = s.summarize("Hello world. This is a test.")
        assert result.method == "frequency"
        assert result.original_length > 0
        assert isinstance(result.compression_ratio, float)
