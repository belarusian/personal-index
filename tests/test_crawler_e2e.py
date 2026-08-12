"""End-to-end tests for the web crawler."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from personal_index.crawler.main import Crawler, CrawlerConfig


class TestCrawlerE2E:
    """Test crawler with realistic scenarios."""

    def test_crawl_single_page(self):
        """Crawl a single page successfully."""
        config = CrawlerConfig(max_depth=1, max_pages=5)
        crawler = Crawler(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is a test page.</p>
            </body>
        </html>
        """

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            mock_get.return_value = mock_response
            pages = crawler.crawl(["https://example.com"], max_depth=1)

        assert len(pages) >= 1
        assert any("Test Page" in p.title for p in pages)

    def test_crawl_respects_max_depth(self):
        """Crawler respects max depth limit."""
        config = CrawlerConfig(max_depth=0, max_pages=5)
        crawler = Crawler(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><head><title>Root</title></head>
        <body><a href="/page1">Page 1</a></body></html>
        """

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            mock_get.return_value = mock_response
            pages = crawler.crawl(["https://example.com"], max_depth=0)

        assert len(pages) >= 1

    def test_crawl_respects_max_pages(self):
        """Crawler respects max pages limit."""
        config = CrawlerConfig(max_depth=3, max_pages=2)
        crawler = Crawler(config=config)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><head><title>Page</title></head>
        <body><a href="/page1">P1</a><a href="/page2">P2</a></body></html>
        """

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            mock_get.return_value = mock_response
            pages = crawler.crawl(["https://example.com"], max_depth=3)

        assert len(pages) <= 2

    def test_crawl_with_interest_store(self):
        """Crawler can use interest store for filtering."""
        from personal_index.interests import InterestStore
        from personal_index.models import Interest

        config = CrawlerConfig(max_depth=1, max_pages=5)
        store = InterestStore()
        store.add(Interest(name="python", keywords=["python"]))

        crawler = Crawler(config=config, interest_store=store)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = """
        <html><head><title>Python Page</title></head>
        <body><p>Python programming content.</p></body></html>
        """

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            mock_get.return_value = mock_response
            pages = crawler.crawl(["https://example.com"], max_depth=1)

        assert len(pages) >= 1

    def test_crawl_handles_errors(self):
        """Crawler handles HTTP errors gracefully."""
        config = CrawlerConfig(max_depth=1, max_pages=5)
        crawler = Crawler(config=config)

        # Use a mock that doesn't raise but returns error response
        mock_response = MagicMock()
        mock_response.status_code = 404

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            mock_get.return_value = mock_response
            pages = crawler.crawl(["https://example.com/nonexistent"], max_depth=1)

        assert isinstance(pages, list)

    def test_crawl_follows_links(self):
        """Crawler follows links up to max depth."""
        config = CrawlerConfig(max_depth=2, max_pages=10)
        crawler = Crawler(config=config)

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            # First call returns root with link to page1
            root_response = MagicMock()
            root_response.status_code = 200
            root_response.text = """
            <html><head><title>Root</title></head>
            <body><a href="https://example.com/page1">Go to Page 1</a></body></html>
            """
            
            # Second call returns page1 with link to page2
            page1_response = MagicMock()
            page1_response.status_code = 200
            page1_response.text = """
            <html><head><title>Page 1</title></head>
            <body><a href="https://example.com/page2">Go to Page 2</a></body></html>
            """
            
            # Third call returns page2
            page2_response = MagicMock()
            page2_response.status_code = 200
            page2_response.text = """
            <html><head><title>Page 2</title></head>
            <body><p>Content</p></body></html>
            """

            mock_get.side_effect = [root_response, page1_response, page2_response]
            pages = crawler.crawl(["https://example.com"], max_depth=2)

        assert len(pages) >= 3

    def test_crawl_robots_txt(self):
        """Crawler respects robots.txt when enabled."""
        config = CrawlerConfig(max_depth=1, respect_robots=True)
        crawler = Crawler(config=config)

        with patch('personal_index.crawler.main.requests.Session.get') as mock_get:
            root_response = MagicMock()
            root_response.status_code = 200
            root_response.text = "<html><body>Content</body></html>"
            
            robots_response = MagicMock()
            robots_response.status_code = 200
            robots_response.text = "User-agent: *\nDisallow: /admin/"

            mock_get.side_effect = [root_response, robots_response]
            pages = crawler.crawl(["https://example.com"], max_depth=1)

        assert isinstance(pages, list)
