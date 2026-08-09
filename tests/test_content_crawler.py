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
