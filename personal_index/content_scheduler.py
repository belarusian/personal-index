"""Schedule periodic content re-indexing and updates."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any, Dict, List
from collections.abc import Callable


class ScheduleFrequency(Enum):
    """How often to run a scheduled task."""
    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ONCE = "once"

    @property
    def interval_seconds(self) -> int:
        """Return the interval in seconds for this frequency."""
        intervals = {
            ScheduleFrequency.HOURLY: 3600,
            ScheduleFrequency.DAILY: 86400,
            ScheduleFrequency.WEEKLY: 604800,
            ScheduleFrequency.MONTHLY: 2592000,
            ScheduleFrequency.ONCE: 0,
        }
        return intervals[self]


@dataclass
class ScheduledTask:
    """A task to be run on a schedule."""
    name: str
    frequency: ScheduleFrequency
    callback: Callable
    enabled: bool = True
    last_run: str | None = None
    next_run: str | None = None
    run_count: int = 0
    created_at: str = ""
    error_count: int = 0
    last_error: str | None = None
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        """Set defaults for created_at and next_run after init."""
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if self.next_run is None:
            self._calculate_next_run()

    def _calculate_next_run(self):
        """Calculate the next run time."""
        if self.frequency == ScheduleFrequency.ONCE:
            self.next_run = datetime.now(timezone.utc).isoformat()
        else:
            base = datetime.now(timezone.utc)
            if self.last_run:
                base = datetime.fromisoformat(self.last_run)
            delta = timedelta(seconds=self.frequency.interval_seconds)
            self.next_run = (base + delta).isoformat()

    def mark_run(self):
        """Mark the task as having run."""
        self.last_run = datetime.now(timezone.utc).isoformat()
        self.run_count += 1
        self._calculate_next_run()

    def mark_error(self, error: str):
        """Record an error from the task."""
        self.error_count += 1
        self.last_error = error

    def is_due(self) -> bool:
        """Check if the task is due to run."""
        if not self.enabled or not self.next_run:
            return False
        next_dt = datetime.fromisoformat(self.next_run)
        return datetime.now(timezone.utc) >= next_dt


@dataclass
class TaskResult:
    """Result of running a scheduled task."""
    task_name: str
    success: bool
    duration_seconds: float = 0.0
    error: str | None = None
    run_at: str = ""

    def __post_init__(self):
        """Set default run_at after init."""
        if not self.run_at:
            self.run_at = datetime.now(timezone.utc).isoformat()


class ContentScheduler:
    """Schedule and manage periodic content re-indexing tasks."""

    def __init__(self):
        """Initialize the content scheduler with empty task and result storage."""
        self._tasks: Dict[str, ScheduledTask] = {}
        self._results: List[TaskResult] = []
        self._running = False
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._max_results = 1000

    @property
    def tasks(self) -> Dict[str, ScheduledTask]:
        """Return a copy of all scheduled tasks."""
        return dict(self._tasks)

    @property
    def results(self) -> List[TaskResult]:
        """Return a copy of all task results."""
        return list(self._results)

    def add_task(
        self,
        name: str,
        frequency: ScheduleFrequency,
        callback: Callable,
        tags: List[str] | None = None,
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        task = ScheduledTask(
            name=name,
            frequency=frequency,
            callback=callback,
            tags=tags or [],
        )
        self._tasks[name] = task
        return task

    def remove_task(self, name: str) -> bool:
        """Remove a scheduled task by name."""
        if name in self._tasks:
            del self._tasks[name]
            return True
        return False

    def get_task(self, name: str) -> ScheduledTask | None:
        """Get a task by name."""
        return self._tasks.get(name)

    def enable_task(self, name: str) -> bool:
        """Enable a task."""
        task = self._tasks.get(name)
        if task:
            task.enabled = True
            return True
        return False

    def disable_task(self, name: str) -> bool:
        """Disable a task."""
        task = self._tasks.get(name)
        if task:
            task.enabled = False
            return True
        return False

    def run_task(self, name: str) -> TaskResult:
        """Run a specific task immediately."""
        task = self._tasks.get(name)
        if not task:
            return TaskResult(task_name=name, success=False, error=f"Task '{name}' not found")

        start = time.monotonic()
        try:
            task.callback()
            duration = time.monotonic() - start
            task.mark_run()
            result = TaskResult(task_name=name, success=True, duration_seconds=duration)
        except Exception as e:
            duration = time.monotonic() - start
            task.mark_error(str(e))
            result = TaskResult(task_name=name, success=False, duration_seconds=duration, error=str(e))

        self._results.append(result)
        self._trim_results()
        return result

    def run_due_tasks(self) -> List[TaskResult]:
        """Run all tasks that are due."""
        results = []
        due_tasks = [name for name, task in self._tasks.items() if task.is_due()]
        for name in due_tasks:
            result = self.run_task(name)
            results.append(result)
        return results

    def get_due_tasks(self) -> List[ScheduledTask]:
        """Get all tasks that are due."""
        return [task for task in self._tasks.values() if task.is_due()]

    def get_enabled_tasks(self) -> List[ScheduledTask]:
        """Get all enabled tasks."""
        return [task for task in self._tasks.values() if task.enabled]

    def get_tasks_by_tag(self, tag: str) -> List[ScheduledTask]:
        """Get tasks with a specific tag."""
        return [task for task in self._tasks.values() if tag in task.tags]

    def start(self, poll_interval: float = 60.0):
        """Start the scheduler in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop,
            args=(poll_interval,),
            daemon=True,
        )
        self._thread.start()

    def stop(self):
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
            self._thread = None

    def _run_loop(self, poll_interval: float):
        """Main scheduler loop."""
        while self._running:
            with self._lock:
                self.run_due_tasks()
            time.sleep(poll_interval)

    def get_task_stats(self) -> Dict[str, Any]:
        """Get statistics about all tasks."""
        return {
            "total_tasks": len(self._tasks),
            "enabled_tasks": sum(1 for t in self._tasks.values() if t.enabled),
            "disabled_tasks": sum(1 for t in self._tasks.values() if not t.enabled),
            "due_tasks": sum(1 for t in self._tasks.values() if t.is_due()),
            "total_runs": sum(t.run_count for t in self._tasks.values()),
            "total_errors": sum(t.error_count for t in self._tasks.values()),
        }

    def get_recent_results(self, limit: int = 10) -> List[TaskResult]:
        """Get the most recent task results."""
        return list(reversed(self._results))[:limit]

    def _trim_results(self):
        """Trim results to max size."""
        if len(self._results) > self._max_results:
            self._results = self._results[-self._max_results:]

    def clear_results(self):
        """Clear all task results."""
        self._results.clear()

    def reset_task(self, name: str) -> bool:
        """Reset a task's run state."""
        task = self._tasks.get(name)
        if task:
            task.run_count = 0
            task.error_count = 0
            task.last_run = None
            task.last_error = None
            task._calculate_next_run()
            return True
        return False
