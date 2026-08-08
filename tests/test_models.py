"""Tests for personal_index.models."""

import re
from datetime import datetime

import pytest

from personal_index.models import (
    CrawledPage,
    Interest,
    InterestType,
)


class TestInterest:
    """Tests for the Interest model."""

    def test_create_keyword_interest(self):
        interest = Interest(
            name="Python news",
            interest_type=InterestType.KEYWORD,
            value="python",
            priority=7,
        )
        assert interest.name == "Python news"
        assert interest.interest_type == InterestType.KEYWORD
        assert interest.value == "python"
        assert interest.priority == 7
        assert interest.enabled is True

    def test_create_topic_interest(self):
        interest = Interest(
            name="Machine learning",
            interest_type=InterestType.TOPIC,
            value="machine learning AI",
            priority=8,
        )
        assert interest.interest_type == InterestType.TOPIC
        assert interest.value == "machine learning AI"

    def test_create_url_pattern_interest(self):
        interest = Interest(
            name="GitHub repos",
            interest_type=InterestType.URL_PATTERN,
            value=r"github\.com/[\w-]+/[\w-]+",
            priority=6,
        )
        assert interest.interest_type == InterestType.URL_PATTERN

    def test_keyword_match(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="python",
        )
        assert interest.matches("I love Python programming") is True
        assert interest.matches("Java is great") is False

    def test_keyword_match_case_insensitive(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="Python",
        )
        assert interest.matches("PYTHON is awesome") is True
        assert interest.matches("python rocks") is True

    def test_topic_match(self):
        interest = Interest(
            name="ML",
            interest_type=InterestType.TOPIC,
            value="machine learning neural networks",
        )
        assert interest.matches("Deep learning with neural networks") is True
        assert interest.matches("machine learning basics") is True
        assert interest.matches("cooking recipes") is False

    def test_topic_match_any_term(self):
        interest = Interest(
            name="tech",
            interest_type=InterestType.TOPIC,
            value="docker kubernetes helm",
        )
        assert interest.matches("Deploying with Docker") is True
        assert interest.matches("Kubernetes cluster setup") is True
        assert interest.matches("Helm charts explained") is True

    def test_url_pattern_match(self):
        interest = Interest(
            name="GitHub",
            interest_type=InterestType.URL_PATTERN,
            value=r"github\.com",
        )
        assert interest.matches("", "https://github.com/user/repo") is True
        assert interest.matches("", "https://gitlab.com/user/repo") is False

    def test_disabled_interest_no_match(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="python",
            enabled=False,
        )
        assert interest.matches("python is great") is False

    def test_keyword_score(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="python",
            priority=5,
        )
        score = interest.score("python python python")
        assert score == 15.0  # 3 occurrences * priority 5

    def test_topic_score(self):
        interest = Interest(
            name="ML",
            interest_type=InterestType.TOPIC,
            value="machine learning AI",
            priority=6,
        )
        score = interest.score("machine learning and AI together")
        assert score == pytest.approx(6.0)  # all 3 terms match

    def test_topic_partial_score(self):
        interest = Interest(
            name="ML",
            interest_type=InterestType.TOPIC,
            value="machine learning AI",
            priority=6,
        )
        score = interest.score("machine learning basics")
        assert score == pytest.approx(4.0)  # 2/3 terms match

    def test_score_disabled_returns_zero(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="python",
            enabled=False,
        )
        assert interest.score("python") == 0.0

    def test_created_at_default(self):
        interest = Interest(
            name="test",
            interest_type=InterestType.KEYWORD,
            value="test",
        )
        assert isinstance(interest.created_at, datetime)


class TestCrawledPage:
    """Tests for the CrawledPage model."""

    def test_create_crawled_page(self):
        page = CrawledPage(
            url="https://example.com",
            title="Example",
            content="Hello world",
        )
        assert page.url == "https://example.com"
        assert page.title == "Example"
        assert page.content == "Hello world"
        assert page.status_code == 0
        assert page.depth == 0
        assert page.parent_url is None

    def test_crawled_page_defaults(self):
        page = CrawledPage(url="https://example.com")
        assert page.title == ""
        assert page.content == ""
        assert page.meta_description == ""
        assert page.headers == {}
        assert page.matched_interests == []
        assert page.relevance_score == 0.0
        assert isinstance(page.crawled_at, datetime)

    def test_crawled_page_with_parent(self):
        page = CrawledPage(
            url="https://example.com/page2",
            parent_url="https://example.com",
            depth=1,
        )
        assert page.parent_url == "https://example.com"
        assert page.depth == 1
