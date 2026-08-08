"""Tests for personal_index.crawler."""

import pytest
import responses

from personal_index.crawler import Crawler, CrawlerConfig
from personal_index.interest_store import InterestStore
from personal_index.models import Interest, InterestType


@pytest.fixture
def config():
    return CrawlerConfig(
        max_depth=2,
        max_pages=10,
        delay=0,  # No delay for tests
        timeout=5,
    )


@pytest.fixture
def crawler(config):
    return Crawler(config=config)


class TestCrawlerConfig:
    """Tests for CrawlerConfig."""

    def test_default_config(self):
        config = CrawlerConfig()
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.delay == 1.0
        assert config.timeout == 10
        assert config.respect_robots is True

    def test_custom_config(self):
        config = CrawlerConfig(
            max_depth=5,
            max_pages=50,
            delay=2.0,
            allowed_domains=["example.com"],
        )
        assert config.max_depth == 5
        assert config.max_pages == 50
        assert config.delay == 2.0
        assert "example.com" in config.allowed_domains


class TestCrawler:
    """Tests for Crawler."""

    def test_init_default(self):
        crawler = Crawler()
        assert crawler.config.max_depth == 3
        assert crawler._pages_crawled == 0

    def test_get_domain(self, crawler):
        assert crawler._get_domain("https://example.com/path") == "example.com"
        assert crawler._get_domain("http://sub.example.com") == "sub.example.com"

    def test_should_crawl_not_visited(self, crawler):
        assert crawler._should_crawl("https://example.com") is True

    def test_should_crawl_already_visited(self, crawler):
        crawler._visited.add("https://example.com")
        assert crawler._should_crawl("https://example.com") is False

    def test_should_crawl_max_pages(self, crawler):
        crawler.config.max_pages = 0
        assert crawler._should_crawl("https://example.com") is False

    def test_should_crawl_blocked_extension(self, crawler):
        assert crawler._should_crawl("https://example.com/image.jpg") is False
        assert crawler._should_crawl("https://example.com/doc.pdf") is False

    def test_should_crawl_allowed_domains(self, crawler):
        crawler.config.allowed_domains = ["example.com"]
        assert crawler._should_crawl("https://example.com/page") is True
        assert crawler._should_crawl("https://other.com/page") is False

    def test_should_crawl_invalid_scheme(self, crawler):
        assert crawler._should_crawl("ftp://example.com") is False
        assert crawler._should_crawl("file:///local") is False

    @responses.activate
    def test_fetch_success(self, crawler):
        responses.add(
            responses.GET,
            "https://example.com",
            body="<html><body>Hello</body></html>",
            status=200,
        )
        resp = crawler._fetch("https://example.com")
        assert resp is not None
        assert resp.status_code == 200

    @responses.activate
    def test_fetch_404(self, crawler):
        responses.add(
            responses.GET,
            "https://example.com/notfound",
            status=404,
        )
        resp = crawler._fetch("https://example.com/notfound")
        assert resp is None

    @responses.activate
    def test_fetch_timeout(self, crawler):
        responses.add(
            responses.GET,
            "https://example.com/slow",
            body="ok",
            status=200,
        )
        # Simulate by removing the response
        responses.replace(
            responses.GET,
            "https://example.com/slow",
            body=Exception("timeout"),
        )
        # Just test that it doesn't crash
        resp = crawler._fetch("https://example.com/slow")

    def test_extract_links(self, crawler):
        html = """
        <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://example.com/page2">Page 2</a>
            <a href="relative/path">Relative</a>
        </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) >= 2

    def test_extract_content(self, crawler):
        html = """
        <html>
        <head><title>Test Page</title></head>
        <body>
            <p>Hello World</p>
            <script>alert('xss')</script>
        </body>
        </html>
        """
        page = crawler._extract_content(html, "https://example.com")
        assert page.title == "Test Page"
        assert "Hello World" in page.content
        assert "alert" not in page.content

    def test_extract_content_meta_description(self, crawler):
        html = """
        <html>
        <head>
            <meta name="description" content="A test description">
        </head>
        <body><p>Content</p></body>
        </html>
        """
        page = crawler._extract_content(html, "https://example.com")
        assert page.meta_description == "A test description"

    def test_filter_by_interests_no_store(self, crawler):
        page = crawler._extract_content("<p>test</p>", "https://example.com")
        assert crawler._filter_by_interests(page) is True

    def test_filter_by_interests_match(self, crawler):
        store = InterestStore(storage_path="/tmp/test_interests_ci.json")
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        crawler.interest_store = store

        page = crawler._extract_content(
            "<p>Python programming</p>",
            "https://example.com",
        )
        assert crawler._filter_by_interests(page) is True
        assert "Py" in page.matched_interests

    def test_filter_by_interests_no_match(self, crawler):
        store = InterestStore(storage_path="/tmp/test_interests_ci2.json")
        store.add(Interest("Py", InterestType.KEYWORD, "python", 5))
        crawler.interest_store = store

        page = crawler._extract_content(
            "<p>Java programming</p>",
            "https://example.com",
        )
        assert crawler._filter_by_interests(page) is False

    def test_pages_crawled_property(self, crawler):
        assert crawler.pages_crawled == 0

    def test_results_property(self, crawler):
        assert crawler.results == []
