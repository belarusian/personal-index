"""Tests for content filter module."""

import pytest
from personal_index.config import Interest
from personal_index.content import ExtractedContent
from personal_index.filter import ContentFilter, FilterResult


@pytest.fixture
def sample_content():
    return ExtractedContent(
        url="http://example.com/ai-news",
        title="Latest AI Breakthrough",
        text="Researchers have made a breakthrough in artificial intelligence and machine learning.",
        meta_description="AI and ML news",
        headings=["h1: AI News"],
    )


class TestFilterResult:
    def test_creation(self):
        result = FilterResult(url="http://example.com", passed=True)
        assert result.url == "http://example.com"
        assert result.passed is True
        assert result.relevance_score == 0.0

    def test_with_matches(self):
        result = FilterResult(
            url="http://example.com",
            passed=True,
            matched_interests=["AI"],
            matched_keywords=["neural"],
            relevance_score=15.0,
        )
        assert result.matched_interests == ["AI"]
        assert result.matched_keywords == ["neural"]
        assert result.relevance_score == 15.0


class TestContentFilter:
    def test_creation_empty(self):
        f = ContentFilter()
        assert len(f.interests) == 0

    def test_creation_with_interests(self):
        interests = [Interest(topic="AI", keywords=["neural", "deep learning"])]
        f = ContentFilter(interests=interests)
        assert len(f.interests) == 1

    def test_add_interest(self):
        f = ContentFilter()
        f.add_interest(Interest(topic="AI", keywords=["neural"]))
        assert len(f.interests) == 1

    def test_remove_interest(self):
        f = ContentFilter()
        f.add_interest(Interest(topic="AI", keywords=["neural"]))
        removed = f.remove_interest("AI")
        assert removed is True
        assert len(f.interests) == 0

    def test_remove_nonexistent_interest(self):
        f = ContentFilter()
        removed = f.remove_interest("nonexistent")
        assert removed is False

    def test_filter_match(self, sample_content):
        interests = [Interest(topic="AI", keywords=["artificial intelligence", "machine learning"])]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert result.passed is True
        assert "AI" in result.matched_interests

    def test_filter_no_match(self, sample_content):
        interests = [Interest(topic="Cooking", keywords=["recipes", "cooking"])]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert result.passed is False

    def test_filter_disabled_interest(self, sample_content):
        interests = [Interest(topic="AI", keywords=["neural"], enabled=False)]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert result.passed is False

    def test_filter_url_pattern(self):
        content = ExtractedContent(
            url="http://techblog.example.com/ai-post",
            title="AI Post",
            text="Some content about AI",
        )
        interests = [Interest(topic="Tech", url_patterns=["http://techblog.example.com/*"])]
        f = ContentFilter(interests=interests)
        result = f.filter_content(content)
        assert result.passed is True
        assert "Tech" in result.matched_interests

    def test_filter_relevance_score(self, sample_content):
        interests = [
            Interest(topic="AI", keywords=["artificial intelligence"], priority=8),
            Interest(topic="ML", keywords=["machine learning"], priority=5),
        ]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert result.relevance_score > 0

    def test_filter_batch(self, sample_content):
        interests = [Interest(topic="AI", keywords=["neural"])]
        f = ContentFilter(interests=interests)
        contents = [sample_content]
        results = f.filter_batch(contents)
        assert len(results) == 1

    def test_filter_multiple_matches(self):
        content = ExtractedContent(
            url="http://example.com",
            title="AI and ML",
            text="Artificial intelligence and machine learning are transforming technology.",
        )
        interests = [
            Interest(topic="AI", keywords=["artificial intelligence"]),
            Interest(topic="ML", keywords=["machine learning"]),
        ]
        f = ContentFilter(interests=interests)
        result = f.filter_content(content)
        assert result.passed is True
        assert len(result.matched_interests) == 2

    def test_get_matching_interests(self):
        interests = [
            Interest(topic="AI", keywords=["neural"]),
            Interest(topic="Cooking", keywords=["recipes"]),
        ]
        f = ContentFilter(interests=interests)
        matching = f.get_matching_interests("neural networks are cool")
        assert len(matching) == 1
        assert matching[0].topic == "AI"

    def test_filter_reasons(self, sample_content):
        interests = [Interest(topic="AI", keywords=["machine learning"])]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert len(result.reasons) > 0

    def test_filter_reasons_no_match(self, sample_content):
        interests = [Interest(topic="Cooking", keywords=["recipes"])]
        f = ContentFilter(interests=interests)
        result = f.filter_content(sample_content)
        assert "No matching interests found" in result.reasons

    def test_get_stats(self):
        interests = [
            Interest(topic="AI", keywords=["neural", "deep learning"]),
            Interest(topic="ML", keywords=["machine learning"], enabled=False),
        ]
        f = ContentFilter(interests=interests)
        stats = f.get_stats()
        assert stats["total_interests"] == 2
        assert stats["enabled_interests"] == 1
        assert stats["indexed_keywords"] > 0

    def test_keyword_index_case_insensitive(self):
        interests = [Interest(topic="AI", keywords=["Neural Networks"])]
        f = ContentFilter(interests=interests)
        content = ExtractedContent(
            url="http://example.com",
            title="Test",
            text="neural networks are great",
        )
        result = f.filter_content(content)
        assert result.passed is True
