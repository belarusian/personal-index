"""Tests for the content scheduler module."""

from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest

from personal_index.content_scheduler import (
    ContentScheduler,
    ScheduleFrequency,
    ScheduledTask,
    TaskResult,
)


class TestScheduleFrequency:
    def test_interval_seconds(self):
        assert ScheduleFrequency.HOURLY.interval_seconds == 3600
        assert ScheduleFrequency.DAILY.interval_seconds == 86400
        assert ScheduleFrequency.WEEKLY.interval_seconds == 604800
        assert ScheduleFrequency.MONTHLY.interval_seconds == 2592000
        assert ScheduleFrequency.ONCE.interval_seconds == 0

    def test_values(self):
        assert ScheduleFrequency.HOURLY.value == "hourly"
        assert ScheduleFrequency.DAILY.value == "daily"


class TestScheduledTask:
    def test_creation(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.DAILY,
            callback=lambda: None,
        )
        assert task.name == "test"
        assert task.frequency == ScheduleFrequency.DAILY
        assert task.enabled is True
        assert task.run_count == 0
        assert task.error_count == 0
        assert task.created_at != ""
        assert task.next_run is not None

    def test_mark_run(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.DAILY,
            callback=lambda: None,
        )
        task.mark_run()
        assert task.run_count == 1
        assert task.last_run is not None

    def test_mark_error(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.DAILY,
            callback=lambda: None,
        )
        task.mark_error("something failed")
        assert task.error_count == 1
        assert task.last_error == "something failed"

    def test_is_due_once(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.ONCE,
            callback=lambda: None,
        )
        assert task.is_due() is True

    def test_is_due_disabled(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.ONCE,
            callback=lambda: None,
        )
        task.enabled = False
        assert task.is_due() is False

    def test_tags(self):
        task = ScheduledTask(
            name="test",
            frequency=ScheduleFrequency.DAILY,
            callback=lambda: None,
            tags=["indexing", "content"],
        )
        assert "indexing" in task.tags
        assert "content" in task.tags


class TestTaskResult:
    def test_success_result(self):
        result = TaskResult(task_name="test", success=True, duration_seconds=1.5)
        assert result.success is True
        assert result.duration_seconds == 1.5
        assert result.error is None
        assert result.run_at != ""

    def test_error_result(self):
        result = TaskResult(task_name="test", success=False, error="fail")
        assert result.success is False
        assert result.error == "fail"


class TestContentScheduler:
    def setup_method(self):
        self.scheduler = ContentScheduler()

    def test_add_task(self):
        task = self.scheduler.add_task(
            "test_task",
            ScheduleFrequency.DAILY,
            lambda: None,
        )
        assert task.name == "test_task"
        assert "test_task" in self.scheduler.tasks

    def test_remove_task(self):
        self.scheduler.add_task("test_task", ScheduleFrequency.DAILY, lambda: None)
        assert self.scheduler.remove_task("test_task") is True
        assert "test_task" not in self.scheduler.tasks

    def test_remove_nonexistent_task(self):
        assert self.scheduler.remove_task("nonexistent") is False

    def test_get_task(self):
        self.scheduler.add_task("test_task", ScheduleFrequency.DAILY, lambda: None)
        task = self.scheduler.get_task("test_task")
        assert task is not None
        assert task.name == "test_task"

    def test_get_nonexistent_task(self):
        assert self.scheduler.get_task("nonexistent") is None

    def test_enable_task(self):
        self.scheduler.add_task("test_task", ScheduleFrequency.DAILY, lambda: None)
        assert self.scheduler.enable_task("test_task") is True

    def test_disable_task(self):
        self.scheduler.add_task("test_task", ScheduleFrequency.DAILY, lambda: None)
        assert self.scheduler.disable_task("test_task") is True
        assert self.scheduler.get_task("test_task").enabled is False

    def test_enable_nonexistent_task(self):
        assert self.scheduler.enable_task("nonexistent") is False

    def test_run_task_success(self):
        callback = MagicMock()
        self.scheduler.add_task("test_task", ScheduleFrequency.ONCE, callback)
        result = self.scheduler.run_task("test_task")
        assert result.success is True
        assert result.task_name == "test_task"
        assert result.duration_seconds >= 0
        callback.assert_called_once()

    def test_run_task_error(self):
        def failing_callback():
            raise ValueError("test error")

        self.scheduler.add_task("test_task", ScheduleFrequency.ONCE, failing_callback)
        result = self.scheduler.run_task("test_task")
        assert result.success is False
        assert result.error == "test error"

    def test_run_nonexistent_task(self):
        result = self.scheduler.run_task("nonexistent")
        assert result.success is False
        assert "not found" in result.error

    def test_run_due_tasks(self):
        callback = MagicMock()
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, callback)
        self.scheduler.add_task("task2", ScheduleFrequency.ONCE, callback)
        results = self.scheduler.run_due_tasks()
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_get_due_tasks(self):
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, lambda: None)
        self.scheduler.add_task("task2", ScheduleFrequency.DAILY, lambda: None)
        due = self.scheduler.get_due_tasks()
        assert len(due) == 1
        assert due[0].name == "task1"

    def test_get_enabled_tasks(self):
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, lambda: None)
        task2 = self.scheduler.add_task("task2", ScheduleFrequency.ONCE, lambda: None)
        task2.enabled = False
        enabled = self.scheduler.get_enabled_tasks()
        assert len(enabled) == 1
        assert enabled[0].name == "task1"

    def test_get_tasks_by_tag(self):
        self.scheduler.add_task("task1", ScheduleFrequency.DAILY, lambda: None, tags=["indexing"])
        self.scheduler.add_task("task2", ScheduleFrequency.DAILY, lambda: None, tags=["content"])
        tasks = self.scheduler.get_tasks_by_tag("indexing")
        assert len(tasks) == 1
        assert tasks[0].name == "task1"

    def test_task_stats(self):
        self.scheduler.add_task("task1", ScheduleFrequency.DAILY, lambda: None)
        self.scheduler.add_task("task2", ScheduleFrequency.DAILY, lambda: None)
        stats = self.scheduler.get_task_stats()
        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 2
        assert stats["disabled_tasks"] == 0

    def test_get_recent_results(self):
        callback = MagicMock()
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, callback)
        self.scheduler.run_task("task1")
        results = self.scheduler.get_recent_results()
        assert len(results) == 1
        assert results[0].task_name == "task1"

    def test_clear_results(self):
        callback = MagicMock()
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, callback)
        self.scheduler.run_task("task1")
        self.scheduler.clear_results()
        assert len(self.scheduler.results) == 0

    def test_reset_task(self):
        callback = MagicMock()
        self.scheduler.add_task("task1", ScheduleFrequency.DAILY, callback)
        self.scheduler.run_task("task1")
        assert self.scheduler.reset_task("task1") is True
        task = self.scheduler.get_task("task1")
        assert task.run_count == 0
        assert task.error_count == 0

    def test_reset_nonexistent_task(self):
        assert self.scheduler.reset_task("nonexistent") is False

    def test_results_property_returns_copy(self):
        self.scheduler.add_task("task1", ScheduleFrequency.ONCE, lambda: None)
        self.scheduler.run_task("task1")
        results = self.scheduler.results
        results.clear()
        assert len(self.scheduler.results) == 1

    def test_tasks_property_returns_copy(self):
        self.scheduler.add_task("task1", ScheduleFrequency.DAILY, lambda: None)
        tasks = self.scheduler.tasks
        tasks.clear()
        assert len(self.scheduler.tasks) == 1
