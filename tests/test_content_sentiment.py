"""Tests for content_sentiment - sentiment analysis for saved content."""

from __future__ import annotations

import pytest
from personal_index.content_sentiment import (
    SentimentScore,
    SentimentResult,
    SentimentAnalyzer,
    SentimentConfig,
    SentimentLabel,
    SentimentIntensity,
    SentimentDocumentResult,
    SentimentSentenceResult,
)


class TestSentimentScore:
    def test_score_valid_range(self):
        score = SentimentScore(positive=0.6, negative=0.2, neutral=0.2)
        assert score.positive == 0.6
        assert score.negative == 0.2
        assert score.neutral == 0.2

    def test_score_compound(self):
        score = SentimentScore(positive=0.7, negative=0.1, neutral=0.2)
        assert score.compound > 0

    def test_score_negative_compound(self):
        score = SentimentScore(positive=0.1, negative=0.7, neutral=0.2)
        assert score.compound < 0

    def test_score_neutral_compound(self):
        score = SentimentScore(positive=0.33, negative=0.33, neutral=0.34)
        assert abs(score.compound) < 0.2

    def test_score_label_positive(self):
        score = SentimentScore(positive=0.7, negative=0.1, neutral=0.2)
        assert score.label == SentimentLabel.POSITIVE

    def test_score_label_negative(self):
        score = SentimentScore(positive=0.1, negative=0.7, neutral=0.2)
        assert score.label == SentimentLabel.NEGATIVE

    def test_score_label_neutral(self):
        score = SentimentScore(positive=0.33, negative=0.33, neutral=0.34)
        assert score.label == SentimentLabel.NEUTRAL

    def test_score_intensity_strong(self):
        score = SentimentScore(positive=0.9, negative=0.05, neutral=0.05)
        assert score.intensity == SentimentIntensity.STRONG

    def test_score_intensity_weak(self):
        score = SentimentScore(positive=0.4, negative=0.35, neutral=0.25)
        assert score.intensity == SentimentIntensity.WEAK


class TestSentimentAnalyzer:
    def test_analyze_positive(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is wonderful and amazing!")
        assert isinstance(result, SentimentResult)
        assert result.score.positive > result.score.negative

    def test_analyze_negative(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("This is terrible and awful.")
        assert isinstance(result, SentimentResult)
        assert result.score.negative > result.score.positive

    def test_analyze_neutral(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("The meeting is at 3pm on Tuesday.")
        assert isinstance(result, SentimentResult)

    def test_analyze_empty(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("")
        assert result.score.positive == 0.0
        assert result.score.negative == 0.0
        assert result.score.neutral == 1.0

    def test_analyze_mixed(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze("Good product but bad service.")
        assert isinstance(result, SentimentResult)

    def test_analyze_batch(self):
        analyzer = SentimentAnalyzer()
        texts = ["Great day!", "Terrible weather.", "It is raining."]
        results = analyzer.analyze_batch(texts)
        assert len(results) == 3
        assert all(isinstance(r, SentimentResult) for r in results)

    def test_analyze_with_config(self):
        config = SentimentConfig(min_length=5)
        analyzer = SentimentAnalyzer(config=config)
        result = analyzer.analyze("good")
        assert isinstance(result, SentimentResult)


class TestSentimentAnalyzerDocument:
    def test_analyze_document(self):
        analyzer = SentimentAnalyzer()
        text = "This product is great. The quality is amazing. However, shipping was slow."
        result = analyzer.analyze_document(text)
        assert isinstance(result, SentimentDocumentResult)
        assert len(result.sentences) > 0

    def test_analyze_document_empty(self):
        analyzer = SentimentAnalyzer()
        result = analyzer.analyze_document("")
        assert isinstance(result, SentimentDocumentResult)
        assert len(result.sentences) == 0

    def test_document_overall_sentiment(self):
        analyzer = SentimentAnalyzer()
        text = "I love this. It is wonderful. Amazing product."
        result = analyzer.analyze_document(text)
        assert result.overall_score.positive > result.overall_score.negative

    def test_document_sentence_results(self):
        analyzer = SentimentAnalyzer()
        text = "Good morning. Bad news today."
        result = analyzer.analyze_document(text)
        assert len(result.sentences) >= 1
        assert all(isinstance(s, SentimentSentenceResult) for s in result.sentences)


class TestSentimentConfig:
    def test_config_defaults(self):
        config = SentimentConfig()
        assert config.min_length == 3

    def test_config_custom(self):
        config = SentimentConfig(min_length=5, boost_intensifiers=True)
        assert config.min_length == 5
        assert config.boost_intensifiers is True
