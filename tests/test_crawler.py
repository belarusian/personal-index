"""Tests for personal_index.crawler."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime
from urllib.parse import urlparse

from personal_index.models import CrawledPage, CrawlConfig, Interest
from personal_index.crawler import (
    RateLimiter,
    LinkExtractor,
    PageParser,
    WebCrawler,
    CrawlStats,
)
from personal_index.filter import ContentFilter


class TestCrawlStats:
    def test_default_stats(self):
        stats = CrawlStats()
        assert stats.pages_crawled == 0
        assert stats.pages_filtered == 0
        assert stats.pages_stored == 0
        assert stats.errors == 0
        assert stats.duration is None

    def test_duration_calculation(self):
        start = datetime(2024, 1, 1, 12, 0, 0)
        end = datetime(2024, 1, 1, 12, 0, 30)
        stats = CrawlStats(start_time=start, end_time=end)
        assert stats.duration == 30.0


class TestRateLimiter:
    def test_rate_limiter_init(self):
        limiter = RateLimiter(rate_limit=1.0, politeness_delay=0.5)
        assert limiter.rate_limit == 1.0
        assert limiter.politeness_delay == 0.5

    @patch("time.sleep")
    def test_wait_respects_rate_limit(self, mock_sleep):
        limiter = RateLimiter(rate_limit=0.001, politeness_delay=0.001)
        limiter.wait("https://example.com/page1")
        limiter.wait("https://example.com/page2")
        # Should have slept at least once for rate limiting
        mock_sleep.assert_called()


class TestLinkExtractor:
    def test_extract_absolute_links(self):
        html = """
        <html><body>
        <a href="https://example.com/page1">Link 1</a>
        <a href="https://example.com/page2">Link 2</a>
        </body></html>
        """
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_extract_relative_links(self):
        html = """
        <html><body>
        <a href="/page1">Link 1</a>
        <a href="page2">Link 2</a>
        </body></html>
        """
        links = LinkExtractor.extract_links(html, "https://example.com/base/")
        assert "https://example.com/page1" in links
        assert "https://example.com/base/page2" in links

    def test_skip_javascript_links(self):
        html = '<a href="javascript:void(0)">Click</a>'
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_skip_mailto_links(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_skip_anchor_links(self):
        html = '<a href="#section">Section</a>'
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_deduplicate_links(self):
        html = """
        <a href="https://example.com/page1">Link 1</a>
        <a href="https://example.com/page1">Link 1 again</a>
        """
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert len(links) == 1

    def test_remove_fragments(self):
        html = '<a href="https://example.com/page#section">Link</a>'
        links = LinkExtractor.extract_links(html, "https://example.com")
        assert "https://example.com/page" in links
        assert "https://example.com/page#section" not in links


class TestPageParser:
    def test_parse_title(self):
        html = "<html><head><title>Test Page</title></head><body>Content</body></html>"
        page = PageParser.parse(html, "https://example.com")
        assert page.title == "Test Page"

    def test_parse_meta_description(self):
        html = """
        <html><head>
        <meta name="description" content="A test description">
        </head><body>Content</body></html>
        """
        page = PageParser.parse(html, "https://example.com")
        assert page.meta_description == "A test description"

    def test_parse_content(self):
        html = "<html><body><p>Hello World</p></body></html>"
        page = PageParser.parse(html, "https://example.com")
        assert "Hello World" in page.content

    def test_parse_removes_scripts(self):
        html = """
        <html><body>
        <p>Visible text</p>
        <script>alert('hidden')</script>
        </body></html>
        """
        page = PageParser.parse(html, "https://example.com")
        assert "Visible text" in page.content
        assert "alert" not in page.content

    def test_parse_removes_styles(self):
        html = """
        <html><body>
        <p>Visible text</p>
        <style>.hidden { display: none; }</style>
        </body></html>
        """
        page = PageParser.parse(html, "https://example.com")
        assert "Visible text" in page.content
        assert "display" not in page.content

    def test_parse_word_count(self):
        html = "<html><body><p>One two three four five</p></body></html>"
        page = PageParser.parse(html, "https://example.com")
        assert page.word_count == 5

    def test_parse_truncates_long_content(self):
        long_content = "word " * 60000
        html = f"<html><body><p>{long_content}</p></body></html>"
        page = PageParser.parse(html, "https://example.com")
        assert len(page.content) <= 50000


class TestWebCrawler:
    def test_crawler_default_config(self):
        crawler = WebCrawler()
        assert crawler.config.max_depth == 2
        assert crawler.config.max_pages == 100

    def test_crawler_custom_config(self):
        config = CrawlConfig(max_depth=5, max_pages=50)
        crawler = WebCrawler(config=config)
        assert crawler.config.max_depth == 5
        assert crawler.config.max_pages == 50

    def test_is_allowed_domain_no_restrictions(self):
        crawler = WebCrawler()
        assert crawler._is_allowed_domain("https://example.com") is True

    def test_is_allowed_domain_with_blocked(self):
        config = CrawlConfig(blocked_domains=["spam.com"])
        crawler = WebCrawler(config=config)
        assert crawler._is_allowed_domain("https://spam.com") is False
        assert crawler._is_allowed_domain("https://example.com") is True

    def test_is_allowed_domain_with_allowed(self):
        config = CrawlConfig(allowed_domains=["example.com"])
        crawler = WebCrawler(config=config)
        assert crawler._is_allowed_domain("https://example.com") is True
        assert crawler._is_allowed_domain("https://other.com") is False

    def test_crawler_tracks_visited(self):
        crawler = WebCrawler()
        crawler._visited.add("https://example.com")
        assert "https://example.com" in crawler.get_visited_urls()

    def test_crawler_queue_size(self):
        crawler = WebCrawler()
        crawler._queue.append(("https://example.com", 1, None))
        assert crawler.get_queue_size() == 1
