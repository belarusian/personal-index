"""Priority task queue for managing crawl and index operations."""

from __future__ import annotations

import heapq
import logging
import threading
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TaskPriority(int, Enum):
    CRITICAL = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3
    BACKGROUND = 4


class TaskStatus(str, Enum):
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
    started_at: Optional[float] = field(compare=False, default=None)
    completed_at: Optional[float] = field(compare=False, default=None)
    error: Optional[str] = field(compare=False, default=None)
    result: Any = field(compare=False, default=None)

    def start(self) -> None:
        self.status = TaskStatus.RUNNING
        self.started_at = time.time()

    def complete(self, result: Any = None) -> None:
        self.status = TaskStatus.COMPLETED
        self.completed_at = time.time()
        self.result = result

    def fail(self, error: str) -> None:
        self.status = TaskStatus.FAILED
        self.completed_at = time.time()
        self.error = error

    def cancel(self) -> None:
        self.status = TaskStatus.CANCELLED
        self.completed_at = time.time()

    @property
    def duration(self) -> Optional[float]:
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
                data: Optional[dict] = None) -> Task:
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

    def dequeue(self) -> Optional[Task]:
        with self._lock:
            while self._heap:
                task = heapq.heappop(self._heap)
                if task.status == TaskStatus.PENDING:
                    task.start()
                    return task
            return None

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._lock:
            return self._tasks.get(task_id)

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.PENDING:
                task.cancel()
                return True
            return False

    def complete_task(self, task_id: str, result: Any = None) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task and task.status == TaskStatus.RUNNING:
                task.complete(result)
                self._completed.append(task)
                return True
            return False

    def fail_task(self, task_id: str, error: str) -> bool:
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
        with self._lock:
            return len(self._heap)

    @property
    def pending_count(self) -> int:
        with self._lock:
            return sum(1 for t in self._heap if t.status == TaskStatus.PENDING)

    @property
    def completed_count(self) -> int:
        with self._lock:
            return len(self._completed)

    def get_stats(self) -> dict:
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
        with self._lock:
            if len(self._completed) > keep:
                self._completed = self._completed[-keep:]
