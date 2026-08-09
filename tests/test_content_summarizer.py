"""Tests for content_summarizer module."""

from __future__ import annotations

import pytest
from personal_index.content_summarizer import (
    ContentSummarizer,
    SummaryConfig,
    SummaryResult,
    KeyPoint,
)


class TestSummaryConfig:
    """Test SummaryConfig dataclass."""

    def test_default_config(self):
        config = SummaryConfig()
        assert config.max_key_points == 5
        assert config.min_sentence_length == 15
        assert config.method == "frequency"
        assert config.include_phrases is True

    def test_custom_config(self):
        config = SummaryConfig(max_key_points=10, method="hybrid")
        assert config.max_key_points == 10
        assert config.method == "hybrid"

    def test_invalid_method(self):
        with pytest.raises(ValueError):
            SummaryConfig(method="invalid_method")


class TestKeyPoint:
    """Test KeyPoint dataclass."""

    def test_create_key_point(self):
        kp = KeyPoint(text="Important point", score=0.95, category="main")
        assert kp.text == "Important point"
        assert kp.score == 0.95
        assert kp.category == "main"

    def test_key_point_default_category(self):
        kp = KeyPoint(text="A point", score=0.5)
        assert kp.category == "general"

    def test_key_point_ranking(self):
        kp1 = KeyPoint(text="First", score=0.9)
        kp2 = KeyPoint(text="Second", score=0.3)
        assert kp1.score > kp2.score


class TestContentSummarizerEmptyInput:
    """Test summarizer with empty/edge inputs."""

    def test_empty_text(self):
        summarizer = ContentSummarizer()
        result = summarizer.summarize("")
        assert result.key_points == []
        assert result.summary == ""
        assert result.compression_ratio == 0.0

    def test_whitespace_only(self):
        summarizer = ContentSummarizer()
        result = summarizer.summarize("   \n\n   ")
        assert result.key_points == []
        assert result.summary == ""

    def test_very_short_text(self):
        summarizer = ContentSummarizer()
        result = summarizer.summarize("Short text.")
        assert result.original_length == 11
        assert len(result.key_points) <= 1


class TestContentSummarizerFrequencyMethod:
    """Test frequency-based summarization."""

    def test_basic_summarization(self):
        text = (
            "Machine learning is a subset of artificial intelligence. "
            "Deep learning uses neural networks. "
            "Machine learning algorithms learn from data. "
            "Artificial intelligence powers modern technology. "
            "Neural networks are inspired by the brain. "
            "Data science combines statistics and programming. "
            "Machine learning is transforming industries."
        )
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text, method="frequency")
        assert len(result.key_points) > 0
        assert result.method == "frequency"
        assert result.compression_ratio > 0

    def test_frequency_returns_key_sentences(self):
        text = (
            "Python is a programming language. "
            "Python is widely used in data science. "
            "Python supports multiple paradigms. "
            "The Python community is large and active."
        )
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text, method="frequency")
        assert any("Python" in kp.text for kp in result.key_points)

    def test_frequency_max_key_points(self):
        text = " ".join([f"Sentence number {i} is here." for i in range(50)])
        config = SummaryConfig(max_key_points=3)
        summarizer = ContentSummarizer(config=config)
        result = summarizer.summarize(text, method="frequency")
        assert len(result.key_points) <= 3


class TestContentSummarizerHybridMethod:
    """Test hybrid summarization method."""

    def test_hybrid_method(self):
        text = (
            "Climate change is a pressing global issue. "
            "Rising temperatures affect ecosystems worldwide. "
            "Carbon emissions from fossil fuels drive warming. "
            "Renewable energy offers a sustainable solution. "
            "Policy changes are needed to reduce emissions. "
            "International cooperation is essential for progress."
        )
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text, method="hybrid")
        assert len(result.key_points) > 0
        assert result.method == "hybrid"

    def test_hybrid_includes_phrases(self):
        text = (
            "The quick brown fox jumps over the lazy dog. "
            "The fox is very quick and agile. "
            "Dogs are known to be lazy sometimes."
        )
        config = SummaryConfig(include_phrases=True)
        summarizer = ContentSummarizer(config=config)
        result = summarizer.summarize(text, method="hybrid")
        assert len(result.key_phrases) > 0


class TestContentSummarizerExtractKeyPoints:
    """Test key point extraction."""

    def test_extract_key_points_basic(self):
        text = (
            "The article discusses three main topics. "
            "First, the economy is growing steadily. "
            "Second, technology is advancing rapidly. "
            "Third, education systems need reform."
        )
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        assert len(result.key_points) >= 1

    def test_key_points_sorted_by_score(self):
        text = "A repeated important concept. A repeated important concept. Another idea here."
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        scores = [kp.score for kp in result.key_points]
        assert scores == sorted(scores, reverse=True)

    def test_key_points_have_categories(self):
        text = (
            "Introduction to the topic. "
            "The main argument is presented here. "
            "Supporting evidence follows. "
            "Conclusion summarizes the findings."
        )
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        for kp in result.key_points:
            assert kp.category in ("main", "supporting", "conclusion", "general")


class TestContentSummarizerSummaryResult:
    """Test SummaryResult properties."""

    def test_compression_ratio(self):
        text = "A long text that will be summarized into something shorter."
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        assert 0.0 <= result.compression_ratio <= 1.0

    def test_original_length_preserved(self):
        text = "Hello world test."
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        assert result.original_length == len(text)

    def test_summary_length(self):
        text = "First sentence. Second sentence. Third sentence."
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        assert result.summary_length == len(result.summary)


class TestContentSummarizerIntegration:
    """Integration tests for content summarizer."""

    def test_summarize_long_article(self):
        paragraphs = [
            "Artificial intelligence has transformed many industries. "
            "Companies use AI for automation and decision making.",
            "Machine learning models require large datasets for training. "
            "The quality of data directly impacts model performance.",
            "Natural language processing enables computers to understand text. "
            "This technology powers chatbots and translation services.",
            "Computer vision allows machines to interpret visual information. "
            "Applications include medical imaging and autonomous vehicles.",
            "Ethical considerations are important in AI development. "
            "Bias in training data can lead to unfair outcomes.",
        ]
        text = " ".join(paragraphs)
        summarizer = ContentSummarizer()
        result = summarizer.summarize(text)
        assert len(result.key_points) > 0
        assert len(result.summary) < len(text)
        assert result.compression_ratio < 1.0

    def test_batch_summarize(self):
        articles = [
            "First article about topic one. It covers important details.",
            "Second article on topic two. This one has different content.",
            "Third article discussing topic three. Unique perspective here.",
        ]
        summarizer = ContentSummarizer()
        results = summarizer.batch_summarize(articles)
        assert len(results) == 3
        for r in results:
            assert len(r.key_points) >= 0

    def test_summarize_with_custom_config(self):
        config = SummaryConfig(max_key_points=2, min_sentence_length=5)
        summarizer = ContentSummarizer(config=config)
        text = "Short. Medium length sentence. Longer sentence with more words."
        result = summarizer.summarize(text)
        assert len(result.key_points) <= 2
