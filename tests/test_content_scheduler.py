"""Tests for the content scheduler module."""

from datetime import datetime, timedelta

from personal_index.content_scheduler import (
    ScheduleType,
    ScheduledTask,
    TaskRunRecord,
    TaskScheduler,
)


class TestScheduledTask:
    def test_create(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test Task",
            schedule_type=ScheduleType.DAILY,
        )
        assert task.enabled is True
        assert task.run_count == 0

    def test_is_due_no_next_run(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
        )
        assert task.is_due() is True

    def test_is_due_enabled(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            next_run=datetime(2024, 1, 1),
        )
        now = datetime(2024, 1, 2)
        assert task.is_due(now) is True

    def test_is_due_not_yet(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            next_run=datetime(2025, 1, 1),
        )
        now = datetime(2024, 1, 1)
        assert task.is_due(now) is False

    def test_is_due_disabled(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            enabled=False,
            next_run=datetime(2020, 1, 1),
        )
        assert task.is_due() is False

    def test_mark_run_daily(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.DAILY,
        )
        now = datetime(2024, 1, 1)
        task.mark_run(now)
        assert task.run_count == 1
        assert task.last_run == now
        assert task.next_run == datetime(2024, 1, 2)

    def test_mark_run_once(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.ONCE,
        )
        task.mark_run(datetime(2024, 1, 1))
        assert task.next_run is None

    def test_max_runs(self) -> None:
        task = ScheduledTask(
            task_id="t1",
            name="Test",
            schedule_type=ScheduleType.DAILY,
            max_runs=2,
        )
        task.mark_run(datetime(2024, 1, 1))
        task.mark_run(datetime(2024, 1, 2))
        assert task.next_run is None


class TestTaskScheduler:
    def setup_method(self) -> None:
        self.scheduler = TaskScheduler()

    def test_register_task(self) -> None:
        task = self.scheduler.register(
            "t1", "Test Task", ScheduleType.DAILY,
        )
        assert self.scheduler.get_task("t1") is task

    def test_remove_task(self) -> None:
        self.scheduler.register("t1", "Test Task")
        assert self.scheduler.remove("t1") is True
        assert self.scheduler.get_task("t1") is None

    def test_remove_nonexistent(self) -> None:
        assert self.scheduler.remove("nonexistent") is False

    def test_get_due_tasks(self) -> None:
        self.scheduler.register(
            "t1", "Due Task",
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.register(
            "t2", "Future Task",
            next_run=datetime(2025, 1, 1),
        )
        due = self.scheduler.get_due_tasks(datetime(2024, 6, 1))
        assert len(due) == 1
        assert due[0].task_id == "t1"

    def test_run_due(self) -> None:
        results = []

        def callback():
            results.append("executed")
            return {"status": "ok"}

        self.scheduler.register(
            "t1", "Test Task",
            next_run=datetime(2024, 1, 1),
            callback=callback,
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is True
        assert len(results) == 1

    def test_run_due_callback_error(self) -> None:
        def failing_callback():
            raise ValueError("Task failed")

        self.scheduler.register(
            "t1", "Failing Task",
            next_run=datetime(2024, 1, 1),
            callback=failing_callback,
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is False
        assert records[0].error == "Task failed"

    def test_run_due_no_callback(self) -> None:
        self.scheduler.register(
            "t1", "No Callback",
            next_run=datetime(2024, 1, 1),
        )
        records = self.scheduler.run_due(datetime(2024, 1, 2))
        assert len(records) == 1
        assert records[0].success is True

    def test_get_history(self) -> None:
        self.scheduler.register(
            "t1", "Test",
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.run_due(datetime(2024, 1, 2))
        history = self.scheduler.get_history("t1")
        assert len(history) == 1

    def test_get_history_limit(self) -> None:
        for i in range(15):
            self.scheduler.register(
                f"t{i}", f"Task {i}",
                next_run=datetime(2024, 1, 1),
            )
        self.scheduler.run_due(datetime(2024, 1, 2))
        history = self.scheduler.get_history(limit=5)
        assert len(history) == 5

    def test_get_stats(self) -> None:
        self.scheduler.register("t1", "Enabled")
        self.scheduler.register("t2", "Disabled", enabled=False)
        stats = self.scheduler.get_stats()
        assert stats["total_tasks"] == 2
        assert stats["enabled_tasks"] == 1
        assert stats["disabled_tasks"] == 1

    def test_task_schedules_next_run(self) -> None:
        self.scheduler.register(
            "t1", "Daily Task",
            schedule_type=ScheduleType.DAILY,
            next_run=datetime(2024, 1, 1),
        )
        self.scheduler.run_due(datetime(2024, 1, 1))
        task = self.scheduler.get_task("t1")
        assert task is not None
        assert task.next_run == datetime(2024, 1, 2)
