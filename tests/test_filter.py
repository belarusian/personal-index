"""Tests for personal_index.filter."""

import pytest
from personal_index.models import CrawledPage, Interest
from personal_index.filter import ContentFilter, FilterResult


@pytest.fixture
def sample_interests():
    return [
        Interest(
            topic="python",
            keywords=["python", "programming", "code"],
            url_patterns=["python.org", "docs.python.org"],
        ),
        Interest(
            topic="ai",
            keywords=["artificial intelligence", "machine learning", "neural network"],
            url_patterns=["ai-news.com"],
        ),
    ]


@pytest.fixture
def disabled_interest():
    return Interest(
        topic="disabled",
        keywords=["should not match"],
        enabled=False,
    )


class TestContentFilter:
    def test_filter_matches_keywords_in_content(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com/python-tutorial",
            title="Python Tutorial",
            content="Learn python programming and write better code",
        )
        result = content_filter.filter_page(page)
        assert result.passed is True
        assert "python" in result.matched_interests

    def test_filter_matches_keywords_in_title(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com/article",
            title="Machine Learning Basics",
            content="Some random content without keywords",
        )
        result = content_filter.filter_page(page)
        assert result.passed is True
        assert "ai" in result.matched_interests

    def test_filter_rejects_unmatched_content(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com/cooking",
            title="How to Cook Pasta",
            content="Boil water and add pasta",
        )
        result = content_filter.filter_page(page)
        assert result.passed is False
        assert result.matched_interests == []

    def test_filter_matches_url_patterns(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://docs.python.org/3/tutorial",
            title="Python Documentation",
            content="Official Python docs",
        )
        result = content_filter.filter_page(page)
        assert result.passed is True
        assert "python" in result.matched_interests

    def test_filter_ignores_disabled_interests(self, disabled_interest):
        content_filter = ContentFilter([disabled_interest])
        page = CrawledPage(
            url="https://example.com",
            title="Should Not Match",
            content="This should not match disabled interest",
        )
        result = content_filter.filter_page(page)
        assert result.passed is False

    def test_filter_case_insensitive(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com",
            title="PYTHON Programming",
            content="Learn PYTHON",
        )
        result = content_filter.filter_page(page)
        assert result.passed is True

    def test_filter_empty_interests(self):
        content_filter = ContentFilter([])
        page = CrawledPage(
            url="https://example.com",
            title="Any Title",
            content="Any content",
        )
        result = content_filter.filter_page(page)
        assert result.passed is False

    def test_filter_sets_matched_interests_on_page(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming guide",
        )
        result = content_filter.filter_page(page)
        assert "python" in page.matched_interests

    def test_filter_result_reason(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming",
        )
        result = content_filter.filter_page(page)
        assert "Matched:" in result.reason
        assert "python" in result.reason

    def test_filter_result_reason_no_match(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        page = CrawledPage(
            url="https://example.com",
            title="Unrelated",
            content="Nothing relevant here",
        )
        result = content_filter.filter_page(page)
        assert "No matching interests" in result.reason


class TestShouldCrawlUrl:
    def test_should_crawl_matching_url(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        should_crawl, interests = content_filter.should_crawl_url(
            "https://docs.python.org/3"
        )
        assert should_crawl is True
        assert "python" in interests

    def test_should_crawl_url_with_keyword(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        should_crawl, interests = content_filter.should_crawl_url(
            "https://example.com/python-tutorial"
        )
        assert should_crawl is True
        assert "python" in interests

    def test_should_not_crawl_unrelated_url(self, sample_interests):
        content_filter = ContentFilter(sample_interests)
        should_crawl, interests = content_filter.should_crawl_url(
            "https://example.com/cooking-recipe"
        )
        assert should_crawl is False
