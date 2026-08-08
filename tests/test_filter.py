"""Tests for content filtering."""

import pytest
from personal_index.config import Interest
from personal_index.models import Page
from personal_index.filter import ContentFilter


class TestContentFilter:
    def setup_method(self) -> None:
        self.interests = [
            Interest(
                topic="machine learning",
                keywords=["machine learning", "neural network", "deep learning"],
                priority=8,
            ),
            Interest(
                topic="cooking",
                keywords=["recipe", "cooking", "baking"],
                priority=5,
            ),
        ]
        self.filter = ContentFilter(self.interests, min_relevance_score=0.5)

    def test_page_matches_interest(self):
        page = Page(
            url="https://example.com/ml-article",
            title="Introduction to Machine Learning",
            content="Machine learning is a subset of AI. Neural networks are used in deep learning.",
        )
        result = self.filter.filter_page(page)
        assert result.passed is True
        assert "machine learning" in result.matched_interests

    def test_page_does_not_match(self):
        page = Page(
            url="https://example.com/recipe",
            title="My Garden",
            content="I love growing flowers in my garden.",
        )
        result = self.filter.filter_page(page)
        assert result.passed is False

    def test_page_matches_cooking(self):
        page = Page(
            url="https://example.com/baking",
            title="Baking Bread",
            content="This recipe for baking bread is simple.",
        )
        result = self.filter.filter_page(page)
        assert result.passed is True
        assert "cooking" in result.matched_interests

    def test_url_pattern_matching(self):
        interests = [
            Interest(
                topic="tech news",
                keywords=["technology"],
                url_patterns=["https://techcrunch.com/*"],
            )
        ]
        f = ContentFilter(interests, min_relevance_score=0.0)
        page = Page(
            url="https://techcrunch.com/2024/ai-news",
            title="AI News",
            content="Technology is changing fast.",
        )
        result = f.filter_page(page)
        assert result.passed is True

    def test_disabled_interest_ignored(self):
        interests = [
            Interest(topic="test", keywords=["hello"], enabled=False),
        ]
        f = ContentFilter(interests)
        page = Page(url="https://example.com", content="hello world")
        result = f.filter_page(page)
        assert result.passed is False

    def test_min_relevance_score(self):
        f = ContentFilter(self.interests, min_relevance_score=100.0)
        page = Page(
            url="https://example.com",
            content="machine learning is great",
        )
        result = f.filter_page(page)
        assert result.passed is False

    def test_update_page(self):
        page = Page(url="https://example.com", content="machine learning rocks")
        result = self.filter.filter_page(page)
        self.filter.update_page(page, result)
        assert page.relevance_score == result.relevance_score
        assert page.matched_interests == result.matched_interests

    def test_pre_filter_url(self):
        interests = [
            Interest(
                topic="tech",
                keywords=["tech"],
                url_patterns=["https://example.com/*"],
            )
        ]
        f = ContentFilter(interests)
        assert f.filter_url_pre_crawl("https://example.com/page") is True
        assert f.filter_url_pre_crawl("https://other.com/page") is False

    def test_empty_interests(self):
        f = ContentFilter([])
        page = Page(url="https://example.com", content="anything")
        result = f.filter_page(page)
        # With no interests, all pages pass through
        assert result.passed is True

    def test_wildcard_pattern_matching(self):
        interests = [
            Interest(
                topic="docs",
                keywords=["docs"],
                url_patterns=["https://*.example.com/docs/*"],
            )
        ]
        f = ContentFilter(interests, min_relevance_score=0.0)
        page = Page(
            url="https://api.example.com/docs/v1",
            title="API Docs",
            content="Documentation for the API.",
        )
        result = f.filter_page(page)
        assert result.passed is True
