"""Tests for content_crawler module - crawl linked pages from saved items."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from personal_index.content_crawler import (
    CrawlTask,
    CrawlTaskStatus,
    CrawlQueue,
    ContentCrawler,
    CrawlResult,
    CrawlStats,
)


class TestCrawlTask:
    """Tests for CrawlTask data model."""

    def test_create_task(self):
        task = CrawlTask(source_url="https://example.com/page1")
        assert task.source_url == "https://example.com/page1"
        assert task.status == CrawlTaskStatus.PENDING
        assert task.max_depth == 2
        assert task.created_at is not None

    def test_task_with_custom_depth(self):
        task = CrawlTask(source_url="https://example.com", max_depth=5)
        assert task.max_depth == 5

    def test_task_with_blocked_domains(self):
        task = CrawlTask(
            source_url="https://example.com",
            blocked_domains=["spam.com"],
        )
        assert "spam.com" in task.blocked_domains

    def test_task_with_allowed_domains(self):
        task = CrawlTask(
            source_url="https://example.com",
            allowed_domains=["example.com", "blog.example.com"],
        )
        assert "example.com" in task.allowed_domains

    def test_task_to_dict(self):
        task = CrawlTask(source_url="https://example.com")
        d = task.to_dict()
        assert d["source_url"] == "https://example.com"
        assert d["status"] == CrawlTaskStatus.PENDING

    def test_task_from_dict(self):
        data = {
            "source_url": "https://example.com",
            "status": CrawlTaskStatus.COMPLETED,
            "max_depth": 3,
        }
        task = CrawlTask.from_dict(data)
        assert task.source_url == "https://example.com"
        assert task.status == CrawlTaskStatus.COMPLETED
        assert task.max_depth == 3


class TestCrawlTaskStatus:
    """Tests for CrawlTaskStatus enum."""

    def test_status_values(self):
        assert CrawlTaskStatus.PENDING.value == "pending"
        assert CrawlTaskStatus.RUNNING.value == "running"
        assert CrawlTaskStatus.COMPLETED.value == "completed"
        assert CrawlTaskStatus.FAILED.value == "failed"
        assert CrawlTaskStatus.CANCELLED.value == "cancelled"


class TestCrawlQueue:
    """Tests for CrawlQueue."""

    def test_add_task(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://example.com")
        queue.add_task(task)
        assert len(queue.pending) == 1

    def test_get_next_pending(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://example.com")
        queue.add_task(task)
        next_task = queue.get_next_pending()
        assert next_task is not None
        assert next_task.source_url == "https://example.com"

    def test_get_next_pending_empty(self):
        queue = CrawlQueue()
        assert queue.get_next_pending() is None

    def test_complete_task(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://example.com")
        queue.add_task(task)
        queue.complete_task(task.task_id)
        assert task.status == CrawlTaskStatus.COMPLETED

    def test_fail_task(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://example.com")
        queue.add_task(task)
        queue.fail_task(task.task_id, "timeout")
        assert task.status == CrawlTaskStatus.FAILED
        assert task.error == "timeout"

    def test_cancel_task(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://example.com")
        queue.add_task(task)
        queue.cancel_task(task.task_id)
        assert task.status == CrawlTaskStatus.CANCELLED

    def test_pending_count(self):
        queue = CrawlQueue()
        queue.add_task(CrawlTask(source_url="https://a.com"))
        queue.add_task(CrawlTask(source_url="https://b.com"))
        assert queue.pending_count == 2

    def test_completed_count(self):
        queue = CrawlQueue()
        task = CrawlTask(source_url="https://a.com")
        queue.add_task(task)
        queue.complete_task(task.task_id)
        assert queue.completed_count == 1


class TestCrawlResult:
    """Tests for CrawlResult."""

    def test_create_result(self):
        result = CrawlResult(url="https://example.com")
        assert result.url == "https://example.com"
        assert result.status_code == 0
        assert result.error == ""

    def test_result_to_dict(self):
        result = CrawlResult(
            url="https://example.com",
            title="Test Page",
            status_code=200,
        )
        d = result.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test Page"
        assert d["status_code"] == 200


class TestCrawlStats:
    """Tests for CrawlStats."""

    def test_default_stats(self):
        stats = CrawlStats()
        assert stats.total_pages == 0
        assert stats.successful == 0
        assert stats.failed == 0

    def test_stats_to_dict(self):
        stats = CrawlStats(total_pages=10, successful=8, failed=2)
        d = stats.to_dict()
        assert d["total_pages"] == 10
        assert d["successful"] == 8
        assert d["failed"] == 2


class TestContentCrawler:
    """Tests for ContentCrawler class."""

    def test_init(self):
        crawler = ContentCrawler()
        assert crawler.session is not None

    def test_get_domain(self):
        crawler = ContentCrawler()
        assert crawler._get_domain("https://example.com/page") == "example.com"
        assert crawler._get_domain("http://sub.domain.org/path?q=1") == "sub.domain.org"

    def test_should_crawl_valid_url(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com")
        assert crawler._should_crawl("https://example.com/page", task) is True

    def test_should_crawl_already_visited(self):
        crawler = ContentCrawler()
        crawler._visited.add("https://example.com/page")
        task = CrawlTask(source_url="https://example.com")
        assert crawler._should_crawl("https://example.com/page", task) is False

    def test_should_crawl_blocked_extension(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com")
        assert crawler._should_crawl("https://example.com/image.jpg", task) is False

    def test_should_crawl_blocked_domain(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            blocked_domains=["spam.com"],
        )
        assert crawler._should_crawl("https://spam.com/page", task) is False

    def test_should_crawl_allowed_domains(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            allowed_domains=["example.com"],
        )
        assert crawler._should_crawl("https://example.com/page", task) is True
        assert crawler._should_crawl("https://other.com/page", task) is False

    def test_should_crawl_invalid_scheme(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com")
        assert crawler._should_crawl("ftp://example.com/page", task) is False

    def test_should_crawl_empty_url(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com")
        assert crawler._should_crawl("", task) is False

    def test_extract_links(self):
        crawler = ContentCrawler()
        html = """
        <html><body>
        <a href="/page1">Link 1</a>
        <a href="https://example.com/page2">Link 2</a>
        <a href="javascript:void(0)">JS Link</a>
        <a href="mailto:test@example.com">Email</a>
        <a href="#section">Anchor</a>
        </body></html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links
        assert len([l for l in links if "javascript" in l]) == 0
        assert len([l for l in links if "mailto" in l]) == 0
        assert len([l for l in links if "#section" in l]) == 0

    def test_extract_content(self):
        crawler = ContentCrawler()
        html = """
        <html><head>
        <title>Test Page</title>
        <meta name="description" content="A test page">
        </head><body>
        <p>Hello world</p>
        <script>alert('xss')</script>
        </body></html>
        """
        title, content, meta_desc = crawler._extract_content(html, "https://example.com")
        assert title == "Test Page"
        assert meta_desc == "A test page"
        assert "Hello world" in content
        assert "xss" not in content

    def test_crawl_respects_max_pages(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com", max_pages=1)
        with patch.object(crawler, "_fetch_page", return_value=None):
            stats = crawler.crawl(task)
            assert stats.total_pages == 1
            assert stats.failed == 1

    def test_crawl_marks_completed(self):
        crawler = ContentCrawler()
        task = CrawlTask(source_url="https://example.com", max_pages=1, delay=0)
        with patch.object(crawler, "_fetch_page", return_value=None):
            stats = crawler.crawl(task)
            assert task.status == CrawlTaskStatus.COMPLETED
            assert task.stats is not None
            assert task.completed_at is not None

    def test_crawl_from_saved_item(self):
        crawler = ContentCrawler()
        with patch.object(crawler, "crawl") as mock_crawl:
            mock_crawl.return_value = CrawlStats(total_pages=5)
            stats = crawler.crawl_from_saved_item("https://example.com", max_depth=2)
            assert stats.total_pages == 5
            mock_crawl.assert_called_once()


class TestContentCrawlerIntegration:
    """Integration tests for ContentCrawler with saved items."""

    def test_crawl_depth_limit(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_depth=1,
            max_pages=10,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><head><title>Home</title></head><body>
        <a href="/page1">Page 1</a>
        <a href="/page2">Page 2</a>
        </body></html>
        """
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            stats = crawler.crawl(task)
            # Source + 2 links at depth 1 = 3 pages max
            assert stats.total_pages <= 3

    def test_crawl_with_successful_fetch(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_pages=1,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Test</title></head><body><p>Content</p></body></html>"
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            stats = crawler.crawl(task)
            assert stats.successful == 1
            assert len(task.results) == 1
            assert task.results[0].title == "Test"

    def test_crawl_stats_tracking(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_pages=3,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head><title>Home</title></head><body><a href='/p1'>P1</a></body></html>"
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            stats = crawler.crawl(task)
            assert stats.total_pages >= 1
            assert stats.duration_seconds >= 0

    def test_crawl_blocked_extension_filtering(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_pages=1,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><body>
        <a href="/page.html">HTML</a>
        <a href="/image.jpg">Image</a>
        <a href="/style.css">CSS</a>
        </body></html>
        """
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            stats = crawler.crawl(task)
            # Only HTML page should be crawled, not jpg or css
            results = task.results
            urls = [r.url for r in results]
            assert not any(".jpg" in u for u in urls)
            assert not any(".css" in u for u in urls)

    def test_crawl_result_links_extraction(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_pages=1,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = """
        <html><body>
        <a href="/link1">Link 1</a>
        <a href="/link2">Link 2</a>
        </body></html>
        """
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            crawler.crawl(task)
            assert len(task.results) == 1
            assert len(task.results[0].links) == 2

    def test_crawl_empty_page(self):
        crawler = ContentCrawler()
        task = CrawlTask(
            source_url="https://example.com",
            max_pages=1,
            delay=0,
        )
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "<html><head></head><body></body></html>"
        with patch.object(crawler, "_fetch_page", return_value=mock_resp):
            stats = crawler.crawl(task)
            assert stats.successful == 1
            assert task.results[0].title == ""
            assert task.results[0].content == ""
