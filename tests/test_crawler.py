"""Tests for the crawler module."""

import time
import pytest
from personal_index.crawler import CrawlConfig, CrawlResult, RateLimiter, WebCrawler


class TestCrawlConfig:
    def test_default_config(self):
        config = CrawlConfig()
        assert config.max_depth == 3
        assert config.politeness_delay == 1.0
        assert config.rate_limit == 10
        assert config.timeout == 30
        assert config.max_pages == 1000

    def test_custom_config(self):
        config = CrawlConfig(max_depth=5, politeness_delay=0.5, rate_limit=20)
        assert config.max_depth == 5
        assert config.politeness_delay == 0.5
        assert config.rate_limit == 20


class TestCrawlResult:
    def test_create_result(self):
        result = CrawlResult(url="https://example.com")
        assert result.url == "https://example.com"
        assert result.status_code == 0
        assert result.error is None

    def test_result_with_data(self):
        result = CrawlResult(
            url="https://example.com",
            title="Example",
            content="Hello world",
            status_code=200,
        )
        assert result.title == "Example"
        assert result.content == "Hello world"
        assert result.status_code == 200


class TestRateLimiter:
    def test_acquire_within_limit(self):
        limiter = RateLimiter(rate=10)
        assert limiter.acquire("example.com") is True

    def test_acquire_exhausts_tokens(self):
        limiter = RateLimiter(rate=2)
        assert limiter.acquire("example.com") is True
        assert limiter.acquire("example.com") is True
        assert limiter.acquire("example.com") is False

    def test_different_hosts_independent(self):
        limiter = RateLimiter(rate=1)
        assert limiter.acquire("host1.com") is True
        assert limiter.acquire("host2.com") is True

    def test_wait_time_when_exhausted(self):
        limiter = RateLimiter(rate=1)
        limiter.acquire("example.com")
        assert limiter.wait_time("example.com") > 0

    def test_wait_time_zero_when_available(self):
        limiter = RateLimiter(rate=10)
        assert limiter.wait_time("example.com") == 0.0


class TestWebCrawler:
    def test_init_default(self):
        crawler = WebCrawler()
        assert crawler.config.max_depth == 3
        assert len(crawler.crawled_urls) == 0

    def test_init_custom_config(self):
        config = CrawlConfig(max_depth=5)
        crawler = WebCrawler(config)
        assert crawler.config.max_depth == 5

    def test_get_host(self):
        crawler = WebCrawler()
        assert crawler._get_host("https://example.com/page") == "example.com"
        assert crawler._get_host("http://test.org") == "test.org"

    def test_is_allowed_no_restrictions(self):
        crawler = WebCrawler()
        assert crawler._is_allowed("https://anywhere.com/page") is True

    def test_is_allowed_domain_restriction(self):
        config = CrawlConfig(allowed_domains=["example.com"])
        crawler = WebCrawler(config)
        assert crawler._is_allowed("https://example.com/page") is True
        assert crawler._is_allowed("https://other.com/page") is False

    def test_is_allowed_blocked_path(self):
        config = CrawlConfig(blocked_paths=["/admin"])
        crawler = WebCrawler(config)
        assert crawler._is_allowed("https://example.com/page") is True
        assert crawler._is_allowed("https://example.com/admin/settings") is False

    def test_crawl_basic(self):
        crawler = WebCrawler()
        results = crawler.crawl("https://example.com")
        assert len(results) == 1
        assert results[0].url == "https://example.com"

    def test_crawl_no_duplicate(self):
        crawler = WebCrawler()
        crawler.crawl("https://example.com")
        results = crawler.crawl("https://example.com")
        assert len(results) == 1

    def test_crawl_depth_limit(self):
        config = CrawlConfig(max_depth=0, politeness_delay=0)
        crawler = WebCrawler(config)
        results = crawler.crawl("https://example.com", depth=1)
        assert len(results) == 0

    def test_crawl_max_pages(self):
        config = CrawlConfig(max_pages=1, politeness_delay=0)
        crawler = WebCrawler(config)
        crawler.crawl("https://example.com")
        results = crawler.crawl("https://other.com")
        assert len(results) == 1

    def test_crawl_blocked_url(self):
        config = CrawlConfig(blocked_paths=["/blocked"], politeness_delay=0)
        crawler = WebCrawler(config)
        results = crawler.crawl("https://example.com/blocked/page")
        assert len(results) == 0

    def test_get_stats(self):
        crawler = WebCrawler()
        crawler.crawl("https://example.com/page1")
        crawler.crawl("https://example.com/page2")
        stats = crawler.get_stats()
        assert stats["total_crawled"] == 2
        assert stats["total_results"] == 2
        assert stats["unique_hosts"] == 1

    def test_resolve_links(self):
        crawler = WebCrawler()
        links = crawler._resolve_links(
            "https://example.com/page",
            ["/other", "https://other.com/link", "#anchor"],
        )
        assert "https://example.com/other" in links
        assert "https://other.com/link" in links
        assert len(links) == 3  # anchor resolves to absolute too
