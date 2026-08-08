"""Tests for web crawler module."""

import pytest
from unittest.mock import patch, MagicMock
from personal_index.config import CrawlerConfig, Interest
from personal_index.crawler import Crawler, RateLimiter, CrawlResult


class TestRateLimiter:
    def test_creation(self):
        limiter = RateLimiter(rate=1.0)
        assert limiter.rate == 1.0
        assert limiter.last_request == {}

    def test_wait_records_domain(self):
        limiter = RateLimiter(rate=1000)  # Very fast rate
        limiter.wait("example.com")
        assert "example.com" in limiter.last_request


class TestCrawlResult:
    def test_creation(self):
        result = CrawlResult(url="http://example.com", success=True)
        assert result.url == "http://example.com"
        assert result.success is True
        assert result.error == ""

    def test_failed_result(self):
        result = CrawlResult(
            url="http://example.com",
            success=False,
            error="Connection refused",
        )
        assert result.success is False
        assert result.error == "Connection refused"


class TestCrawler:
    def test_default_config(self):
        crawler = Crawler()
        assert crawler.config.max_depth == 3
        assert crawler.config.timeout == 30

    def test_custom_config(self):
        config = CrawlerConfig(max_depth=5, rate_limit=2.0)
        crawler = Crawler(config=config)
        assert crawler.config.max_depth == 5
        assert crawler.rate_limiter.rate == 2.0

    def test_reset(self):
        crawler = Crawler()
        crawler.visited.add("http://example.com")
        crawler.domain_counts["example.com"] = 1
        crawler.results = [CrawlResult(url="http://example.com", success=True)]
        crawler.reset()
        assert len(crawler.visited) == 0
        assert len(crawler.domain_counts) == 0
        assert len(crawler.results) == 0

    @patch("personal_index.crawler.Crawler._fetch_and_process")
    def test_crawl_single_url(self, mock_fetch):
        mock_fetch.return_value = CrawlResult(
            url="http://example.com",
            success=True,
            depth=0,
            links_found=0,
        )
        crawler = Crawler()
        results = crawler.crawl(["http://example.com"])
        assert len(results) == 1
        assert "example.com" in results[0].url

    @patch("personal_index.crawler.Crawler._fetch_and_process")
    def test_crawl_respects_max_depth(self, mock_fetch):
        mock_fetch.return_value = CrawlResult(
            url="http://example.com",
            success=True,
            depth=0,
            links_found=0,
        )
        config = CrawlerConfig(max_depth=1)
        crawler = Crawler(config=config)
        results = crawler.crawl(["http://example.com"])
        assert len(results) == 1

    @patch("personal_index.crawler.Crawler._fetch_and_process")
    def test_crawl_invalid_url(self, mock_fetch):
        crawler = Crawler()
        results = crawler.crawl(["not-a-url"])
        assert len(results) == 0

    @patch("personal_index.crawler.Crawler._fetch_and_process")
    def test_crawl_progress_callback(self, mock_fetch):
        mock_fetch.return_value = CrawlResult(
            url="http://example.com",
            success=True,
            depth=0,
            links_found=0,
        )
        progress_calls = []

        def on_progress(url, depth, success):
            progress_calls.append((url, depth, success))

        crawler = Crawler()
        crawler.crawl(["http://example.com"], on_progress=on_progress)
        assert len(progress_calls) == 1
        assert "example.com" in progress_calls[0][0]
        assert progress_calls[0][2] is True

    @patch("personal_index.crawler.Crawler._fetch_and_process")
    def test_crawl_domain_limit(self, mock_fetch):
        mock_fetch.return_value = CrawlResult(
            url="http://example.com",
            success=True,
            depth=0,
            links_found=0,
        )
        config = CrawlerConfig(max_pages_per_domain=1)
        crawler = Crawler(config=config)
        results = crawler.crawl([
            "http://example.com/page1",
            "http://example.com/page2",
        ])
        assert len(results) == 1

    def test_get_stats(self):
        crawler = Crawler()
        crawler.results = [
            CrawlResult(url="http://example.com/a", success=True),
            CrawlResult(url="http://example.com/b", success=False),
        ]
        crawler.domain_counts = {"example.com": 2}
        stats = crawler.get_stats()
        assert stats["total_crawled"] == 2
        assert stats["successful"] == 1
        assert stats["failed"] == 1
        assert stats["unique_domains"] == 1

    def test_matches_interests_empty(self):
        crawler = Crawler()
        assert crawler._matches_interests("some text", []) is True

    def test_matches_interests_match(self):
        crawler = Crawler()
        interest = Interest(topic="AI", keywords=["neural"])
        assert crawler._matches_interests("neural networks", [interest]) is True

    def test_matches_interests_no_match(self):
        crawler = Crawler()
        interest = Interest(topic="AI", keywords=["neural"])
        assert crawler._matches_interests("cooking recipes", [interest]) is False

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Test content</body></html>"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body>Test content</body></html>"
        mock_get.return_value = mock_response

        crawler = Crawler()
        result = crawler._fetch_and_process("http://example.com", 0, [])
        assert result.success is True
        assert result.content is not None

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_404(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        crawler = Crawler()
        result = crawler._fetch_and_process("http://example.com", 0, [])
        assert result.success is False
        assert "404" in result.error

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_too_large(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"x" * 2_000_000
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "x" * 2_000_000
        mock_get.return_value = mock_response

        crawler = Crawler()
        result = crawler._fetch_and_process("http://example.com", 0, [])
        assert result.success is False
        assert "too large" in result.error.lower()

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_wrong_content_type(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"binary data"
        mock_response.headers = {"Content-Type": "application/pdf"}
        mock_response.text = "binary data"
        mock_get.return_value = mock_response

        crawler = Crawler()
        result = crawler._fetch_and_process("http://example.com", 0, [])
        assert result.success is False
        assert "content type" in result.error.lower()

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_interest_filter(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"<html><body>Cooking recipes</body></html>"
        mock_response.headers = {"Content-Type": "text/html"}
        mock_response.text = "<html><body>Cooking recipes</body></html>"
        mock_get.return_value = mock_response

        crawler = Crawler()
        interest = Interest(topic="AI", keywords=["neural", "machine learning"])
        result = crawler._fetch_and_process("http://example.com", 0, [interest])
        assert result.success is False
        assert "interest" in result.error.lower()

    @patch("personal_index.crawler.requests.Session.get")
    def test_fetch_request_exception(self, mock_get):
        from requests.exceptions import ConnectionError
        mock_get.side_effect = ConnectionError("Connection refused")

        crawler = Crawler()
        result = crawler._fetch_and_process("http://example.com", 0, [])
        assert result.success is False
        assert "Connection" in result.error
