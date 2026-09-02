"""Tests for content_scheduler module."""

from datetime import datetime, timedelta, timezone

import pytest

from personal_index.content_scheduler import TaskScheduler, TaskStatus


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

    def test_cron_range_with_step(self, scheduler):
        task = scheduler.add_task("T", "crawl", "0 9-17/2 * * 1-5")
        assert task.next_run is not None
        assert task._hour == [9, 11, 13, 15, 17]

    def test_cron_dom_dow_or(self, scheduler):
        # Standard cron: when both dom and dow are restricted, a day
        # matches if it satisfies dom OR dow. '0 0 1 * 1' = at 00:00 on
        # the 1st of the month OR on Monday. The next run must be the
        # next Monday (weekday 0), not the next day that is both the
        # 1st and a Monday.
        task = scheduler.add_task("T", "crawl", "0 0 1 * 1")
        assert task.next_run is not None
        assert task.next_run.weekday() == 0  # Monday
        assert task.next_run.hour == 0
        assert task.next_run.minute == 0

    def test_cron_dow_only_still_schedules(self, scheduler):
        # Only dow restricted (dom is '*'): next run is the next Monday.
        task = scheduler.add_task("T", "crawl", "0 0 * * 1")
        assert task.next_run is not None
        assert task.next_run.weekday() == 0

    def test_cron_dom_only_still_schedules(self, scheduler):
        # Only dom restricted (dow is '*'): next run is the next 1st.
        task = scheduler.add_task("T", "crawl", "0 0 1 * *")
        assert task.next_run is not None
        assert task.next_run.day == 1

    def test_cron_dow_7_is_sunday(self, scheduler):
        # Standard cron accepts 7 as an alias for Sunday (0). '0 0 * * 7'
        # must schedule on a Sunday (weekday 6), identical to '0 0 * * 0'.
        task = scheduler.add_task("T", "crawl", "0 0 * * 7")
        assert task.next_run is not None
        assert task.next_run.weekday() == 6  # Sunday
        assert task._dow == [6]
        # Must match the dow=0 result exactly.
        task0 = scheduler.add_task("T0", "crawl", "0 0 * * 0")
        assert task.next_run == task0.next_run

    def test_cron_dow_7_in_range(self, scheduler):
        # A range ending in 7 (e.g. '6-7') covers Saturday and Sunday.
        task = scheduler.add_task("T", "crawl", "0 0 * * 6-7")
        assert task._dow == [5, 6]  # Saturday, Sunday
        assert task.next_run is not None
        assert task.next_run.weekday() in (5, 6)

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
        task_a = scheduler.add_task("A", "crawl", "* * * * *", callback=cb)
        task_b = scheduler.add_task("B", "export", "* * * * *", callback=cb)
        # Force tasks to be due by setting next_run in the past
        task_a.next_run = datetime.now(timezone.utc) - timedelta(minutes=5)
        task_b.next_run = datetime.now(timezone.utc) - timedelta(minutes=5)
        due_results = scheduler.run_due_tasks()
        assert len(due_results) == 2
        assert "A" in results
        assert "B" in results

    def test_run_due_tasks_skips_disabled(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        task.next_run = datetime.now(timezone.utc) - timedelta(minutes=5)
        scheduler.disable_task(task.task_id)
        due_results = scheduler.run_due_tasks()
        assert len(due_results) == 0

    def test_run_due_tasks_skips_not_due(self, scheduler):
        scheduler.add_task("T", "crawl", "* * * * *")
        # next_run is in the future (default)
        due_results = scheduler.run_due_tasks()
        assert len(due_results) == 0


# --- Task to_dict ---

class TestTaskDict:
    def test_to_dict(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        d = task.to_dict()
        assert d["name"] == "T"
        assert d["task_type"] == "crawl"
        assert d["status"] == "pending"
        assert d["run_count"] == 0

    def test_to_dict_after_run(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        task.run()
        d = task.to_dict()
        assert d["status"] == "completed"
        assert d["run_count"] == 1
        assert d["last_run"] is not None


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


# --- Additional Scheduler Tests ---

class TestSchedulerEdgeCases:
    def test_task_to_dict_has_all_fields(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *", config={"key": "val"})
        d = task.to_dict()
        assert "task_id" in d
        assert "name" in d
        assert "task_type" in d
        assert "cron_expr" in d
        assert "enabled" in d
        assert "status" in d
        assert "created_at" in d
        assert "last_run" in d
        assert "next_run" in d
        assert "run_count" in d
        assert "last_error" in d
        assert "config" in d

    def test_task_status_enum_values(self):
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_scheduler_stats_by_type_multiple(self, scheduler):
        scheduler.add_task("A", "crawl", "* * * * *")
        scheduler.add_task("B", "crawl", "* * * * *")
        scheduler.add_task("C", "export", "0 * * * *")
        stats = scheduler.get_stats()
        assert stats["by_type"]["crawl"] == 2
        assert stats["by_type"]["export"] == 1

    def test_disable_and_reenable(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        scheduler.disable_task(task.task_id)
        assert task.enabled is False
        scheduler.enable_task(task.task_id)
        assert task.enabled is True

    def test_task_run_updates_last_run(self, scheduler):
        task = scheduler.add_task("T", "crawl", "* * * * *")
        task.run()
        assert task.last_run is not None

    def test_task_run_failure_preserves_error(self, scheduler):
        def cb(task):
            raise RuntimeError("test error")
        task = scheduler.add_task("T", "crawl", "* * * * *", callback=cb)
        task.run()
        assert task.last_error == "test error"
        assert task.status == TaskStatus.FAILED

    def test_list_tasks_empty(self, scheduler):
        assert scheduler.list_tasks() == []
        assert scheduler.list_tasks("crawl") == []
