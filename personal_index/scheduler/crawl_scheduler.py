"""Scheduled crawling for Personal Index.

Handles periodic re-scanning of tracked topics with configurable intervals.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Callable, Optional

from personal_index.config import SchedulerConfig


@dataclass
class ScheduledTask:
    """Represents a scheduled crawl task."""

    task_id: str
    name: str
    seed_urls: list[str]
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None
    enabled: bool = True
    interval_seconds: float = 86400  # 24 hours
    max_depth: int = 3
    error: Optional[str] = None

    @property
    def is_due(self) -> bool:
        """Check if this task is due to run."""
        if not self.enabled:
            return False
        if self.next_run is None:
            return True
        return datetime.now(timezone.utc) >= self.next_run

    def mark_completed(self) -> None:
        """Mark this task as completed and schedule next run."""
        self.last_run = datetime.now(timezone.utc)
        self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)
        self.error = None

    def mark_failed(self, error: str) -> None:
        """Mark this task as failed."""
        self.error = error
        self.last_run = datetime.now(timezone.utc)
        self.next_run = self.last_run + timedelta(seconds=self.interval_seconds)


class CrawlScheduler:
    """Manages scheduled crawling tasks."""

    def __init__(self, config: Optional[SchedulerConfig] = None) -> None:
        """Initialize the crawl scheduler.

        Args:
            config: Scheduler configuration. Uses defaults if None.
        """
        self.config = config or SchedulerConfig()
        self._tasks: dict[str, ScheduledTask] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._lock = threading.Lock()
        self._on_task_complete: Optional[Callable] = None
        self._on_task_error: Optional[Callable] = None

    @property
    def tasks(self) -> list[ScheduledTask]:
        """Get all scheduled tasks."""
        return list(self._tasks.values())

    @property
    def is_running(self) -> bool:
        """Check if the scheduler is running."""
        return self._running

    def add_task(
        self,
        name: str,
        seed_urls: list[str],
        interval_hours: Optional[float] = None,
        max_depth: int = 3,
    ) -> ScheduledTask:
        """Add a new scheduled crawl task.

        Args:
            name: Task name.
            seed_urls: Seed URLs to crawl.
            interval_hours: Hours between runs. Uses config default if None.
            max_depth: Maximum crawl depth.

        Returns:
            The created ScheduledTask.
        """
        interval = (
            interval_hours * 3600
            if interval_hours is not None
            else self.config.interval_hours * 3600
        )
        task = ScheduledTask(
            task_id=name.replace(" ", "_").lower(),
            name=name,
            seed_urls=seed_urls,
            interval_seconds=interval,
            max_depth=max_depth,
            next_run=datetime.now(timezone.utc),
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a scheduled task.

        Args:
            task_id: The task ID to remove.

        Returns:
            True if the task was removed.
        """
        with self._lock:
            return self._tasks.pop(task_id, None) is not None

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        """Get a task by ID.

        Args:
            task_id: The task ID.

        Returns:
            The task if found, None otherwise.
        """
        return self._tasks.get(task_id)

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get all tasks that are due to run.

        Returns:
            List of tasks that should be executed.
        """
        return [task for task in self._tasks.values() if task.is_due]

    def run_due_tasks(self, crawl_callback: Callable) -> list[str]:
        """Run all due tasks.

        Args:
            crawl_callback: Function to execute a crawl. Should accept
                (task: ScheduledTask) and return list of crawled pages.

        Returns:
            List of task IDs that were executed.
        """
        due_tasks = self.get_due_tasks()
        executed = []

        for task in due_tasks:
            try:
                crawl_callback(task)
                task.mark_completed()
                executed.append(task.task_id)
                if self._on_task_complete:
                    self._on_task_complete(task)
            except Exception as e:
                task.mark_failed(str(e))
                if self._on_task_error:
                    self._on_task_error(task, e)

        return executed

    def start(self, crawl_callback: Callable) -> None:
        """Start the scheduler in a background thread.

        Args:
            crawl_callback: Function to execute a crawl.
        """
        if self._running:
            return

        self._running = True

        def _run_loop() -> None:
            while self._running:
                if self.config.enabled:
                    self.run_due_tasks(crawl_callback)
                time.sleep(60)  # Check every minute

        self._thread = threading.Thread(target=_run_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    def on_task_complete(self, callback: Callable) -> None:
        """Register a callback for task completion.

        Args:
            callback: Function to call when a task completes.
        """
        self._on_task_complete = callback

    def on_task_error(self, callback: Callable) -> None:
        """Register a callback for task errors.

        Args:
            callback: Function to call when a task fails.
        """
        self._on_task_error = callback
