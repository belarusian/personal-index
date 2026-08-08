"""Tests for personal_index.models."""

import pytest
from datetime import datetime
from personal_index.models import (
    Interest,
    CrawledPage,
    SearchResult,
    CrawlConfig,
    InterestType,
)


class TestInterestType:
    def test_interest_type_values(self):
        assert InterestType.TOPIC.value == "topic"
        assert InterestType.KEYWORD.value == "keyword"
        assert InterestType.URL_PATTERN.value == "url_pattern"


class TestInterest:
    def test_create_interest(self):
        interest = Interest(topic="machine learning")
        assert interest.topic == "machine learning"
        assert interest.keywords == []
        assert interest.url_patterns == []
        assert interest.enabled is True
        assert isinstance(interest.created_at, datetime)

    def test_interest_id_is_deterministic(self):
        i1 = Interest(topic="test")
        i2 = Interest(topic="test")
        assert i1.id == i2.id
        assert len(i1.id) == 16

    def test_interest_id_is_unique_per_topic(self):
        i1 = Interest(topic="topic1")
        i2 = Interest(topic="topic2")
        assert i1.id != i2.id

    def test_matches_text_case_insensitive(self):
        interest = Interest(topic="test", keywords=["Python", "AI"])
        assert interest.matches_text("I love python programming")
        assert interest.matches_text("AI is the future")
        assert not interest.matches_text("Hello world")

    def test_matches_url_case_insensitive(self):
        interest = Interest(topic="test", url_patterns=["example.com"])
        assert interest.matches_url("https://EXAMPLE.COM/page")
        assert not interest.matches_url("https://other.com/page")

    def test_matches_text_empty_keywords(self):
        interest = Interest(topic="test", keywords=[])
        assert not interest.matches_text("anything")


class TestCrawledPage:
    def test_create_page(self):
        page = CrawledPage(url="https://example.com")
        assert page.url == "https://example.com"
        assert page.title == ""
        assert page.content == ""
        assert page.status_code == 0
        assert page.depth == 0

    def test_page_id_is_deterministic(self):
        p1 = CrawledPage(url="https://example.com")
        p2 = CrawledPage(url="https://example.com")
        assert p1.id == p2.id

    def test_page_id_is_unique_per_url(self):
        p1 = CrawledPage(url="https://example.com/1")
        p2 = CrawledPage(url="https://example.com/2")
        assert p1.id != p2.id

    def test_searchable_text(self):
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            meta_description="A test page",
            content="Some content here",
        )
        searchable = page.searchable_text
        assert "Test Page" in searchable
        assert "A test page" in searchable
        assert "Some content here" in searchable

    def test_searchable_text_empty_fields(self):
        page = CrawledPage(url="https://example.com")
        assert page.searchable_text == ""


class TestSearchResult:
    def test_create_result(self):
        page = CrawledPage(url="https://example.com")
        result = SearchResult(page=page, score=0.95)
        assert result.page == page
        assert result.score == 0.95
        assert result.highlights == []


class TestCrawlConfig:
    def test_default_config(self):
        config = CrawlConfig()
        assert config.max_depth == 2
        assert config.max_pages == 100
        assert config.rate_limit == 1.0
        assert config.politeness_delay == 0.5
        assert config.timeout == 10
        assert config.respect_robots is True

    def test_custom_config(self):
        config = CrawlConfig(
            max_depth=5,
            max_pages=500,
            rate_limit=2.0,
            user_agent="custom-agent",
        )
        assert config.max_depth == 5
        assert config.max_pages == 500
        assert config.rate_limit == 2.0
        assert config.user_agent == "custom-agent"
