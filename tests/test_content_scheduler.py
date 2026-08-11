"""Tests for content_scheduler module."""

import pytest
from datetime import datetime, timezone
from personal_index.content_scheduler import TaskScheduler, ScheduledTask, TaskStatus


@pytest.fixture
def scheduler():
    return TaskScheduler()


# --- Task Creation ---

class TestTaskCreation:
    def test_add_task(self, scheduler):
        task = scheduler.add_task("My Crawl", "crawl", "* * * * *")
        assert task.task_id.startswith("task_")
        assert task.name == "My Crawl"
        assert task.task_type == "crawl"

    def test_add_task_with_callback(self, scheduler):
        results = []
        def cb(task):
            results.append(task.name)
        task = scheduler.add_task("Export", "export", "0 * * * *", callback=cb)
        assert task.callback is not None

    def test_add_task_with_config(self, scheduler):
        task = scheduler.add_task("Cleanup", "cleanup", "0 0 * * *", config={"max_age": 30})
        assert task.config["max_age"] == 30

    def test_add_multiple_tasks(self, scheduler):
        scheduler.add_task("A", "crawl", "* * * * *")
        scheduler.add_task("B", "export", "0 * * * *")
        assert len(scheduler.list_tasks()) == 2

    def test_task_default_enabled(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        assert task.enabled is True

    def test_task_default_status(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        assert task.status == TaskStatus.PENDING


# --- Cron Parsing ---

class TestCronParsing:
    def test_cron_every_minute(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        assert task.next_run is not None

    def test_cron_hourly(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0 * * * *")
        assert task.next_run is not None

    def test_cron_daily(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0 0 * * *")
        assert task.next_run is not None

    def test_cron_weekly(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0 0 * * 0")
        assert task.next_run is not None

    def test_cron_invalid(self, scheduler):
        task = scheduler.add_task("T", "crawl", "invalid")
        assert task.next_run is None

    def test_cron_step(self, scheduler):
        task = scheduler.add_task("T", "crawl", "*/5 * * * *")
        assert task.next_run is not None

    def test_cron_range(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0 9-17 * * 1-5")
        assert task.next_run is not None

    def test_cron_multiple(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0,30 * * * *")
        assert task.next_run is not None


# --- Task Management ---

class TestTaskManagement:
    def test_get_task(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        found = scheduler.get_task(task.task_id)
        assert found is not None
        assert found.name == "T"

    def test_get_nonexistent_task(self, scheduler):
        assert scheduler.get_task("nonexistent") is None

    def test_list_tasks(self, scheduler):
        scheduler.add_task("A", "crawl", "* * * * *")
        scheduler.add_task("B", "export", "* * * * *")
        assert len(scheduler.list_tasks()) == 2

    def test_list_tasks_by_type(self, scheduler):
        scheduler.add_task("A", "crawl", "* * * * *")
        scheduler.add_task("B", "export", "* * * * *")
        assert len(scheduler.list_tasks("crawl")) == 1

    def test_remove_task(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        assert scheduler.remove_task(task.task_id) is True
        assert scheduler.get_task(task.task_id) is None

    def test_remove_nonexistent_task(self, scheduler):
        assert scheduler.remove_task("nonexistent") is False

    def test_enable_task(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        task.enabled = False
        assert scheduler.enable_task(task.task_id) is True
        assert task.enabled is True

    def test_disable_task(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        assert scheduler.disable_task(task.task_id) is True
        assert task.enabled is False

    def test_enable_nonexistent(self, scheduler):
        assert scheduler.enable_task("nonexistent") is False


# --- Task Execution ---

class TestTaskExecution:
    def test_run_task_success(self, scheduler):
        results = []
        def cb(task):
            results.append(task.name)
        task = scheduler.add_task("Test", "crawl", "* * * * *", callback=cb)
        assert task.run() is True
        assert task.status == TaskStatus.COMPLETED
        assert "Test" in results

    def test_run_task_failure(self, scheduler):
        def cb(task):
            raise ValueError("boom")
        task = scheduler.add_task("Fail", "crawl", "* * * * *", callback=cb)
        assert task.run() is False
        assert task.status == TaskStatus.FAILED
        assert task.last_error == "boom"

    def test_run_task_no_callback(self, scheduler):
        task = scheduler.add_task("NoCB", "crawl", "* * * * *")
        assert task.run() is True
        assert task.status == TaskStatus.COMPLETED

    def test_run_count(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        task.run()
        task.run()
        assert task.run_count == 2

    def test_run_due_tasks(self, scheduler):
        results = []
        def cb(task):
            results.append(task.name)
        scheduler.add_task("A", "crawl", "* * * * *", callback=cb)
        scheduler.add_task("B", "export", "* * * * *", callback=cb)
        due_results = scheduler.run_due_tasks()
        assert len(due_results) == 2


# --- Task to_dict ---

class TestTaskDict:
    def test_to_dict(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        d = task.to_dict()
        assert d["name"] == "T"
        assert d["task_type"] == "crawl"
        assert d["status"] == "pending"
        assert d["run_count"] == 0


# --- Stats ---

class TestStats:
    def test_stats_empty(self, scheduler):
        stats = scheduler.get_stats()
        assert stats["total_tasks"] == 0

    def test_stats_with_tasks(self, scheduler):
        scheduler.add_task("A", "crawl", "* * * * *")
        scheduler.add_task("B", "export", "* * * * *")
        stats = scheduler.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["enabled"] == 2
        assert stats["by_type"]["crawl"] == 1
        assert stats["by_type"]["export"] == 1

    def test_stats_disabled(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        scheduler.disable_task(task.task_id)
        stats = scheduler.get_stats()
        assert stats["disabled"] == 1
