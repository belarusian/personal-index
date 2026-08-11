"""
Content Scheduler Module
Schedule crawls, exports, and cleanup tasks with cron-like expressions.
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ScheduledTask:
    """Represents a single scheduled task."""

    def __init__(
        self,
        task_id: str,
        name: str,
        task_type: str,
        cron_expr: str,
        callback: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None,
        enabled: bool = True,
    ):
        self.task_id = task_id
        self.name = name
        self.task_type = task_type
        self.cron_expr = cron_expr
        self.callback = callback
        self.config = config or {}
        self.enabled = enabled
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now(timezone.utc)
        self.last_run: Optional[datetime] = None
        self.next_run: Optional[datetime] = None
        self.run_count = 0
        self.last_error: Optional[str] = None
        self._minute: List[int] = []
        self._hour: List[int] = []
        self._dom: List[int] = []
        self._month: List[int] = []
        self._dow: List[int] = []
        self._parse_cron()

    def _parse_cron(self) -> None:
        """Parse cron expression and compute next run time."""
        parts = self.cron_expr.strip().split()
        if len(parts) != 5:
            self.next_run = None
            return
        minute, hour, dom, month, dow = parts
        self._minute = self._parse_field(minute, 0, 59)
        self._hour = self._parse_field(hour, 0, 23)
        self._dom = self._parse_field(dom, 1, 31)
        self._month = self._parse_field(month, 1, 12)
        # Cron: 0=Sunday, 1=Monday, ..., 6=Saturday
        # Python weekday(): 0=Monday, ..., 6=Sunday
        # Convert cron DOW to Python weekday
        cron_dow = self._parse_field(dow, 0, 6)
        self._dow = []
        for d in cron_dow:
            if d == 0:
                self._dow.append(6)  # Sunday
            else:
                self._dow.append(d - 1)  # Shift: cron 1(Mon) -> python 0(Mon)
        self._compute_next_run()

    def _parse_field(self, field: str, min_val: int, max_val: int) -> List[int]:
        """Parse a cron field into a list of valid values."""
        if field == "*":
            return list(range(min_val, max_val + 1))
        values = set()
        for part in field.split(","):
            if "/" in part:
                base, step = part.split("/", 1)
                start = int(base) if base != "*" else min_val
                step = int(step)
                values.update(range(start, max_val + 1, step))
            elif "-" in part:
                start, end = part.split("-", 1)
                values.update(range(int(start), int(end) + 1))
            else:
                values.add(int(part))
        return sorted(v for v in values if min_val <= v <= max_val)

    def _compute_next_run(self) -> None:
        """Compute the next scheduled run time."""
        now = datetime.now(timezone.utc)
        candidate = now.replace(second=0, microsecond=0) + timedelta(minutes=1)
        # Try up to 1 year ahead
        for _ in range(525600):
            if (candidate.minute in self._minute and
                candidate.hour in self._hour and
                candidate.day in self._dom and
                candidate.month in self._month and
                candidate.weekday() in self._dow):
                self.next_run = candidate
                return
            candidate += timedelta(minutes=1)
        self.next_run = None

    def is_due(self) -> bool:
        """Check if the task is due to run."""
        if not self.enabled or self.next_run is None:
            return False
        return datetime.now(timezone.utc) >= self.next_run

    def run(self) -> bool:
        """Execute the task callback."""
        self.status = TaskStatus.RUNNING
        try:
            if self.callback:
                self.callback(self)
            self.status = TaskStatus.COMPLETED
            self.last_run = datetime.now(timezone.utc)
            self.run_count += 1
            self._compute_next_run()
            return True
        except Exception as e:
            self.status = TaskStatus.FAILED
            self.last_error = str(e)
            return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "name": self.name,
            "task_type": self.task_type,
            "cron_expr": self.cron_expr,
            "enabled": self.enabled,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "run_count": self.run_count,
            "last_error": self.last_error,
            "config": self.config,
        }


class TaskScheduler:
    """Manages scheduled tasks."""

    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._task_counter = 0

    def add_task(
        self,
        name: str,
        task_type: str,
        cron_expr: str,
        callback: Optional[Callable] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ScheduledTask:
        """Add a new scheduled task."""
        self._task_counter += 1
        task_id = f"task_{self._task_counter}"
        task = ScheduledTask(
            task_id=task_id,
            name=name,
            task_type=task_type,
            cron_expr=cron_expr,
            callback=callback,
            config=config,
        )
        self._tasks[task_id] = task
        return task

    def get_task(self, task_id: str) -> Optional[ScheduledTask]:
        return self._tasks.get(task_id)

    def list_tasks(self, task_type: Optional[str] = None) -> List[ScheduledTask]:
        if task_type:
            return [t for t in self._tasks.values() if t.task_type == task_type]
        return list(self._tasks.values())

    def remove_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def enable_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.enabled = True
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        task = self._tasks.get(task_id)
        if task:
            task.enabled = False
            return True
        return False

    def run_due_tasks(self) -> List[Dict[str, Any]]:
        """Run all tasks that are due."""
        results = []
        for task in self._tasks.values():
            if task.is_due():
                success = task.run()
                results.append({
                    "task_id": task.task_id,
                    "name": task.name,
                    "success": success,
                    "status": task.status.value,
                })
        return results

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_tasks": len(self._tasks),
            "enabled": sum(1 for t in self._tasks.values() if t.enabled),
            "disabled": sum(1 for t in self._tasks.values() if not t.enabled),
            "by_type": self._count_by_type(),
        }

    def _count_by_type(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for task in self._tasks.values():
            counts[task.task_type] = counts.get(task.task_type, 0) + 1
        return counts
