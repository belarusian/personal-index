"""Priority task queue for managing crawl and index operations."""

from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    """Priority levels for tasks in the queue."""

    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(str, Enum):
    """Possible statuses for a task."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class Task:
    """A unit of work in the task queue."""

    priority: int
    sequence: int = field(compare=True)
    task_id: str = field(compare=False)
    name: str = field(compare=False, default="")
    data: dict[str, Any] = field(compare=False, default_factory=dict)
    status: TaskStatus = field(compare=False, default=TaskStatus.PENDING)
    created_at: float = field(compare=False, default_factory=time.time)
    started_at: float | None = field(compare=False, default=None)
    completed_at: float | None = field(compare=False, default=None)
    error: str | None = field(compare=False, default=None)
    result: Any = field(compare=False, default=None)

    def start(self) -> None:
        """Mark the task as running and record start time."""
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def complete(self, result: Any = None) -> None:
        """Mark the task as completed with an optional result."""
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result

    def fail(self, error: str) -> None:
        """Mark the task as failed with an error message."""
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def cancel(self) -> None:
        """Mark the task as cancelled."""
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()

    @property
    def duration(self) -> float | None:
        """Elapsed time in seconds between start and completion, or None."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None


class TaskQueue:
    """Thread-safe priority task queue."""

    def __init__(self, max_size: int = 10000):
        self._heap: list[Task] = []
        self._tasks: dict[str, Task] = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._sequence = 0
        self._completed: list[Task] = []

    def enqueue(self, task_id: str, name: str = "", priority: TaskPriority = TaskPriority.NORMAL,
                data: dict | None = None) -> Task:
        """Add a task to the queue.

        Args:
            task_id: Unique identifier for the task.
            name: Human-readable name.
            priority: Task priority level.
            data: Arbitrary data payload.

        Returns:
            The created Task.
        """
        with self._lock:
            if len(self._heap) >= self._max_size:
                logger.warning("Task queue is full, dropping lowest priority task")
                self._evict_lowest()

            task = Task(
                priority=priority.value,
                sequence=self._sequence,
                task_id=task_id,
                name=name,
                data=data or {},
            )
            self._sequence += 1
            heapq.heappush(self._heap, task)
            self._tasks[task_id] = task
            return task

    def dequeue(self) -> Task | None:
        """Remove and return the highest-priority pending task.

        Returns:
            The next Task, or None if the queue is empty.
        """
        with self._lock:
            while self._heap:
                task = heapq.heappop(self._heap)
                if task.status == TaskStatus.PENDING:
                    task.start()
                    return task
            return None

    def get_task(self, task_id: str) -> Task | None:
        """Look up a task by ID.

        Args:
            task_id: The task identifier.

        Returns:
            The Task, or None if not found.
        """
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a pending task.

        Args:
            task_id: The task identifier.

        Returns:
            True if the task was cancelled, False otherwise.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.cancel()
                return True
            return False

    def complete_task(self, task_id: str, result: Any = None) -> bool:
        """Mark a running task as completed.

        Args:
            task_id: The task identifier.
            result: Optional result value.

        Returns:
            True if the task was completed, False otherwise.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.complete(result)
                self._completed.append(task)
                return True
            return False

    def fail_task(self, task_id: str, error: str) -> bool:
        """Mark a running task as failed.

        Args:
            task_id: The task identifier.
            error: Error message.

        Returns:
            True if the task was marked failed, False otherwise.
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.fail(error)
                self._completed.append(task)
                return True
            return False

    def _evict_lowest(self) -> None:
        if self._heap:
            lowest = heapq.heappop(self._heap)
            if lowest.task_id in self._tasks:
                lowest.cancel()
                del self._tasks[lowest.task_id]

    @property
    def size(self) -> int:
        """Number of tasks in the heap (including non-pending)."""
        with self._lock:
            return len(self._heap)

    @property
    def pending_count(self) -> int:
        """Number of tasks still in PENDING status."""
        with self._lock:
            return sum(1 for t in self._heap if t.status == TaskStatus.PENDING)

    @property
    def completed_count(self) -> int:
        """Number of completed tasks retained."""
        with self._lock:
            return len(self._completed)

    def get_stats(self) -> dict:
        """Get queue statistics.

        Returns:
            Dictionary with queue size, task counts, and status breakdown.
        """
        with self._lock:
            status_counts = {}
            for task in self._tasks.values():
                status_counts[task.status.value] = status_counts.get(task.status.value, 0) + 1
            return {
                "queue_size": len(self._heap),
                "total_tasks": len(self._tasks),
                "completed": len(self._completed),
                "status_breakdown": status_counts,
            }

    def clear_completed(self, keep: int = 100) -> None:
        """Trim the completed task list, keeping only the most recent.

        Args:
            keep: Number of recent completed tasks to retain.
        """
        with self._lock:
            if len(self._completed) > keep:
                self._completed = self._completed[-keep:]
