"""Tests for crawl scheduler module."""

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.config import SchedulerConfig
from personal_index.scheduler import CrawlScheduler
from personal_index.scheduler.crawl_scheduler import ScheduledTask


class TestScheduledTask:
    def test_create_task(self):
        task = ScheduledTask(
            task_id="test",
            name="Test Task",
            seed_urls=["https://example.com"],
        )
        assert task.task_id == "test"
        assert task.enabled is True
        assert task.interval_seconds == 86400

    def test_is_due_no_next_run(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
            next_run=None,
        )
        assert task.is_due is True

    def test_is_due_enabled(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
            next_run=datetime.now(timezone.utc) - timedelta(hours=1),
        )
        assert task.is_due is True

    def test_is_due_not_yet(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
            next_run=datetime.now(timezone.utc) + timedelta(hours=1),
        )
        assert task.is_due is False

    def test_is_due_disabled(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
            enabled=False,
            next_run=None,
        )
        assert task.is_due is False

    def test_mark_completed(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
        )
        task.mark_completed()
        assert task.last_run is not None
        assert task.next_run is not None
        assert task.error is None

    def test_mark_failed(self):
        task = ScheduledTask(
            task_id="test",
            name="Test",
            seed_urls=["https://example.com"],
        )
        task.mark_failed("Connection error")
        assert task.error == "Connection error"
        assert task.last_run is not None


class TestCrawlScheduler:
    def test_default_config(self):
        scheduler = CrawlScheduler()
        assert scheduler.config.enabled is False
        assert scheduler.config.interval_hours == 24

    def test_add_task(self):
        scheduler = CrawlScheduler()
        task = scheduler.add_task("Test", ["https://example.com"])
        assert task.task_id == "test"
        assert len(scheduler.tasks) == 1

    def test_add_task_custom_interval(self):
        scheduler = CrawlScheduler()
        task = scheduler.add_task("Test", ["https://example.com"], interval_hours=12)
        assert task.interval_seconds == 12 * 3600

    def test_remove_task(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])
        removed = scheduler.remove_task("test")
        assert removed is True
        assert len(scheduler.tasks) == 0

    def test_remove_nonexistent_task(self):
        scheduler = CrawlScheduler()
        removed = scheduler.remove_task("nonexistent")
        assert removed is False

    def test_get_task(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])
        task = scheduler.get_task("test")
        assert task is not None
        assert task.name == "Test"

    def test_get_nonexistent_task(self):
        scheduler = CrawlScheduler()
        assert scheduler.get_task("nonexistent") is None

    def test_get_due_tasks(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])
        due = scheduler.get_due_tasks()
        assert len(due) == 1

    def test_run_due_tasks(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])

        results = []

        def mock_crawl(task):
            results.append(task.task_id)

        executed = scheduler.run_due_tasks(mock_crawl)
        assert "test" in executed
        assert "test" in results

    def test_run_due_tasks_handles_error(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])

        def failing_crawl(task):
            raise Exception("Crawl failed")

        executed = scheduler.run_due_tasks(failing_crawl)
        assert "test" not in executed
        task = scheduler.get_task("test")
        assert task.error == "Crawl failed"

    def test_callbacks(self):
        scheduler = CrawlScheduler()
        scheduler.add_task("Test", ["https://example.com"])

        completed_tasks = []
        error_tasks = []

        scheduler.on_task_complete(lambda t: completed_tasks.append(t.task_id))
        scheduler.on_task_error(lambda t, e: error_tasks.append(t.task_id))

        scheduler.run_due_tasks(lambda t: None)
        assert "test" in completed_tasks
        assert len(error_tasks) == 0

    def test_start_stop(self):
        scheduler = CrawlScheduler()
        scheduler.start(lambda t: None)
        assert scheduler.is_running is True
        scheduler.stop()
        assert scheduler.is_running is False

    def test_start_already_running(self):
        scheduler = CrawlScheduler()
        scheduler.start(lambda t: None)
        scheduler.start(lambda t: None)
        scheduler.stop()
