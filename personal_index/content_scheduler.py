"""Content scheduling module for personal-index.

Manages scheduled tasks such as periodic crawls, digest generation,
and content refresh with cron-like scheduling support.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable


class ScheduleType(Enum):
    """Types of scheduling patterns."""

    ONCE = "once"
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    CRON = "cron"


@dataclass
class ScheduledTask:
    """A scheduled task definition.

    Attributes:
        task_id: Unique identifier.
        name: Human-readable task name.
        schedule_type: Type of schedule.
        next_run: When the task should next run.
        last_run: When the task last ran.
        run_count: Number of times the task has run.
        enabled: Whether the task is enabled.
        callback: Function to call when task runs.
        cron_expression: Cron expression for CRON type.
        max_runs: Maximum number of runs (None for unlimited).
        metadata: Additional task metadata.
    """

    task_id: str
    name: str
    schedule_type: ScheduleType = ScheduleType.ONCE
    next_run: datetime | None = None
    last_run: datetime | None = None
    run_count: int = 0
    enabled: bool = True
    callback: Callable | None = None
    cron_expression: str | None = None
    max_runs: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def is_due(self, now: datetime | None = None) -> bool:
        """Check if the task is due to run."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        check_time = now or datetime.now()
        return check_time >= self.next_run

    def mark_run(self, now: datetime | None = None) -> None:
        """Mark the task as having run and schedule next run."""
        run_time = now or datetime.now()
        self.last_run = run_time
        self.run_count += 1
        self.next_run = self._calculate_next_run(run_time)

    def _calculate_next_run(self, last_run: datetime) -> datetime | None:
        """Calculate when the task should next run."""
        if self.max_runs and self.run_count >= self.max_runs:
            return None

        intervals = {
            ScheduleType.HOURLY: timedelta(hours=1),
            ScheduleType.DAILY: timedelta(days=1),
            ScheduleType.WEEKLY: timedelta(weeks=1),
            ScheduleType.MONTHLY: timedelta(days=30),
        }

        if self.schedule_type == ScheduleType.ONCE:
            return None

        delta = intervals.get(self.schedule_type)
        if delta:
            return last_run + delta

        return None


@dataclass
class TaskRunRecord:
    """Record of a task execution.

    Attributes:
        task_id: ID of the task that ran.
        started_at: When the task started.
        completed_at: When the task completed.
        success: Whether the task succeeded.
        duration_seconds: How long the task took.
        result: Task result data.
        error: Error message if task failed.
    """

    task_id: str
    started_at: datetime
    completed_at: datetime | None = None
    success: bool = False
    duration_seconds: float = 0.0
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None


class TaskScheduler:
    """Manages and executes scheduled tasks.

    Provides task registration, scheduling, and execution
    with history tracking.
    """

    def __init__(self) -> None:
        self.tasks: dict[str, ScheduledTask] = {}
        self.run_history: list[TaskRunRecord] = []

    def register(
        self,
        task_id: str,
        name: str,
        schedule_type: ScheduleType = ScheduleType.ONCE,
        next_run: datetime | None = None,
        callback: Callable | None = None,
        **kwargs: Any,
    ) -> ScheduledTask:
        """Register a new scheduled task.

        Args:
            task_id: Unique task identifier.
            name: Human-readable name.
            schedule_type: Schedule type.
            next_run: When to first run.
            callback: Function to execute.
            **kwargs: Additional task parameters.

        Returns:
            The registered ScheduledTask.
        """
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            schedule_type=schedule_type,
            next_run=next_run,
            callback=callback,
            **kwargs,
        )
        self.tasks[task_id] = task
        return task

    def remove(self, task_id: str) -> bool:
        """Remove a scheduled task."""
        if task_id in self.tasks:
            del self.tasks[task_id]
            return True
        return False

    def get_due_tasks(
        self,
        now: datetime | None = None,
    ) -> list[ScheduledTask]:
        """Get all tasks that are due to run."""
        return [t for t in self.tasks.values() if t.is_due(now)]

    def run_due(
        self,
        now: datetime | None = None,
    ) -> list[TaskRunRecord]:
        """Run all due tasks and return records.

        Args:
            now: Current time (defaults to now).

        Returns:
            List of TaskRunRecord for executed tasks.
        """
        due_tasks = self.get_due_tasks(now)
        records = []

        for task in due_tasks:
            record = self._execute_task(task, now)
            records.append(record)
            self.run_history.append(record)

        return records

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_history(
        self,
        task_id: str | None = None,
        limit: int = 10,
    ) -> list[TaskRunRecord]:
        """Get task run history, optionally filtered by task."""
        history = self.run_history
        if task_id:
            history = [r for r in history if r.task_id == task_id]
        return history[-limit:]

    def get_stats(self) -> dict[str, Any]:
        """Get scheduler statistics."""
        total = len(self.tasks)
        enabled = sum(1 for t in self.tasks.values() if t.enabled)
        total_runs = sum(t.run_count for t in self.tasks.values())
        return {
            "total_tasks": total,
            "enabled_tasks": enabled,
            "disabled_tasks": total - enabled,
            "total_runs": total_runs,
            "history_size": len(self.run_history),
        }

    def _execute_task(
        self,
        task: ScheduledTask,
        now: datetime | None = None,
    ) -> TaskRunRecord:
        """Execute a single task."""
        start_time = now or datetime.now()
        record = TaskRunRecord(
            task_id=task.task_id,
            started_at=start_time,
        )

        try:
            if task.callback:
                result = task.callback()
                record.result = (
                    result if isinstance(result, dict)
                    else {"output": str(result)}
                )
            record.success = True
        except Exception as e:
            record.error = str(e)
            record.success = False

        end_time = now or datetime.now()
        record.completed_at = end_time
        record.duration_seconds = (
            end_time - start_time
        ).total_seconds()

        task.mark_run(now)
        return record
