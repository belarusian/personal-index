"""Tests for the web crawler module."""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from urllib.parse import urlparse

from personal_index.crawler import (
    CrawledPage,
    RateLimiter,
    RobotsChecker,
    WebCrawler,
)
from personal_index.config import CrawlerConfig
from personal_index.filter import ContentFilter
from personal_index.index import SearchIndex
from personal_index.interests import Interest, InterestStore


class TestCrawledPage:
    def test_create_page(self):
        page = CrawledPage(url="https://example.com", title="Test", content="Hello")
        assert page.url == "https://example.com"
        assert page.title == "Test"
        assert page.status_code == 0

    def test_page_with_error(self):
        page = CrawledPage(url="https://example.com", title="", content="", error="timeout")
        assert page.error == "timeout"


class TestRateLimiter:
    @pytest.mark.asyncio
    async def test_rate_limiter_no_wait_first_request(self):
        limiter = RateLimiter(delay=0.1)
        # First request should not wait
        await limiter.wait("example.com")

    @pytest.mark.asyncio
    async def test_rate_limiter_different_domains(self):
        limiter = RateLimiter(delay=0.1)
        await limiter.wait("example.com")
        await limiter.wait("other.com")  # Different domain, no wait needed


class TestRobotsChecker:
    def test_parse_robots_allow_all(self):
        checker = RobotsChecker()
        result = checker._parse_robots("User-agent: *\nAllow: /")
        assert result == []  # No disallow rules

    def test_parse_robots_with_disallow(self):
        checker = RobotsChecker()
        result = checker._parse_robots("User-agent: *\nDisallow: /private")
        assert result is None  # Has disallow rules


class TestWebCrawler:
    def test_default_config(self):
        crawler = WebCrawler()
        assert crawler.config.max_depth == 3
        assert crawler.config.politeness_delay == 1.0

    def test_custom_config(self):
        config = CrawlerConfig(max_depth=5, politeness_delay=0.5)
        crawler = WebCrawler(config=config)
        assert crawler.config.max_depth == 5

    def test_stats_initial(self):
        crawler = WebCrawler()
        assert crawler.stats["pages_crawled"] == 0
        assert crawler.stats["pages_indexed"] == 0

    def test_reset_stats(self):
        crawler = WebCrawler()
        crawler._stats["pages_crawled"] = 10
        crawler.reset_stats()
        assert crawler.stats["pages_crawled"] == 0

    def test_extract_title(self):
        crawler = WebCrawler()
        html = "<html><head><title>Test Page</title></head></html>"
        assert crawler._extract_title(html) == "Test Page"

    def test_extract_title_missing(self):
        crawler = WebCrawler()
        html = "<html><body>No title</body></html>"
        assert crawler._extract_title(html) == ""

    def test_extract_text(self):
        crawler = WebCrawler()
        html = "<html><body><p>Hello World</p><script>var x=1;</script></body></html>"
        text = crawler._extract_text(html)
        assert "Hello World" in text
        assert "var x=1" not in text

    def test_extract_text_removes_scripts(self):
        crawler = WebCrawler()
        html = "<html><body><script>alert('xss')</script><p>Safe text</p></body></html>"
        text = crawler._extract_text(html)
        assert "alert" not in text
        assert "Safe text" in text

    def test_extract_text_removes_styles(self):
        crawler = WebCrawler()
        html = "<html><body><style>.hidden { display: none; }</style><p>Visible</p></body></html>"
        text = crawler._extract_text(html)
        assert "display" not in text
        assert "Visible" in text

    def test_extract_links_absolute(self):
        crawler = WebCrawler()
        html = '<a href="https://example.com/page">Link</a>'
        links = crawler._extract_links(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_extract_links_relative(self):
        crawler = WebCrawler()
        html = '<a href="/page">Link</a>'
        links = crawler._extract_links(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_extract_links_no_javascript(self):
        crawler = WebCrawler()
        html = '<a href="javascript:void(0)">JS Link</a>'
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_extract_links_no_mailto(self):
        crawler = WebCrawler()
        html = '<a href="mailto:test@example.com">Email</a>'
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_extract_links_no_hash(self):
        crawler = WebCrawler()
        html = '<a href="#section">Anchor</a>'
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 0

    def test_clean_text(self):
        crawler = WebCrawler()
        text = crawler._clean_text("  Hello   World  ")
        assert text == "Hello World"

    def test_parse_html(self):
        crawler = WebCrawler()
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <p>Hello World</p>
            <a href="https://example.com/link">Link</a>
        </body>
        </html>
        """
        title, content, links = crawler._parse_html(html, "https://example.com")
        assert title == "Test Page"
        assert "Hello World" in content
        assert "https://example.com/link" in links

    def test_extract_text_html_entities(self):
        crawler = WebCrawler()
        html = "<p>Hello &amp; World &lt;test&gt;</p>"
        text = crawler._extract_text(html)
        assert "&" in text
        assert "<" in text

    def test_extract_links_mixed(self):
        crawler = WebCrawler()
        html = """
        <a href="https://other.com/page">Absolute</a>
        <a href="/relative">Relative</a>
        <a href="javascript:void(0)">JS</a>
        <a href="#anchor">Anchor</a>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert "https://other.com/page" in links
        assert "https://example.com/relative" in links
        assert len(links) == 2

    def test_reset_visited(self):
        crawler = WebCrawler()
        crawler._visited.add("https://example.com")
        crawler.reset_visited()
        assert len(crawler._visited) == 0
