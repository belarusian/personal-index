"""Tests for web crawler module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from personal_index.config import CrawlerConfig, Interest
from personal_index.filter import ContentFilter
from personal_index.models import Page, PageStatus
from personal_index.crawler import WebCrawler


class TestWebCrawler:
    def test_default_config(self):
        crawler = WebCrawler()
        assert crawler.config.max_depth == 3
        assert crawler.config.politeness_delay == 1.0

    def test_custom_config(self):
        config = CrawlerConfig(max_depth=5, politeness_delay=0.5)
        crawler = WebCrawler(config=config)
        assert crawler.config.max_depth == 5
        assert crawler.config.politeness_delay == 0.5

    def test_crawl_with_mock(self):
        crawler = WebCrawler(
            config=CrawlerConfig(politeness_delay=0),
            content_filter=ContentFilter([]),
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = "<html><head><title>Test</title></head><body><p>Hello</p></body></html>"
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            assert len(pages) == 1
            assert pages[0].title == "Test"

    def test_crawl_respects_max_depth(self):
        crawler = WebCrawler(
            config=CrawlerConfig(politeness_delay=0),
            content_filter=ContentFilter([]),
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = '<html><body><a href="/page2">Link</a></body></html>'
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            # Should only crawl the seed URL, not follow links
            assert len(pages) == 1

    def test_crawl_handles_http_error(self):
        crawler = WebCrawler(config=CrawlerConfig(politeness_delay=0))

        mock_response = Mock()
        mock_response.status_code = 404

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            assert len(pages) == 0
            assert crawler.stats.get("failed_http", 0) > 0

    def test_crawl_handles_connection_error(self):
        crawler = WebCrawler(config=CrawlerConfig(politeness_delay=0))

        with patch.object(crawler.session, "get", side_effect=requests.exceptions.ConnectionError("Connection refused")):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            assert len(pages) == 0

    def test_crawl_filters_content(self):
        interests = [Interest(topic="AI", keywords=["artificial intelligence"])]
        content_filter = ContentFilter(interests, min_relevance_score=0.0)
        crawler = WebCrawler(
            config=CrawlerConfig(politeness_delay=0),
            content_filter=content_filter,
        )

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = "<html><body><p>Cooking recipes</p></body></html>"
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com"], max_depth=0)
            # Content doesn't match interests, should be filtered
            assert len(pages) == 0

    def test_crawl_stats(self):
        crawler = WebCrawler(config=CrawlerConfig(politeness_delay=0))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com"
        mock_response.text = "<html><body>Test</body></html>"
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            crawler.crawl(["https://example.com"], max_depth=0)
            stats = crawler.stats
            assert "total_crawled" in stats

    def test_domain_limit(self):
        config = CrawlerConfig(politeness_delay=0, max_pages_per_domain=1)
        crawler = WebCrawler(config=config, content_filter=ContentFilter([]))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/page"
        mock_response.text = '<html><body><a href="/other">Link</a></body></html>'
        mock_response.headers = {"Content-Type": "text/html"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com/page"], max_depth=1)
            # Only 1 page per domain allowed
            assert len(pages) <= 1

    def test_context_manager(self):
        with WebCrawler() as crawler:
            assert crawler.session is not None

    def test_close(self):
        crawler = WebCrawler()
        crawler.close()

    def test_non_html_content_skipped(self):
        crawler = WebCrawler(config=CrawlerConfig(politeness_delay=0))

        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.url = "https://example.com/image.png"
        mock_response.text = ""
        mock_response.headers = {"Content-Type": "image/png"}

        with patch.object(crawler.session, "get", return_value=mock_response):
            pages = crawler.crawl(["https://example.com/image.png"], max_depth=0)
            assert len(pages) == 0
            assert crawler.stats.get("skipped_not_html", 0) > 0
