"""Tests for personal_index.content_filter."""

import pytest

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, InterestType


@pytest.fixture
def filter_no_store():
    return ContentFilter()


@pytest.fixture
def filter_with_store(tmp_path):
    store = InterestStore(store_path=str(tmp_path / "interests.json"))
    store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
    store.add(Interest("ML", InterestType.TOPIC, "machine learning", 8))
    return ContentFilter(interest_store=store)


class TestFilterConfig:
    """Tests for FilterConfig."""

    def test_defaults(self):
        config = FilterConfig()
        assert config.min_content_length == 100
        assert config.max_content_length == 100000
        assert config.min_title_length == 3
        assert config.require_interest_match is True
        assert config.blocked_domains == []
        assert config.min_relevance_score == 0.0


class TestContentFilter:
    """Tests for ContentFilter."""

    def test_no_store_always_include(self, filter_no_store):
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="x" * 200,
        )
        assert filter_no_store.should_include(page) is True

    def test_content_too_short(self, filter_no_store):
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="short",
        )
        assert filter_no_store.should_include(page) is False

    def test_content_too_long(self, filter_no_store):
        config = FilterConfig(max_content_length=50)
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="x" * 100,
        )
        assert f.should_include(page) is False

    def test_title_too_short(self, filter_no_store):
        page = CrawledPage(
            url="https://example.com",
            title="AB",
            content="x" * 200,
        )
        assert filter_no_store.should_include(page) is False

    def test_blocked_domain(self, filter_no_store):
        config = FilterConfig(blocked_domains=["spam.com"])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://spam.com/page",
            title="Test",
            content="x" * 200,
        )
        assert f.should_include(page) is False

    def test_blocked_domain_subdomain(self, filter_no_store):
        config = FilterConfig(blocked_domains=["spam.com"])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://sub.spam.com/page",
            title="Test",
            content="x" * 200,
        )
        assert f.should_include(page) is False

    def test_blocked_pattern(self, filter_no_store):
        config = FilterConfig(blocked_patterns=[r"advertis"])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="This page has an advertisement in it. " + "x" * 80,
        )
        assert f.should_include(page) is False

    def test_required_pattern(self, filter_no_store):
        config = FilterConfig(required_patterns=[r"python"])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="This is about python programming. " + "x" * 80,
        )
        assert f.should_include(page) is True

    def test_required_pattern_no_match(self, filter_no_store):
        config = FilterConfig(required_patterns=[r"python"])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="This is about java programming. " + "x" * 80,
        )
        assert f.should_include(page) is False

    def test_interest_match(self, filter_with_store):
        page = CrawledPage(
            url="https://example.com",
            title="Python Guide",
            content="Python is a great language for programming. " + "x" * 80,
        )
        assert filter_with_store.should_include(page) is True
        assert "Py" in page.matched_interests

    def test_interest_no_match(self, filter_with_store):
        page = CrawledPage(
            url="https://example.com",
            title="Cooking",
            content="How to cook pasta. " + "x" * 90,
        )
        assert filter_with_store.should_include(page) is False

    def test_min_relevance_score(self, filter_with_store):
        config = FilterConfig(min_relevance_score=10.0)
        f = ContentFilter(config=config, interest_store=filter_with_store.interest_store)
        page = CrawledPage(
            url="https://example.com",
            title="Python",
            content="python " + "x" * 90,
        )
        # Score will be 5.0 (1 occurrence * priority 5)
        assert f.should_include(page) is False

    def test_filter_pages(self, filter_no_store):
        pages = [
            CrawledPage(url="https://a.com", title="Good", content="x" * 200),
            CrawledPage(url="https://b.com", title="Bad", content="short"),
        ]
        filtered = filter_no_store.filter_pages(pages)
        assert len(filtered) == 1
        assert filtered[0].url == "https://a.com"

    def test_get_filter_reasons(self, filter_no_store):
        page = CrawledPage(
            url="https://example.com",
            title="AB",
            content="short",
        )
        reasons = filter_no_store.get_filter_reasons(page)
        assert "content length" in reasons[0]
        assert "title too short" in reasons[1]

    def test_invalid_regex_ignored(self):
        config = FilterConfig(blocked_patterns=["[invalid("])
        f = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="x" * 200,
        )
        assert f.should_include(page) is True
