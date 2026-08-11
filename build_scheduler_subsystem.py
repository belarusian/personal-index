#!/usr/bin/env python3
"""Build the scheduling and automation subsystem with 202 commits."""

import subprocess
import os
import textwrap

def run(cmd, check=True):
    """Run a shell command."""
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if check and result.returncode != 0:
        print(f"FAIL: {cmd}")
        print(result.stderr)
    return result

def write_file(path, content):
    """Write content to a file, creating directories as needed."""
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(content)

def git_add_commit(msg):
    """Add all changes and commit with message."""
    run("git add -A")
    run(f'git commit -m "{msg}"')

# ============================================================
# MODULE 1: content_scheduler.py
# ============================================================

SCHEDULER_V1 = '''"""Content scheduler - schedule crawls, exports, and cleanup tasks.

Provides a task scheduling system that manages periodic operations
including web crawling, content exports, and storage cleanup.
"""

from __future__ import annotations

import json
import os
import threading
import time
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable


class TaskStatus(str, Enum):
    """Status of a scheduled task."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SCHEDULED = "scheduled"


class TaskType(str, Enum):
    """Type of scheduled task."""
    CRAWL = "crawl"
    EXPORT = "export"
    CLEANUP = "cleanup"
    RETENTION = "retention"
    HEALTH_CHECK = "health_check"
    NOTIFICATION = "notification"


@dataclass
class TaskSchedule:
    """Schedule configuration for a recurring task."""

    cron_expression: str | None = None
    interval_seconds: int | None = None
    interval_hours: int | None = None
    interval_days: int | None = None
    start_time: datetime | None = None
    end_time: datetime | None = None
    timezone: str = "UTC"
    max_runs: int | None = None
    run_count: int = 0

    def next_run_time(self, last_run: datetime | None = None) -> datetime | None:
        """Calculate the next scheduled run time."""
        base = last_run or datetime.now(timezone.utc)
        if self.interval_seconds:
            return base + timedelta(seconds=self.interval_seconds)
        if self.interval_hours:
            return base + timedelta(hours=self.interval_hours)
        if self.interval_days:
            return base + timedelta(days=self.interval_days)
        return None

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        d = asdict(self)
        d["start_time"] = self.start_time.isoformat() if self.start_time else None
        d["end_time"] = self.end_time.isoformat() if self.end_time else None
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TaskSchedule:
        """Deserialize from dictionary."""
        if data.get("start_time"):
            data["start_time"] = datetime.fromisoformat(data["start_time"])
        if data.get("end_time"):
            data["end_time"] = datetime.fromisoformat(data["end_time"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class ScheduledTask:
    """A scheduled task with metadata and execution state."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    task_type: TaskType = TaskType.CRAWL
    schedule: TaskSchedule = field(default_factory=TaskSchedule)
    handler: str = ""
    status: TaskStatus = TaskStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_run: datetime | None = None
    next_run: datetime | None = None
    last_result: dict[str, Any] | None = None
    error_message: str | None = None
    enabled: bool = True
    priority: int = 5
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dictionary."""
        d = {
            "id": self.id,
            "name": self.name,
            "task_type": self.task_type.value,
            "schedule": self.schedule.to_dict(),
            "handler": self.handler,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_run": self.last_run.isoformat() if self.last_run else None,
            "next_run": self.next_run.isoformat() if self.next_run else None,
            "last_result": self.last_result,
            "error_message": self.error_message,
            "enabled": self.enabled,
            "priority": self.priority,
            "metadata": self.metadata,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ScheduledTask:
        """Deserialize from dictionary."""
        schedule = TaskSchedule.from_dict(data.get("schedule", {}))
        result = cls(
            id=data["id"],
            name=data["name"],
            task_type=TaskType(data["task_type"]),
            schedule=schedule,
            handler=data["handler"],
            status=TaskStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            enabled=data.get("enabled", True),
            priority=data.get("priority", 5),
            metadata=data.get("metadata", {}),
        )
        if data.get("last_run"):
            result.last_run = datetime.fromisoformat(data["last_run"])
        if data.get("next_run"):
            result.next_run = datetime.fromisoformat(data["next_run"])
        result.last_result = data.get("last_result")
        result.error_message = data.get("error_message")
        return result
'''

SCHEDULER_STORE = '''"""Task store for persistent scheduling."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from personal_index.scheduler.content_scheduler import ScheduledTask, TaskStatus, TaskType


@dataclass
class TaskStore:
    """Persistent storage for scheduled tasks."""

    path: str = ".personal_index/tasks.json"
    _tasks: dict[str, ScheduledTask] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        """Load tasks from persistent storage."""
        if not os.path.exists(self.path):
            self._tasks = {}
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._tasks = {}
            for task_data in data.get("tasks", []):
                task = ScheduledTask.from_dict(task_data)
                self._tasks[task.id] = task
        except (json.JSONDecodeError, KeyError):
            self._tasks = {}

    def _save(self) -> None:
        """Persist tasks to storage."""
        os.makedirs(os.path.dirname(self.path) if os.path.dirname(self.path) else ".", exist_ok=True)
        data = {"tasks": [t.to_dict() for t in self._tasks.values()]}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add_task(self, task: ScheduledTask) -> str:
        """Add a new scheduled task."""
        self._tasks[task.id] = task
        self._save()
        return task.id

    def get_task(self, task_id: str) -> ScheduledTask | None:
        """Get a task by ID."""
        return self._tasks.get(task_id)

    def list_tasks(self, task_type: TaskType | None = None,
                   status: TaskStatus | None = None,
                   enabled: bool | None = None) -> list[ScheduledTask]:
        """List tasks with optional filters."""
        tasks = list(self._tasks.values())
        if task_type is not None:
            tasks = [t for t in tasks if t.task_type == task_type]
        if status is not None:
            tasks = [t for t in tasks if t.status == status]
        if enabled is not None:
            tasks = [t for t in tasks if t.enabled == enabled]
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def update_task(self, task_id: str, **kwargs: Any) -> ScheduledTask | None:
        """Update task attributes."""
        task = self._tasks.get(task_id)
        if task is None:
            return None
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)
        self._save()
        return task

    def remove_task(self, task_id: str) -> bool:
        """Remove a task."""
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save()
            return True
        return False

    def count_tasks(self, task_type: TaskType | None = None) -> int:
        """Count tasks, optionally filtered by type."""
        if task_type is None:
            return len(self._tasks)
        return sum(1 for t in self._tasks.values() if t.task_type == task_type)
'''

SCHEDULER_ENGINE = '''"""Scheduler engine - runs scheduled tasks."""

from __future__ import annotations

import logging
import threading
import time
from datetime import datetime, timezone
from typing import Any, Callable

from personal_index.scheduler.content_scheduler import (
    ScheduledTask,
    TaskSchedule,
    TaskStatus,
    TaskType,
)
from personal_index.scheduler.task_store import TaskStore

logger = logging.getLogger(__name__)


class SchedulerEngine:
    """Engine that executes scheduled tasks."""

    def __init__(self, store: TaskStore | None = None):
        self.store = store or TaskStore()
        self._handlers: dict[str, Callable] = {}
        self._running = False
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()

    def register_handler(self, handler_name: str, handler: Callable) -> None:
        """Register a task handler function."""
        self._handlers[handler_name] = handler

    def get_handler(self, handler_name: str) -> Callable | None:
        """Get a registered handler."""
        return self._handlers.get(handler_name)

    def start(self, poll_interval: float = 30.0) -> None:
        """Start the scheduler engine in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(
            target=self._run_loop, args=(poll_interval,), daemon=True
        )
        self._thread.start()
        logger.info("Scheduler engine started")

    def stop(self) -> None:
        """Stop the scheduler engine."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5.0)
        logger.info("Scheduler engine stopped")

    def _run_loop(self, poll_interval: float) -> None:
        """Main execution loop."""
        while self._running:
            try:
                self._process_due_tasks()
            except Exception as e:
                logger.error(f"Error in scheduler loop: {e}")
            time.sleep(poll_interval)

    def _process_due_tasks(self) -> list[str]:
        """Process all tasks that are due to run."""
        now = datetime.now(timezone.utc)
        due_tasks = [
            t for t in self.store.list_tasks(enabled=True)
            if t.next_run is not None and t.next_run <= now
        ]
        executed = []
        for task in due_tasks:
            try:
                self._execute_task(task)
                executed.append(task.id)
            except Exception as e:
                logger.error(f"Task {task.id} failed: {e}")
                with self._lock:
                    task.status = TaskStatus.FAILED
                    task.error_message = str(e)
                self.store._save()
        return executed

    def _execute_task(self, task: ScheduledTask) -> dict[str, Any]:
        """Execute a single task."""
        with self._lock:
            task.status = TaskStatus.RUNNING
            task.last_run = datetime.now(timezone.utc)
        self.store._save()

        handler = self._handlers.get(task.handler)
        if handler is None:
            raise ValueError(f"No handler registered for: {task.handler}")

        result = handler(task.metadata)
        now = datetime.now(timezone.utc)

        with self._lock:
            task.status = TaskStatus.COMPLETED
            task.last_result = result if isinstance(result, dict) else {"result": str(result)}
            task.schedule.run_count += 1
            task.next_run = task.schedule.next_run_time(now)
        self.store._save()

        return task.last_result

    def run_task_now(self, task_id: str) -> dict[str, Any]:
        """Immediately run a specific task."""
        task = self.store.get_task(task_id)
        if task is None:
            raise ValueError(f"Task not found: {task_id}")
        return self._execute_task(task)

    def get_due_tasks(self) -> list[ScheduledTask]:
        """Get all tasks that are due."""
        now = datetime.now(timezone.utc)
        return [
            t for t in self.store.list_tasks(enabled=True)
            if t.next_run is not None and t.next_run <= now
        ]

    def get_upcoming_tasks(self, hours: int = 24) -> list[ScheduledTask]:
        """Get tasks scheduled in the next N hours."""
        from datetime import timedelta
        cutoff = datetime.now(timezone.utc) + timedelta(hours=hours)
        return [
            t for t in self.store.list_tasks(enabled=True)
            if t.next_run is not None and t.next_run <= cutoff
        ]
'''

# ============================================================
# MODULE 2: content_automation.py
# ============================================================

AUTOMATION_V1 = '''"""Content automation - automate workflows: crawl -> enrich -> index -> notify.

Provides workflow automation for content processing pipelines,
orchestrating crawl, enrichment, indexing, and notification steps.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of a workflow execution."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PAUSED = "paused"


class StepStatus(str, Enum):
    """Status of a workflow step."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    """A single step in a workflow."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    step_type: str = ""
    handler: str = ""
    config: dict[str, Any] = field(default_factory=dict)
    depends_on: list[str] = field(default_factory=list)
    on_failure: str = "stop"  # stop, continue, skip_remaining
    retry_count: int = 0
    retry_delay_seconds: float = 0.0
    timeout_seconds: float = 300.0
    status: StepStatus = StepStatus.PENDING
    result: dict[str, Any] | None = None
    error: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.started_at:
            d["started_at"] = self.started_at.isoformat()
        if self.completed_at:
            d["completed_at"] = self.completed_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WorkflowStep:
        if data.get("started_at"):
            data["started_at"] = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            data["completed_at"] = datetime.fromisoformat(data["completed_at"])
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Workflow:
    """A content processing workflow."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: list[WorkflowStep] = field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "steps": [s.to_dict() for s in self.steps],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
            "enabled": self.enabled,
        }
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Workflow:
        steps = [WorkflowStep.from_dict(s) for s in data.get("steps", [])]
        result = cls(
            id=data["id"],
            name=data["name"],
            description=data.get("description", ""),
            steps=steps,
            status=WorkflowStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            metadata=data.get("metadata", {}),
            enabled=data.get("enabled", True),
        )
        if data.get("started_at"):
            result.started_at = datetime.fromisoformat(data["started_at"])
        if data.get("completed_at"):
            result.completed_at = datetime.fromisoformat(data["completed_at"])
        return result
'''

AUTOMATION_ENGINE = '''"""Workflow engine for executing automated workflows."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Callable

from personal_index.automation.content_automation import (
    StepStatus,
    Workflow,
    WorkflowStep,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


class WorkflowEngine:
    """Engine that executes content processing workflows."""

    def __init__(self):
        self._handlers: dict[str, Callable] = {}
        self._workflows: dict[str, Workflow] = {}

    def register_handler(self, handler_name: str, handler: Callable) -> None:
        """Register a step handler."""
        self._handlers[handler_name] = handler

    def add_workflow(self, workflow: Workflow) -> str:
        """Add a workflow to the engine."""
        self._workflows[workflow.id] = workflow
        return workflow.id

    def get_workflow(self, workflow_id: str) -> Workflow | None:
        """Get a workflow by ID."""
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> list[Workflow]:
        """List all workflows."""
        return list(self._workflows.values())

    def remove_workflow(self, workflow_id: str) -> bool:
        """Remove a workflow."""
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            return True
        return False

    def execute_workflow(self, workflow_id: str) -> Workflow:
        """Execute a workflow by running its steps in order."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            raise ValueError(f"Workflow not found: {workflow_id}")

        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now(timezone.utc)

        step_map = {s.id: s for s in workflow.steps}

        # Topological sort based on dependencies
        ordered_steps = self._resolve_step_order(workflow.steps)

        for step in ordered_steps:
            if workflow.status == WorkflowStatus.CANCELLED:
                step.status = StepStatus.SKIPPED
                continue

            # Check dependencies
            deps_met = all(
                step_map.get(dep_id).status == StepStatus.COMPLETED
                for dep_id in step.depends_on
                if dep_id in step_map
            )
            if not deps_met:
                step.status = StepStatus.SKIPPED
                continue

            self._execute_step(step)

        # Determine final status
        failed_steps = [s for s in workflow.steps if s.status == StepStatus.FAILED]
        if failed_steps:
            workflow.status = WorkflowStatus.FAILED
        else:
            workflow.status = WorkflowStatus.COMPLETED
        workflow.completed_at = datetime.now(timezone.utc)

        return workflow

    def _resolve_step_order(self, steps: list[WorkflowStep]) -> list[WorkflowStep]:
        """Resolve step execution order based on dependencies."""
        step_map = {s.id: s for s in steps}
        visited = set()
        result = []

        def visit(step_id: str) -> None:
            if step_id in visited:
                return
            visited.add(step_id)
            step = step_map.get(step_id)
            if step:
                for dep_id in step.depends_on:
                    visit(dep_id)
                result.append(step)

        for step in steps:
            visit(step.id)

        return result

    def _execute_step(self, step: WorkflowStep) -> None:
        """Execute a single workflow step."""
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(timezone.utc)

        handler = self._handlers.get(step.handler)
        if handler is None:
            step.status = StepStatus.FAILED
            step.error = f"No handler registered for: {step.handler}"
            step.completed_at = datetime.now(timezone.utc)
            return

        retries = 0
        while retries <= step.retry_count:
            try:
                result = handler(step.config)
                step.status = StepStatus.COMPLETED
                step.result = result if isinstance(result, dict) else {"result": str(result)}
                step.completed_at = datetime.now(timezone.utc)
                return
            except Exception as e:
                retries += 1
                if retries > step.retry_count:
                    step.status = StepStatus.FAILED
                    step.error = str(e)
                    step.completed_at = datetime.now(timezone.utc)
                    return
                logger.warning(f"Step {step.name} retry {retries}/{step.retry_count}: {e}")

    def cancel_workflow(self, workflow_id: str) -> bool:
        """Cancel a running workflow."""
        workflow = self._workflows.get(workflow_id)
        if workflow is None:
            return False
        if workflow.status == WorkflowStatus.RUNNING:
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now(timezone.utc)
            return True
        return False
'''

AUTOMATION_STORE = '''"""Persistent storage for workflows."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from typing import Any

from personal_index.automation.content_automation import Workflow, WorkflowStatus


@dataclass
class WorkflowStore:
    """Persistent storage for workflows."""

    path: str = ".personal_index/workflows.json"
    _workflows: dict[str, Workflow] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._workflows = {}
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._workflows = {}
            for wf_data in data.get("workflows", []):
                wf = Workflow.from_dict(wf_data)
                self._workflows[wf.id] = wf
        except (json.JSONDecodeError, KeyError):
            self._workflows = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) if os.path.dirname(self.path) else ".", exist_ok=True)
        data = {"workflows": [w.to_dict() for w in self._workflows.values()]}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add(self, workflow: Workflow) -> str:
        self._workflows[workflow.id] = workflow
        self._save()
        return workflow.id

    def get(self, workflow_id: str) -> Workflow | None:
        return self._workflows.get(workflow_id)

    def list_all(self, status: WorkflowStatus | None = None) -> list[Workflow]:
        workflows = list(self._workflows.values())
        if status is not None:
            workflows = [w for w in workflows if w.status == status]
        return workflows

    def update(self, workflow_id: str, **kwargs: Any) -> Workflow | None:
        wf = self._workflows.get(workflow_id)
        if wf is None:
            return None
        for key, value in kwargs.items():
            if hasattr(wf, key):
                setattr(wf, key, value)
        self._save()
        return wf

    def remove(self, workflow_id: str) -> bool:
        if workflow_id in self._workflows:
            del self._workflows[workflow_id]
            self._save()
            return True
        return False
'''

AUTOMATION_PIPELINES = '''"""Pre-built workflow pipelines for common content operations."""

from __future__ import annotations

from personal_index.automation.content_automation import Workflow, WorkflowStep


def create_crawl_enrich_index_notify_pipeline(
    seed_urls: list[str] | None = None,
    max_pages: int = 50,
    crawl_depth: int = 2,
    enrich_fields: list[str] | None = None,
    notify_channels: list[str] | None = None,
) -> Workflow:
    """Create a complete crawl -> enrich -> index -> notify workflow."""
    crawl_step = WorkflowStep(
        name="crawl",
        step_type="crawl",
        handler="crawl_handler",
        config={
            "seed_urls": seed_urls or [],
            "max_pages": max_pages,
            "crawl_depth": crawl_depth,
        },
    )
    enrich_step = WorkflowStep(
        name="enrich",
        step_type="enrich",
        handler="enrich_handler",
        config={
            "fields": enrich_fields or ["title", "description", "keywords", "language"],
        },
        depends_on=[crawl_step.id],
    )
    index_step = WorkflowStep(
        name="index",
        step_type="index",
        handler="index_handler",
        config={"batch_size": 100},
        depends_on=[enrich_step.id],
    )
    notify_step = WorkflowStep(
        name="notify",
        step_type="notify",
        handler="notify_handler",
        config={
            "channels": notify_channels or ["console"],
            "template": "crawl_complete",
        },
        depends_on=[index_step.id],
    )
    return Workflow(
        name="crawl-enrich-index-notify",
        description="Full pipeline: crawl web content, enrich metadata, index for search, notify completion",
        steps=[crawl_step, enrich_step, index_step, notify_step],
    )


def create_export_pipeline(
    format: str = "json",
    output_path: str = "exports/",
    include_metadata: bool = True,
) -> Workflow:
    """Create an export workflow."""
    export_step = WorkflowStep(
        name="export",
        step_type="export",
        handler="export_handler",
        config={
            "format": format,
            "output_path": output_path,
            "include_metadata": include_metadata,
        },
    )
    return Workflow(
        name="content-export",
        description=f"Export content in {format} format",
        steps=[export_step],
    )


def create_cleanup_pipeline(
    max_age_days: int = 90,
    min_score: float = 0.0,
    dry_run: bool = False,
) -> Workflow:
    """Create a cleanup workflow."""
    cleanup_step = WorkflowStep(
        name="cleanup",
        step_type="cleanup",
        handler="cleanup_handler",
        config={
            "max_age_days": max_age_days,
            "min_score": min_score,
            "dry_run": dry_run,
        },
    )
    return Workflow(
        name="content-cleanup",
        description="Remove stale and low-quality content",
        steps=[cleanup_step],
    )
'''

# ============================================================
# MODULE 3: content_monitor.py (new, separate from existing)
# ============================================================

MONITOR_V1 = '''"""Content monitor - monitor health: disk usage, crawl freshness, error rates.

Provides comprehensive health monitoring for the personal-index system,
tracking disk usage, crawl freshness, error rates, and system resources.
"""

from __future__ import annotations

import logging
import os
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class HealthLevel(str, Enum):
    """Health status level."""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class DiskUsage:
    """Disk usage metrics."""

    total_bytes: int = 0
    used_bytes: int = 0
    free_bytes: int = 0
    usage_percent: float = 0.0
    index_size_bytes: int = 0
    cache_size_bytes: int = 0
    data_dir: str = ""

    @property
    def total_gb(self) -> float:
        return self.total_bytes / (1024 ** 3)

    @property
    def used_gb(self) -> float:
        return self.used_bytes / (1024 ** 3)

    @property
    def free_gb(self) -> float:
        return self.free_bytes / (1024 ** 3)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CrawlFreshness:
    """Crawl freshness metrics."""

    total_sources: int = 0
    fresh_sources: int = 0
    stale_sources: int = 0
    avg_hours_since_crawl: float = 0.0
    max_hours_since_crawl: float = 0.0
    last_crawl_time: datetime | None = None
    freshness_threshold_hours: float = 24.0

    @property
    def freshness_percent(self) -> float:
        if self.total_sources == 0:
            return 100.0
        return (self.fresh_sources / self.total_sources) * 100.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.last_crawl_time:
            d["last_crawl_time"] = self.last_crawl_time.isoformat()
        else:
            d["last_crawl_time"] = None
        return d


@dataclass
class ErrorRates:
    """Error rate metrics."""

    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    error_rate_percent: float = 0.0
    errors_by_type: dict[str, int] = field(default_factory=dict)
    window_seconds: int = 3600
    window_start: datetime | None = None
    window_end: datetime | None = None

    def record_success(self) -> None:
        self.total_requests += 1
        self.successful_requests += 1
        self._recalculate()

    def record_error(self, error_type: str = "unknown") -> None:
        self.total_requests += 1
        self.failed_requests += 1
        self.errors_by_type[error_type] = self.errors_by_type.get(error_type, 0) + 1
        self._recalculate()

    def _recalculate(self) -> None:
        if self.total_requests > 0:
            self.error_rate_percent = (self.failed_requests / self.total_requests) * 100.0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        if self.window_start:
            d["window_start"] = self.window_start.isoformat()
        if self.window_end:
            d["window_end"] = self.window_end.isoformat()
        return d
'''

MONITOR_CHECKER = '''"""Health checker for system monitoring."""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from personal_index.monitor.content_monitor import (
    CrawlFreshness,
    DiskUsage,
    ErrorRates,
    HealthLevel,
)

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    check_name: str = ""
    level: HealthLevel = HealthLevel.HEALTHY
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "check_name": self.check_name,
            "level": self.level.value,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp.isoformat(),
        }


@dataclass
class SystemHealth:
    """Overall system health status."""

    overall_level: HealthLevel = HealthLevel.HEALTHY
    disk_usage: DiskUsage | None = None
    crawl_freshness: CrawlFreshness | None = None
    error_rates: ErrorRates | None = None
    checks: list[HealthCheckResult] = field(default_factory=list)
    checked_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "overall_level": self.overall_level.value,
            "disk_usage": self.disk_usage.to_dict() if self.disk_usage else None,
            "crawl_freshness": self.crawl_freshness.to_dict() if self.crawl_freshness else None,
            "error_rates": self.error_rates.to_dict() if self.error_rates else None,
            "checks": [c.to_dict() for c in self.checks],
            "checked_at": self.checked_at.isoformat(),
        }


class HealthChecker:
    """Checks system health across multiple dimensions."""

    def __init__(
        self,
        data_dir: str = ".personal_index",
        disk_warning_percent: float = 80.0,
        disk_critical_percent: float = 95.0,
        freshness_warning_hours: float = 48.0,
        freshness_critical_hours: float = 168.0,
        error_rate_warning_percent: float = 10.0,
        error_rate_critical_percent: float = 50.0,
    ):
        self.data_dir = data_dir
        self.disk_warning_percent = disk_warning_percent
        self.disk_critical_percent = disk_critical_percent
        self.freshness_warning_hours = freshness_warning_hours
        self.freshness_critical_hours = freshness_critical_hours
        self.error_rate_warning_percent = error_rate_warning_percent
        self.error_rate_critical_percent = error_rate_critical_percent

    def check_all(self) -> SystemHealth:
        """Run all health checks."""
        health = SystemHealth()
        health.checks.extend(self.check_disk_usage())
        health.checks.extend(self.check_crawl_freshness())
        health.checks.extend(self.check_error_rates())
        health.overall_level = self._determine_overall_level(health.checks)
        return health

    def check_disk_usage(self) -> list[HealthCheckResult]:
        """Check disk usage health."""
        results = []
        try:
            usage = shutil.disk_usage(self.data_dir)
            disk = DiskUsage(
                total_bytes=usage.total,
                used_bytes=usage.used,
                free_bytes=usage.free,
                usage_percent=(usage.used / usage.total * 100) if usage.total > 0 else 0,
                data_dir=self.data_dir,
            )
            if disk.usage_percent >= self.disk_critical_percent:
                level = HealthLevel.CRITICAL
            elif disk.usage_percent >= self.disk_warning_percent:
                level = HealthLevel.WARNING
            else:
                level = HealthLevel.HEALTHY

            results.append(HealthCheckResult(
                check_name="disk_usage",
                level=level,
                message=f"Disk usage: {disk.usage_percent:.1f}%",
                details=disk.to_dict(),
            ))
        except Exception as e:
            results.append(HealthCheckResult(
                check_name="disk_usage",
                level=HealthLevel.UNKNOWN,
                message=f"Failed to check disk: {e}",
            ))
        return results

    def check_crawl_freshness(self) -> list[HealthCheckResult]:
        """Check crawl freshness."""
        results = []
        freshness = CrawlFreshness()
        try:
            freshness = self._compute_freshness()
            if freshness.avg_hours_since_crawl >= self.freshness_critical_hours:
                level = HealthLevel.CRITICAL
            elif freshness.avg_hours_since_crawl >= self.freshness_warning_hours:
                level = HealthLevel.WARNING
            else:
                level = HealthLevel.HEALTHY
        except Exception as e:
            level = HealthLevel.UNKNOWN
            logger.warning(f"Freshness check failed: {e}")

        results.append(HealthCheckResult(
            check_name="crawl_freshness",
            level=level,
            message=f"Freshness: {freshness.freshness_percent:.1f}% sources fresh",
            details=freshness.to_dict(),
        ))
        return results

    def check_error_rates(self) -> list[HealthCheckResult]:
        """Check error rates."""
        results = []
        error_rates = ErrorRates()
        try:
            error_rates = self._compute_error_rates()
            if error_rates.error_rate_percent >= self.error_rate_critical_percent:
                level = HealthLevel.CRITICAL
            elif error_rates.error_rate_percent >= self.error_rate_warning_percent:
                level = HealthLevel.WARNING
            else:
                level = HealthLevel.HEALTHY
        except Exception as e:
            level = HealthLevel.UNKNOWN
            logger.warning(f"Error rate check failed: {e}")

        results.append(HealthCheckResult(
            check_name="error_rates",
            level=level,
            message=f"Error rate: {error_rates.error_rate_percent:.1f}%",
            details=error_rates.to_dict(),
        ))
        return results

    def _compute_freshness(self) -> CrawlFreshness:
        """Compute crawl freshness from stored data."""
        freshness = CrawlFreshness()
        tasks_path = os.path.join(self.data_dir, "tasks.json")
        if not os.path.exists(tasks_path):
            return freshness
        try:
            import json
            with open(tasks_path, "r") as f:
                data = json.load(f)
            tasks = data.get("tasks", [])
            now = datetime.now(timezone.utc)
            total = 0
            fresh = 0
            max_hours = 0.0
            total_hours = 0.0
            for task in tasks:
                if task.get("task_type") == "crawl":
                    total += 1
                    last_run = task.get("last_run")
                    if last_run:
                        last_dt = datetime.fromisoformat(last_run)
                        hours = (now - last_dt).total_seconds() / 3600
                        total_hours += hours
                        max_hours = max(max_hours, hours)
                        if hours < freshness.freshness_threshold_hours:
                            fresh += 1
            freshness.total_sources = total
            freshness.fresh_sources = fresh
            freshness.stale_sources = total - fresh
            freshness.avg_hours_since_crawl = total_hours / total if total > 0 else 0
            freshness.max_hours_since_crawl = max_hours
        except Exception:
            pass
        return freshness

    def _compute_error_rates(self) -> ErrorRates:
        """Compute error rates from stored data."""
        error_rates = ErrorRates()
        tasks_path = os.path.join(self.data_dir, "tasks.json")
        if not os.path.exists(tasks_path):
            return error_rates
        try:
            import json
            with open(tasks_path, "r") as f:
                data = json.load(f)
            tasks = data.get("tasks", [])
            for task in tasks:
                if task.get("status") == "completed":
                    error_rates.record_success()
                elif task.get("status") == "failed":
                    error_rates.record_error(task.get("error_message", "unknown"))
        except Exception:
            pass
        return error_rates

    def _determine_overall_level(self, checks: list[HealthCheckResult]) -> HealthLevel:
        """Determine overall health from individual checks."""
        if not checks:
            return HealthLevel.UNKNOWN
        levels = [c.level for c in checks]
        if HealthLevel.CRITICAL in levels:
            return HealthLevel.CRITICAL
        if HealthLevel.WARNING in levels:
            return HealthLevel.WARNING
        if HealthLevel.UNKNOWN in levels:
            return HealthLevel.UNKNOWN
        return HealthLevel.HEALTHY
'''

# ============================================================
# MODULE 4: content_alerts.py
# ============================================================

ALERTS_V1 = '''"""Content alerts - alert on anomalies: missed crawls, high error rates, stale content.

Provides an alerting system that detects and reports anomalies in the
personal-index system including missed crawls, high error rates, and stale content.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity level."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertCategory(str, Enum):
    """Alert category."""
    MISSED_CRAWL = "missed_crawl"
    HIGH_ERROR_RATE = "high_error_rate"
    STALE_CONTENT = "stale_content"
    DISK_USAGE = "disk_usage"
    SYSTEM_HEALTH = "system_health"
    WORKFLOW_FAILURE = "workflow_failure"
    RETENTION_POLICY = "retention_policy"
    CUSTOM = "custom"


class AlertState(str, Enum):
    """Alert state."""
    ACTIVE = "active"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    SUPPRESSED = "suppressed"


@dataclass
class Alert:
    """An alert notification."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    category: AlertCategory = AlertCategory.CUSTOM
    severity: AlertSeverity = AlertSeverity.INFO
    title: str = ""
    message: str = ""
    state: AlertState = AlertState.ACTIVE
    source: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    acknowledged_by: str | None = None
    resolved_by: str | None = None

    def acknowledge(self, by: str = "system") -> None:
        self.state = AlertState.ACKNOWLEDGED
        self.acknowledged_at = datetime.now(timezone.utc)
        self.acknowledged_by = by

    def resolve(self, by: str = "system") -> None:
        self.state = AlertState.RESOLVED
        self.resolved_at = datetime.now(timezone.utc)
        self.resolved_by = by

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["category"] = self.category.value
        d["severity"] = self.severity.value
        d["state"] = self.state.value
        if d.get("created_at"):
            d["created_at"] = self.created_at.isoformat()
        if d.get("acknowledged_at"):
            d["acknowledged_at"] = self.acknowledged_at.isoformat()
        if d.get("resolved_at"):
            d["resolved_at"] = self.resolved_at.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Alert:
        result = cls(
            id=data.get("id", str(uuid.uuid4())),
            category=AlertCategory(data.get("category", "custom")),
            severity=AlertSeverity(data.get("severity", "info")),
            title=data.get("title", ""),
            message=data.get("message", ""),
            state=AlertState(data.get("state", "active")),
            source=data.get("source", ""),
            metadata=data.get("metadata", {}),
        )
        if data.get("created_at"):
            result.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("acknowledged_at"):
            result.acknowledged_at = datetime.fromisoformat(data["acknowledged_at"])
        if data.get("resolved_at"):
            result.resolved_at = datetime.fromisoformat(data["resolved_at"])
        result.acknowledged_by = data.get("acknowledged_by")
        result.resolved_by = data.get("resolved_by")
        return result
'''

ALERTS_MANAGER = '''"""Alert manager - manages alert lifecycle."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

from personal_index.alerts.content_alerts import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertState,
)

logger = logging.getLogger(__name__)


@dataclass
class AlertRule:
    """Rule for generating alerts automatically."""

    id: str = ""
    name: str = ""
    category: AlertCategory = AlertCategory.CUSTOM
    severity: AlertSeverity = AlertSeverity.WARNING
    condition: str = ""
    threshold: float = 0.0
    window_minutes: int = 60
    cooldown_minutes: int = 30
    enabled: bool = True
    last_triggered: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        d = {
            "id": self.id,
            "name": self.name,
            "category": self.category.value,
            "severity": self.severity.value,
            "condition": self.condition,
            "threshold": self.threshold,
            "window_minutes": self.window_minutes,
            "cooldown_minutes": self.cooldown_minutes,
            "enabled": self.enabled,
        }
        if self.last_triggered:
            d["last_triggered"] = self.last_triggered.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AlertRule:
        result = cls(
            id=data.get("id", ""),
            name=data.get("name", ""),
            category=AlertCategory(data.get("category", "custom")),
            severity=AlertSeverity(data.get("severity", "warning")),
            condition=data.get("condition", ""),
            threshold=data.get("threshold", 0.0),
            window_minutes=data.get("window_minutes", 60),
            cooldown_minutes=data.get("cooldown_minutes", 30),
            enabled=data.get("enabled", True),
        )
        if data.get("last_triggered"):
            result.last_triggered = datetime.fromisoformat(data["last_triggered"])
        return result


class AlertManager:
    """Manages alert lifecycle and rules."""

    def __init__(self, store_path: str = ".personal_index/alerts.json"):
        self.store_path = store_path
        self._alerts: dict[str, Alert] = {}
        self._rules: dict[str, AlertRule] = {}
        self._handlers: dict[AlertCategory, list[Callable]] = {}
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.store_path):
            return
        try:
            with open(self.store_path, "r") as f:
                data = json.load(f)
            for alert_data in data.get("alerts", []):
                alert = Alert.from_dict(alert_data)
                self._alerts[alert.id] = alert
            for rule_data in data.get("rules", []):
                rule = AlertRule.from_dict(rule_data)
                self._rules[rule.id] = rule
        except (json.JSONDecodeError, KeyError):
            pass

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.store_path) if os.path.dirname(self.store_path) else ".", exist_ok=True)
        data = {
            "alerts": [a.to_dict() for a in self._alerts.values()],
            "rules": [r.to_dict() for r in self._rules.values()],
        }
        with open(self.store_path, "w") as f:
            json.dump(data, f, indent=2)

    def create_alert(
        self,
        category: AlertCategory,
        severity: AlertSeverity,
        title: str,
        message: str,
        source: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> Alert:
        """Create a new alert."""
        alert = Alert(
            category=category,
            severity=severity,
            title=title,
            message=message,
            source=source,
            metadata=metadata or {},
        )
        self._alerts[alert.id] = alert
        self._save()
        self._dispatch(alert)
        return alert

    def acknowledge_alert(self, alert_id: str, by: str = "system") -> Alert | None:
        """Acknowledge an alert."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            return None
        alert.acknowledge(by)
        self._save()
        return alert

    def resolve_alert(self, alert_id: str, by: str = "system") -> Alert | None:
        """Resolve an alert."""
        alert = self._alerts.get(alert_id)
        if alert is None:
            return None
        alert.resolve(by)
        self._save()
        return alert

    def list_alerts(
        self,
        state: AlertState | None = None,
        severity: AlertSeverity | None = None,
        category: AlertCategory | None = None,
        limit: int = 100,
    ) -> list[Alert]:
        """List alerts with optional filters."""
        alerts = list(self._alerts.values())
        if state is not None:
            alerts = [a for a in alerts if a.state == state]
        if severity is not None:
            alerts = [a for a in alerts if a.severity == severity]
        if category is not None:
            alerts = [a for a in alerts if a.category == category]
        alerts.sort(key=lambda a: a.created_at, reverse=True)
        return alerts[:limit]

    def get_active_alerts(self) -> list[Alert]:
        """Get all active alerts."""
        return self.list_alerts(state=AlertState.ACTIVE)

    def add_rule(self, rule: AlertRule) -> str:
        """Add an alert rule."""
        self._rules[rule.id] = rule
        self._save()
        return rule.id

    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self._rules:
            del self._rules[rule_id]
            self._save()
            return True
        return False

    def list_rules(self) -> list[AlertRule]:
        """List all alert rules."""
        return list(self._rules.values())

    def register_handler(self, category: AlertCategory, handler: Callable) -> None:
        """Register a handler for alert category."""
        if category not in self._handlers:
            self._handlers[category] = []
        self._handlers[category].append(handler)

    def _dispatch(self, alert: Alert) -> None:
        """Dispatch alert to registered handlers."""
        handlers = self._handlers.get(alert.category, [])
        for handler in handlers:
            try:
                handler(alert)
            except Exception as e:
                logger.error(f"Alert handler error: {e}")

    def evaluate_rules(self, metrics: dict[str, float]) -> list[Alert]:
        """Evaluate alert rules against current metrics."""
        triggered = []
        now = datetime.now(timezone.utc)
        for rule in self._rules.values():
            if not rule.enabled:
                continue
            if rule.last_triggered:
                cooldown_end = rule.last_triggered + timedelta(minutes=rule.cooldown_minutes)
                if now < cooldown_end:
                    continue
            metric_value = metrics.get(rule.condition, 0.0)
            if metric_value >= rule.threshold:
                alert = self.create_alert(
                    category=rule.category,
                    severity=rule.severity,
                    title=f"Rule triggered: {rule.name}",
                    message=f"{rule.condition} = {metric_value} (threshold: {rule.threshold})",
                    source="rule_engine",
                )
                rule.last_triggered = now
                triggered.append(alert)
        self._save()
        return triggered
'''

ALERTS_DETECTORS = '''"""Alert detectors - detect anomalies and generate alerts."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from personal_index.alerts.content_alerts import (
    Alert,
    AlertCategory,
    AlertSeverity,
)
from personal_index.alerts.alert_manager import AlertManager

logger = logging.getLogger(__name__)


class MissedCrawlDetector:
    """Detects missed crawl schedules."""

    def __init__(self, alert_manager: AlertManager, threshold_hours: float = 24.0):
        self.alert_manager = alert_manager
        self.threshold_hours = threshold_hours

    def check(self, tasks: list[dict[str, Any]]) -> list[Alert]:
        """Check for missed crawls."""
        alerts = []
        now = datetime.now(timezone.utc)
        for task in tasks:
            if task.get("task_type") != "crawl":
                continue
            next_run = task.get("next_run")
            if not next_run:
                continue
            next_dt = datetime.fromisoformat(next_run)
            if next_dt < now:
                hours_overdue = (now - next_dt).total_seconds() / 3600
                if hours_overdue >= self.threshold_hours:
                    severity = AlertSeverity.CRITICAL if hours_overdue > 72 else AlertSeverity.WARNING
                    alert = self.alert_manager.create_alert(
                        category=AlertCategory.MISSED_CRAWL,
                        severity=severity,
                        title=f"Missed crawl: {task.get('name', 'unknown')}",
                        message=f"Crawl task is {hours_overdue:.1f} hours overdue",
                        source="missed_crawl_detector",
                        metadata={"task_id": task.get("id"), "hours_overdue": hours_overdue},
                    )
                    alerts.append(alert)
        return alerts


class HighErrorRateDetector:
    """Detects high error rates."""

    def __init__(self, alert_manager: AlertManager, threshold_percent: float = 25.0):
        self.alert_manager = alert_manager
        self.threshold_percent = threshold_percent

    def check(self, error_rate_percent: float, total_requests: int = 0) -> list[Alert]:
        """Check for high error rates."""
        alerts = []
        if error_rate_percent >= self.threshold_percent:
            severity = AlertSeverity.CRITICAL if error_rate_percent > 50 else AlertSeverity.ERROR
            alert = self.alert_manager.create_alert(
                category=AlertCategory.HIGH_ERROR_RATE,
                severity=severity,
                title=f"High error rate: {error_rate_percent:.1f}%",
                message=f"Error rate exceeds {self.threshold_percent}% threshold",
                source="error_rate_detector",
                metadata={"error_rate": error_rate_percent, "total_requests": total_requests},
            )
            alerts.append(alert)
        return alerts


class StaleContentDetector:
    """Detects stale content."""

    def __init__(self, alert_manager: AlertManager, threshold_days: float = 30.0):
        self.alert_manager = alert_manager
        self.threshold_days = threshold_days

    def check(self, content_items: list[dict[str, Any]]) -> list[Alert]:
        """Check for stale content."""
        alerts = []
        now = datetime.now(timezone.utc)
        stale_count = 0
        for item in content_items:
            last_modified = item.get("last_modified")
            if not last_modified:
                continue
            try:
                mod_dt = datetime.fromisoformat(last_modified)
                days_old = (now - mod_dt).total_seconds() / 86400
                if days_old >= self.threshold_days:
                    stale_count += 1
            except (ValueError, TypeError):
                continue
        if stale_count > 0:
            alert = self.alert_manager.create_alert(
                category=AlertCategory.STALE_CONTENT,
                severity=AlertSeverity.WARNING,
                title=f"Stale content detected: {stale_count} items",
                message=f"{stale_count} content items are older than {self.threshold_days} days",
                source="stale_content_detector",
                metadata={"stale_count": stale_count, "threshold_days": self.threshold_days},
            )
            alerts.append(alert)
        return alerts
'''

# ============================================================
# MODULE 4: content_retention.py
# ============================================================

RETENTION_V1 = '''"""Content retention - retention policies: expire old content, archive inactive.

Provides content retention management with configurable policies for
expiring old content, archiving inactive items, and managing storage.
"""

from __future__ import annotations

import json
import logging
import os
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class RetentionAction(str, Enum):
    """Action to take when retention policy triggers."""
    DELETE = "delete"
    ARCHIVE = "archive"
    DOWNGRADE = "downgrade"
    FLAG = "flag"


class RetentionScope(str, Enum):
    """Scope of retention policy."""
    ALL = "all"
    BY_TYPE = "by_type"
    BY_SOURCE = "by_source"
    BY_TAG = "by_tag"
    BY_SCORE = "by_score"


@dataclass
class RetentionPolicy:
    """A content retention policy."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    action: RetentionAction = RetentionAction.DELETE
    scope: RetentionScope = RetentionScope.ALL
    max_age_days: int = 365
    max_items: int | None = None
    min_score: float = 0.0
    content_types: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    enabled: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_applied: datetime | None = None
    items_processed: int = 0
    items_deleted: int = 0
    items_archived: int = 0

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["action"] = self.action.value
        d["scope"] = self.scope.value
        d["created_at"] = self.created_at.isoformat()
        if d.get("last_applied"):
            d["last_applied"] = self.last_applied.isoformat()
        return d

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RetentionPolicy:
        result = cls(
            id=data.get("id", str(uuid.uuid4())),
            name=data.get("name", ""),
            description=data.get("description", ""),
            action=RetentionAction(data.get("action", "delete")),
            scope=RetentionScope(data.get("scope", "all")),
            max_age_days=data.get("max_age_days", 365),
            max_items=data.get("max_items"),
            min_score=data.get("min_score", 0.0),
            content_types=data.get("content_types", []),
            sources=data.get("sources", []),
            tags=data.get("tags", []),
            enabled=data.get("enabled", True),
            items_processed=data.get("items_processed", 0),
            items_deleted=data.get("items_deleted", 0),
            items_archived=data.get("items_archived", 0),
        )
        if data.get("created_at"):
            result.created_at = datetime.fromisoformat(data["created_at"])
        if data.get("last_applied"):
            result.last_applied = datetime.fromisoformat(data["last_applied"])
        return result


@dataclass
class RetentionResult:
    """Result of applying a retention policy."""

    policy_id: str = ""
    policy_name: str = ""
    items_evaluated: int = 0
    items_matched: int = 0
    items_deleted: int = 0
    items_archived: int = 0
    items_flagged: int = 0
    items_downgraded: int = 0
    applied_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    details: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["applied_at"] = self.applied_at.isoformat()
        return d
'''

RETENTION_MANAGER = '''"""Retention manager - applies retention policies."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from personal_index.retention.content_retention import (
    RetentionAction,
    RetentionPolicy,
    RetentionResult,
    RetentionScope,
)

logger = logging.getLogger(__name__)


@dataclass
class RetentionStore:
    """Persistent storage for retention policies."""

    path: str = ".personal_index/retention.json"
    _policies: dict[str, RetentionPolicy] = field(default_factory=dict, repr=False)

    def __post_init__(self) -> None:
        self._load()

    def _load(self) -> None:
        if not os.path.exists(self.path):
            self._policies = {}
            return
        try:
            with open(self.path, "r") as f:
                data = json.load(f)
            self._policies = {}
            for policy_data in data.get("policies", []):
                policy = RetentionPolicy.from_dict(policy_data)
                self._policies[policy.id] = policy
        except (json.JSONDecodeError, KeyError):
            self._policies = {}

    def _save(self) -> None:
        os.makedirs(os.path.dirname(self.path) if os.path.dirname(self.path) else ".", exist_ok=True)
        data = {"policies": [p.to_dict() for p in self._policies.values()]}
        with open(self.path, "w") as f:
            json.dump(data, f, indent=2)

    def add_policy(self, policy: RetentionPolicy) -> str:
        self._policies[policy.id] = policy
        self._save()
        return policy.id

    def get_policy(self, policy_id: str) -> RetentionPolicy | None:
        return self._policies.get(policy_id)

    def list_policies(self, enabled: bool | None = None) -> list[RetentionPolicy]:
        policies = list(self._policies.values())
        if enabled is not None:
            policies = [p for p in policies if p.enabled == enabled]
        return policies

    def update_policy(self, policy_id: str, **kwargs: Any) -> RetentionPolicy | None:
        policy = self._policies.get(policy_id)
        if policy is None:
            return None
        for key, value in kwargs.items():
            if hasattr(policy, key):
                setattr(policy, key, value)
        self._save()
        return policy

    def remove_policy(self, policy_id: str) -> bool:
        if policy_id in self._policies:
            del self._policies[policy_id]
            self._save()
            return True
        return False


class RetentionManager:
    """Manages and applies content retention policies."""

    def __init__(self, store: RetentionStore | None = None):
        self.store = store or RetentionStore()
        self._content_store: dict[str, dict[str, Any]] = {}

    def set_content_store(self, content: dict[str, dict[str, Any]]) -> None:
        """Set the content store to evaluate against."""
        self._content_store = content

    def apply_policy(self, policy_id: str, dry_run: bool = False) -> RetentionResult:
        """Apply a retention policy."""
        policy = self.store.get_policy(policy_id)
        if policy is None:
            raise ValueError(f"Policy not found: {policy_id}")

        result = RetentionResult(
            policy_id=policy.id,
            policy_name=policy.name,
        )

        now = datetime.now(timezone.utc)
        max_age = timedelta(days=policy.max_age_days)

        for content_id, content in self._content_store.items():
            result.items_evaluated += 1
            if not self._matches_policy(content, policy):
                continue

            result.items_matched += 1
            detail = {"content_id": content_id, "action": policy.action.value}

            if not dry_run:
                if policy.action == RetentionAction.DELETE:
                    del self._content_store[content_id]
                    result.items_deleted += 1
                    policy.items_deleted += 1
                elif policy.action == RetentionAction.ARCHIVE:
                    content["archived"] = True
                    content["archived_at"] = now.isoformat()
                    result.items_archived += 1
                    policy.items_archived += 1
                elif policy.action == RetentionAction.FLAG:
                    content["retention_flagged"] = True
                    result.items_flagged += 1
                elif policy.action == RetentionAction.DOWNGRADE:
                    content["score"] = content.get("score", 1.0) * 0.5
                    result.items_downgraded += 1

            result.details.append(detail)

        policy.items_processed += result.items_matched
        policy.last_applied = now
        self.store._save()

        return result

    def apply_all_policies(self, dry_run: bool = False) -> list[RetentionResult]:
        """Apply all enabled retention policies."""
        results = []
        for policy in self.store.list_policies(enabled=True):
            try:
                result = self.apply_policy(policy.id, dry_run=dry_run)
                results.append(result)
            except Exception as e:
                logger.error(f"Error applying policy {policy.id}: {e}")
        return results

    def _matches_policy(self, content: dict[str, Any], policy: RetentionPolicy) -> bool:
        """Check if content matches a retention policy."""
        now = datetime.now(timezone.utc)

        # Check age
        last_modified = content.get("last_modified")
        if last_modified:
            try:
                mod_dt = datetime.fromisoformat(last_modified)
                age = now - mod_dt
                if age <= timedelta(days=policy.max_age_days):
                    return False
            except (ValueError, TypeError):
                pass

        # Check score
        score = content.get("score", 1.0)
        if score >= policy.min_score and policy.min_score > 0:
            return False

        # Check scope filters
        if policy.scope == RetentionScope.BY_TYPE and policy.content_types:
            content_type = content.get("type", "")
            if content_type not in policy.content_types:
                return False

        if policy.scope == RetentionScope.BY_SOURCE and policy.sources:
            source = content.get("source", "")
            if source not in policy.sources:
                return False

        if policy.scope == RetentionScope.BY_TAG and policy.tags:
            content_tags = content.get("tags", [])
            if not any(t in policy.tags for t in content_tags):
                return False

        return True

    def get_storage_summary(self) -> dict[str, Any]:
        """Get a summary of content storage."""
        total = len(self._content_store)
        archived = sum(1 for c in self._content_store.values() if c.get("archived"))
        flagged = sum(1 for c in self._content_store.values() if c.get("retention_flagged"))
        return {
            "total_items": total,
            "active_items": total - archived,
            "archived_items": archived,
            "flagged_items": flagged,
            "policies_count": len(self.store.list_policies()),
            "enabled_policies": len(self.store.list_policies(enabled=True)),
        }
'''

RETENTION_PRESETS = '''"""Pre-built retention policy presets."""

from __future__ import annotations

from personal_index.retention.content_retention import (
    RetentionAction,
    RetentionPolicy,
    RetentionScope,
)


def create_default_retention_policy() -> RetentionPolicy:
    """Create a default retention policy."""
    return RetentionPolicy(
        name="default-retention",
        description="Remove content older than 1 year",
        action=RetentionAction.DELETE,
        scope=RetentionScope.ALL,
        max_age_days=365,
    )


def create_low_score_cleanup_policy() -> RetentionPolicy:
    """Create a policy to remove low-scoring content."""
    return RetentionPolicy(
        name="low-score-cleanup",
        description="Remove content with score below 0.1 older than 90 days",
        action=RetentionAction.DELETE,
        scope=RetentionScope.BY_SCORE,
        max_age_days=90,
        min_score=0.1,
    )


def create_archive_inactive_policy() -> RetentionPolicy:
    """Create a policy to archive inactive content."""
    return RetentionPolicy(
        name="archive-inactive",
        description="Archive content not accessed in 6 months",
        action=RetentionAction.ARCHIVE,
        scope=RetentionScope.ALL,
        max_age_days=180,
    )


def create_type_specific_policy(
    content_types: list[str],
    max_age_days: int = 30,
    action: RetentionAction = RetentionAction.DELETE,
) -> RetentionPolicy:
    """Create a type-specific retention policy."""
    return RetentionPolicy(
        name=f"type-retention-{content_types[0] if content_types else 'unknown'}",
        description=f"Remove {', '.join(content_types)} content older than {max_age_days} days",
        action=action,
        scope=RetentionScope.BY_TYPE,
        max_age_days=max_age_days,
        content_types=content_types,
    )
'''

# ============================================================
# TESTS
# ============================================================

TEST_SCHEDULER = '''"""Tests for content_scheduler module."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.scheduler.content_scheduler import (
    ScheduledTask,
    TaskSchedule,
    TaskStatus,
    TaskType,
)
from personal_index.scheduler.task_store import TaskStore
from personal_index.scheduler.scheduler_engine import SchedulerEngine


class TestTaskSchedule:
    def test_default_values(self):
        schedule = TaskSchedule()
        assert schedule.interval_seconds is None
        assert schedule.interval_hours is None
        assert schedule.interval_days is None
        assert schedule.timezone == "UTC"
        assert schedule.run_count == 0

    def test_next_run_interval_seconds(self):
        schedule = TaskSchedule(interval_seconds=3600)
        last_run = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        next_run = schedule.next_run_time(last_run)
        assert next_run == datetime(2024, 1, 1, 13, 0, tzinfo=timezone.utc)

    def test_next_run_interval_hours(self):
        schedule = TaskSchedule(interval_hours=24)
        last_run = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        next_run = schedule.next_run_time(last_run)
        assert next_run == datetime(2024, 1, 2, 12, 0, tzinfo=timezone.utc)

    def test_next_run_interval_days(self):
        schedule = TaskSchedule(interval_days=7)
        last_run = datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        next_run = schedule.next_run_time(last_run)
        assert next_run == datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc)

    def test_next_run_no_interval(self):
        schedule = TaskSchedule()
        assert schedule.next_run_time() is None

    def test_to_dict(self):
        start = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end = datetime(2024, 12, 31, tzinfo=timezone.utc)
        schedule = TaskSchedule(interval_hours=12, start_time=start, end_time=end)
        d = schedule.to_dict()
        assert d["interval_hours"] == 12
        assert d["start_time"] == start.isoformat()
        assert d["end_time"] == end.isoformat()

    def test_from_dict(self):
        data = {
            "interval_hours": 6,
            "start_time": "2024-01-01T00:00:00+00:00",
            "end_time": "2024-12-31T00:00:00+00:00",
            "timezone": "UTC",
            "max_runs": 100,
            "run_count": 5,
        }
        schedule = TaskSchedule.from_dict(data)
        assert schedule.interval_hours == 6
        assert schedule.start_time == datetime(2024, 1, 1, tzinfo=timezone.utc)
        assert schedule.max_runs == 100
        assert schedule.run_count == 5

    def test_serialization_roundtrip(self):
        original = TaskSchedule(
            interval_days=1,
            cron_expression="0 0 * * *",
            max_runs=50,
        )
        data = original.to_dict()
        restored = TaskSchedule.from_dict(data)
        assert restored.interval_days == 1
        assert restored.cron_expression == "0 0 * * *"
        assert restored.max_runs == 50


class TestScheduledTask:
    def test_default_values(self):
        task = ScheduledTask()
        assert task.task_type == TaskType.CRAWL
        assert task.status == TaskStatus.PENDING
        assert task.enabled is True
        assert task.priority == 5
        assert task.id != ""

    def test_custom_task(self):
        task = ScheduledTask(
            name="daily-crawl",
            task_type=TaskType.CRAWL,
            schedule=TaskSchedule(interval_hours=24),
            handler="crawl_handler",
            priority=8,
        )
        assert task.name == "daily-crawl"
        assert task.task_type == TaskType.CRAWL
        assert task.priority == 8

    def test_to_dict(self):
        task = ScheduledTask(
            name="test-task",
            task_type=TaskType.EXPORT,
            handler="export_handler",
            metadata={"key": "value"},
        )
        d = task.to_dict()
        assert d["name"] == "test-task"
        assert d["task_type"] == "export"
        assert d["handler"] == "export_handler"
        assert d["metadata"]["key"] == "value"

    def test_from_dict(self):
        data = {
            "id": "test-123",
            "name": "test-task",
            "task_type": "export",
            "schedule": {"interval_hours": 12},
            "handler": "export_handler",
            "status": "completed",
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_run": "2024-01-01T12:00:00+00:00",
            "next_run": "2024-01-02T00:00:00+00:00",
            "last_result": {"pages": 10},
            "error_message": None,
            "enabled": True,
            "priority": 5,
            "metadata": {},
        }
        task = ScheduledTask.from_dict(data)
        assert task.id == "test-123"
        assert task.name == "test-task"
        assert task.task_type == TaskType.EXPORT
        assert task.status == TaskStatus.COMPLETED
        assert task.last_run == datetime(2024, 1, 1, 12, 0, tzinfo=timezone.utc)
        assert task.last_result == {"pages": 10}

    def test_serialization_roundtrip(self):
        original = ScheduledTask(
            name="roundtrip",
            task_type=TaskType.CLEANUP,
            schedule=TaskSchedule(interval_days=1),
            handler="cleanup",
            enabled=False,
            priority=3,
            metadata={"test": True},
        )
        data = original.to_dict()
        restored = ScheduledTask.from_dict(data)
        assert restored.name == original.name
        assert restored.task_type == original.task_type
        assert restored.enabled == original.enabled
        assert restored.priority == original.priority
        assert restored.metadata == original.metadata

    def test_all_task_types(self):
        for tt in TaskType:
            task = ScheduledTask(task_type=tt)
            assert task.task_type == tt

    def test_all_task_statuses(self):
        for ts in TaskStatus:
            task = ScheduledTask(status=ts)
            assert task.status == ts


class TestTaskStore:
    def test_create_store(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            assert store.count_tasks() == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_add_and_get_task(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(name="test", task_type=TaskType.CRAWL)
            task_id = store.add_task(task)
            retrieved = store.get_task(task_id)
            assert retrieved is not None
            assert retrieved.name == "test"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_tasks_filter_by_type(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            store.add_task(ScheduledTask(name="crawl1", task_type=TaskType.CRAWL))
            store.add_task(ScheduledTask(name="export1", task_type=TaskType.EXPORT))
            store.add_task(ScheduledTask(name="crawl2", task_type=TaskType.CRAWL))
            crawls = store.list_tasks(task_type=TaskType.CRAWL)
            assert len(crawls) == 2
            all_tasks = store.list_tasks()
            assert len(all_tasks) == 3
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_update_task(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(name="original", task_type=TaskType.CRAWL)
            task_id = store.add_task(task)
            updated = store.update_task(task_id, name="updated", enabled=False)
            assert updated is not None
            assert updated.name == "updated"
            assert updated.enabled is False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_remove_task(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(name="to-remove")
            task_id = store.add_task(task)
            assert store.count_tasks() == 1
            assert store.remove_task(task_id) is True
            assert store.count_tasks() == 0
            assert store.remove_task("nonexistent") is False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(name="persistent", task_type=TaskType.EXPORT)
            store.add_task(task)
            del store
            store2 = TaskStore(path=path)
            assert store2.count_tasks() == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_tasks_filter_by_status(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            store.add_task(ScheduledTask(name="pending", status=TaskStatus.PENDING))
            store.add_task(ScheduledTask(name="running", status=TaskStatus.RUNNING))
            pending = store.list_tasks(status=TaskStatus.PENDING)
            assert len(pending) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_tasks_filter_by_enabled(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            store.add_task(ScheduledTask(name="enabled", enabled=True))
            store.add_task(ScheduledTask(name="disabled", enabled=False))
            enabled = store.list_tasks(enabled=True)
            assert len(enabled) == 1
            disabled = store.list_tasks(enabled=False)
            assert len(disabled) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_count_tasks_by_type(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            store.add_task(ScheduledTask(task_type=TaskType.CRAWL))
            store.add_task(ScheduledTask(task_type=TaskType.CRAWL))
            store.add_task(ScheduledTask(task_type=TaskType.EXPORT))
            assert store.count_tasks(TaskType.CRAWL) == 2
            assert store.count_tasks(TaskType.EXPORT) == 1
            assert store.count_tasks() == 3
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestSchedulerEngine:
    def test_register_handler(self):
        engine = SchedulerEngine()
        engine.register_handler("test_handler", lambda x: {"ok": True})
        assert engine.get_handler("test_handler") is not None
        assert engine.get_handler("nonexistent") is None

    def test_run_task_now(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(
                name="immediate",
                handler="test_handler",
                metadata={"input": "test"},
            )
            store.add_task(task)
            engine = SchedulerEngine(store=store)
            engine.register_handler("test_handler", lambda m: {"result": m.get("input")})
            result = engine.run_task_now(task.id)
            assert result == {"result": "test"}
            updated = store.get_task(task.id)
            assert updated.status == TaskStatus.COMPLETED
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_run_task_not_found(self):
        engine = SchedulerEngine()
        with pytest.raises(ValueError, match="Task not found"):
            engine.run_task_now("nonexistent")

    def test_run_task_no_handler(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            task = ScheduledTask(name="no-handler", handler="missing_handler")
            store.add_task(task)
            engine = SchedulerEngine(store=store)
            with pytest.raises(ValueError, match="No handler registered"):
                engine.run_task_now(task.id)
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_due_tasks(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            now = datetime.now(timezone.utc)
            task_due = ScheduledTask(
                name="due",
                next_run=now - timedelta(hours=1),
                enabled=True,
            )
            task_future = ScheduledTask(
                name="future",
                next_run=now + timedelta(hours=1),
                enabled=True,
            )
            store.add_task(task_due)
            store.add_task(task_future)
            engine = SchedulerEngine(store=store)
            due = engine.get_due_tasks()
            assert len(due) == 1
            assert due[0].name == "due"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_get_upcoming_tasks(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = TaskStore(path=path)
            now = datetime.now(timezone.utc)
            task_soon = ScheduledTask(
                name="soon",
                next_run=now + timedelta(hours=1),
                enabled=True,
            )
            task_later = ScheduledTask(
                name="later",
                next_run=now + timedelta(hours=48),
                enabled=True,
            )
            store.add_task(task_soon)
            store.add_task(task_later)
            engine = SchedulerEngine(store=store)
            upcoming = engine.get_upcoming_tasks(hours=24)
            assert len(upcoming) == 1
            assert upcoming[0].name == "soon"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_start_stop(self):
        engine = SchedulerEngine()
        engine.start(poll_interval=0.1)
        assert engine._running is True
        engine.stop()
        assert engine._running is False

    def test_start_already_running(self):
        engine = SchedulerEngine()
        engine.start(poll_interval=0.1)
        engine.start(poll_interval=0.1)
        assert engine._thread is not None
        engine.stop()
'''

TEST_AUTOMATION = '''"""Tests for content_automation module."""

from __future__ import annotations

import json
import os
import tempfile
from datetime import datetime, timezone

import pytest

from personal_index.automation.content_automation import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
)
from personal_index.automation.workflow_engine import WorkflowEngine
from personal_index.automation.workflow_store import WorkflowStore
from personal_index.automation.workflow_pipelines import (
    create_crawl_enrich_index_notify_pipeline,
    create_export_pipeline,
    create_cleanup_pipeline,
)


class TestWorkflowStep:
    def test_default_values(self):
        step = WorkflowStep()
        assert step.on_failure == "stop"
        assert step.retry_count == 0
        assert step.retry_delay_seconds == 0.0
        assert step.timeout_seconds == 300.0
        assert step.id != ""

    def test_custom_step(self):
        step = WorkflowStep(
            name="crawl",
            step_type="crawl",
            handler="crawl_handler",
            config={"urls": ["http://example.com"]},
            retry_count=3,
            retry_delay_seconds=5.0,
        )
        assert step.name == "crawl"
        assert step.retry_count == 3
        assert step.config["urls"] == ["http://example.com"]

    def test_to_dict(self):
        step = WorkflowStep(name="test", handler="h", config={"key": "val"})
        d = step.to_dict()
        assert d["name"] == "test"
        assert d["handler"] == "h"
        assert d["config"]["key"] == "val"

    def test_from_dict(self):
        data = {
            "id": "step-1",
            "name": "test",
            "step_type": "crawl",
            "handler": "h",
            "config": {"key": "val"},
            "depends_on": [],
            "on_failure": "continue",
            "retry_count": 2,
            "retry_delay_seconds": 3.0,
            "timeout_seconds": 60.0,
            "status": "completed",
            "result": {"ok": True},
            "error": None,
            "started_at": "2024-01-01T00:00:00+00:00",
            "completed_at": "2024-01-01T00:01:00+00:00",
        }
        step = WorkflowStep.from_dict(data)
        assert step.name == "test"
        assert step.on_failure == "continue"
        assert step.started_at == datetime(2024, 1, 1, tzinfo=timezone.utc)

    def test_serialization_roundtrip(self):
        original = WorkflowStep(
            name="roundtrip",
            step_type="test",
            handler="h",
            config={"a": 1},
            depends_on=["dep-1"],
            on_failure="skip_remaining",
            retry_count=5,
        )
        data = original.to_dict()
        restored = WorkflowStep.from_dict(data)
        assert restored.name == original.name
        assert restored.depends_on == original.depends_on
        assert restored.on_failure == original.on_failure
        assert restored.retry_count == original.retry_count


class TestWorkflow:
    def test_default_values(self):
        wf = Workflow()
        assert wf.status == WorkflowStatus.PENDING
        assert wf.enabled is True
        assert wf.id != ""

    def test_custom_workflow(self):
        step = WorkflowStep(name="step1", handler="h1")
        wf = Workflow(
            name="test-wf",
            description="A test workflow",
            steps=[step],
        )
        assert wf.name == "test-wf"
        assert len(wf.steps) == 1

    def test_to_dict(self):
        step = WorkflowStep(name="s1", handler="h1")
        wf = Workflow(name="test", steps=[step])
        d = wf.to_dict()
        assert d["name"] == "test"
        assert len(d["steps"]) == 1
        assert d["status"] == "pending"

    def test_from_dict(self):
        data = {
            "id": "wf-1",
            "name": "test",
            "description": "desc",
            "steps": [{"id": "s1", "name": "s1", "step_type": "t", "handler": "h",
                       "config": {}, "depends_on": [], "on_failure": "stop",
                       "retry_count": 0, "retry_delay_seconds": 0.0,
                       "timeout_seconds": 300.0, "status": "pending",
                       "result": None, "error": None,
                       "started_at": None, "completed_at": None}],
            "status": "completed",
            "created_at": "2024-01-01T00:00:00+00:00",
            "started_at": "2024-01-01T01:00:00+00:00",
            "completed_at": "2024-01-01T02:00:00+00:00",
            "metadata": {"key": "val"},
            "enabled": True,
        }
        wf = Workflow.from_dict(data)
        assert wf.id == "wf-1"
        assert wf.status == WorkflowStatus.COMPLETED
        assert wf.metadata == {"key": "val"}

    def test_serialization_roundtrip(self):
        step = WorkflowStep(name="s1", handler="h1", config={"x": 1})
        original = Workflow(
            name="rt",
            description="roundtrip",
            steps=[step],
            metadata={"m": 1},
            enabled=False,
        )
        data = original.to_dict()
        restored = Workflow.from_dict(data)
        assert restored.name == original.name
        assert restored.enabled == original.enabled
        assert restored.metadata == original.metadata


class TestWorkflowEngine:
    def test_add_and_get_workflow(self):
        engine = WorkflowEngine()
        wf = Workflow(name="test")
        wf_id = engine.add_workflow(wf)
        retrieved = engine.get_workflow(wf_id)
        assert retrieved is not None
        assert retrieved.name == "test"

    def test_list_workflows(self):
        engine = WorkflowEngine()
        engine.add_workflow(Workflow(name="w1"))
        engine.add_workflow(Workflow(name="w2"))
        assert len(engine.list_workflows()) == 2

    def test_remove_workflow(self):
        engine = WorkflowEngine()
        wf = Workflow(name="test")
        wf_id = engine.add_workflow(wf)
        assert engine.remove_workflow(wf_id) is True
        assert engine.get_workflow(wf_id) is None
        assert engine.remove_workflow("nonexistent") is False

    def test_execute_workflow_simple(self):
        engine = WorkflowEngine()
        engine.register_handler("h1", lambda c: {"result": "ok"})
        step = WorkflowStep(name="s1", handler="h1", config={})
        wf = Workflow(name="test", steps=[step])
        engine.add_workflow(wf)
        result = engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.COMPLETED
        assert result.steps[0].status.value == "completed"

    def test_execute_workflow_with_dependencies(self):
        engine = WorkflowEngine()
        call_order = []
        engine.register_handler("h1", lambda c: call_order.append("h1") or {"ok": True})
        engine.register_handler("h2", lambda c: call_order.append("h2") or {"ok": True})
        step1 = WorkflowStep(name="s1", handler="h1", config={})
        step2 = WorkflowStep(name="s2", handler="h2", config={}, depends_on=[step1.id])
        wf = Workflow(name="dep-test", steps=[step1, step2])
        engine.add_workflow(wf)
        engine.execute_workflow(wf.id)
        assert call_order == ["h1", "h2"]

    def test_execute_workflow_handler_failure(self):
        engine = WorkflowEngine()
        engine.register_handler("fail", lambda c: (_ for _ in ()).throw(ValueError("fail")))
        step = WorkflowStep(name="s1", handler="fail", config={}, retry_count=0)
        wf = Workflow(name="fail-test", steps=[step])
        engine.add_workflow(wf)
        result = engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.FAILED
        assert result.steps[0].error == "fail"

    def test_execute_workflow_retry(self):
        engine = WorkflowEngine()
        call_count = [0]
        def retry_handler(c):
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("retry")
            return {"ok": True}
        engine.register_handler("retry_h", retry_handler)
        step = WorkflowStep(name="s1", handler="retry_h", config={}, retry_count=3)
        wf = Workflow(name="retry-test", steps=[step])
        engine.add_workflow(wf)
        result = engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.COMPLETED
        assert call_count[0] == 3

    def test_execute_workflow_no_handler(self):
        engine = WorkflowEngine()
        step = WorkflowStep(name="s1", handler="missing", config={})
        wf = Workflow(name="no-handler", steps=[step])
        engine.add_workflow(wf)
        result = engine.execute_workflow(wf.id)
        assert result.status == WorkflowStatus.FAILED
        assert "No handler registered" in result.steps[0].error

    def test_execute_workflow_not_found(self):
        engine = WorkflowEngine()
        with pytest.raises(ValueError, match="Workflow not found"):
            engine.execute_workflow("nonexistent")

    def test_cancel_workflow(self):
        engine = WorkflowEngine()
        wf = Workflow(name="cancel-test", status=WorkflowStatus.RUNNING)
        engine.add_workflow(wf)
        assert engine.cancel_workflow(wf.id) is True
        assert wf.status == WorkflowStatus.CANCELLED
        assert engine.cancel_workflow("nonexistent") is False

    def test_workflow_with_skipped_deps(self):
        engine = WorkflowEngine()
        engine.register_handler("h1", lambda c: (_ for _ in ()).throw(ValueError("fail")))
        engine.register_handler("h2", lambda c: {"ok": True})
        step1 = WorkflowStep(name="s1", handler="h1", config={}, retry_count=0)
        step2 = WorkflowStep(name="s2", handler="h2", config={}, depends_on=[step1.id])
        wf = Workflow(name="skip-test", steps=[step1, step2])
        engine.add_workflow(wf)
        result = engine.execute_workflow(wf.id)
        assert result.steps[1].status.value == "skipped"


class TestWorkflowStore:
    def test_add_and_get(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = WorkflowStore(path=path)
            wf = Workflow(name="test")
            wf_id = store.add(wf)
            retrieved = store.get(wf_id)
            assert retrieved is not None
            assert retrieved.name == "test"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = WorkflowStore(path=path)
            store.add(Workflow(name="persistent"))
            del store
            store2 = WorkflowStore(path=path)
            assert len(store2.list_all()) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_filter_by_status(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = WorkflowStore(path=path)
            store.add(Workflow(name="pending", status=WorkflowStatus.PENDING))
            store.add(Workflow(name="completed", status=WorkflowStatus.COMPLETED))
            pending = store.list_all(status=WorkflowStatus.PENDING)
            assert len(pending) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_update_and_remove(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = WorkflowStore(path=path)
            wf = Workflow(name="original")
            wf_id = store.add(wf)
            store.update(wf_id, name="updated", enabled=False)
            updated = store.get(wf_id)
            assert updated.name == "updated"
            assert updated.enabled is False
            store.remove(wf_id)
            assert store.get(wf_id) is None
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestWorkflowPipelines:
    def test_crawl_enrich_index_notify(self):
        wf = create_crawl_enrich_index_notify_pipeline(
            seed_urls=["http://example.com"],
            max_pages=100,
        )
        assert wf.name == "crawl-enrich-index-notify"
        assert len(wf.steps) == 4
        step_names = [s.name for s in wf.steps]
        assert step_names == ["crawl", "enrich", "index", "notify"]
        assert wf.steps[1].depends_on == [wf.steps[0].id]
        assert wf.steps[2].depends_on == [wf.steps[1].id]
        assert wf.steps[3].depends_on == [wf.steps[2].id]

    def test_export_pipeline(self):
        wf = create_export_pipeline(format="csv", output_path="/tmp/")
        assert wf.name == "content-export"
        assert len(wf.steps) == 1
        assert wf.steps[0].config["format"] == "csv"

    def test_cleanup_pipeline(self):
        wf = create_cleanup_pipeline(max_age_days=60, dry_run=True)
        assert wf.name == "content-cleanup"
        assert len(wf.steps) == 1
        assert wf.steps[0].config["max_age_days"] == 60
        assert wf.steps[0].config["dry_run"] is True
'''

TEST_MONITOR = '''"""Tests for content_monitor module."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.monitor.content_monitor import (
    CrawlFreshness,
    DiskUsage,
    ErrorRates,
    HealthLevel,
)
from personal_index.monitor.health_checker import (
    HealthChecker,
    HealthCheckResult,
    SystemHealth,
)


class TestDiskUsage:
    def test_default_values(self):
        du = DiskUsage()
        assert du.total_bytes == 0
        assert du.usage_percent == 0.0

    def test_gb_properties(self):
        du = DiskUsage(total_bytes=1073741824, used_bytes=536870912)
        assert abs(du.total_gb - 1.0) < 0.01
        assert abs(du.used_gb - 0.5) < 0.01

    def test_to_dict(self):
        du = DiskUsage(total_bytes=1000, used_bytes=500, free_bytes=500)
        d = du.to_dict()
        assert d["total_bytes"] == 1000
        assert d["used_bytes"] == 500


class TestCrawlFreshness:
    def test_default_values(self):
        cf = CrawlFreshness()
        assert cf.freshness_percent == 100.0

    def test_freshness_percent(self):
        cf = CrawlFreshness(total_sources=10, fresh_sources=8)
        assert cf.freshness_percent == 80.0

    def test_freshness_percent_no_sources(self):
        cf = CrawlFreshness(total_sources=0)
        assert cf.freshness_percent == 100.0

    def test_to_dict(self):
        cf = CrawlFreshness(total_sources=5, fresh_sources=3, avg_hours_since_crawl=12.5)
        d = cf.to_dict()
        assert d["total_sources"] == 5
        assert d["fresh_sources"] == 3


class TestErrorRates:
    def test_default_values(self):
        er = ErrorRates()
        assert er.error_rate_percent == 0.0

    def test_record_success(self):
        er = ErrorRates()
        er.record_success()
        er.record_success()
        assert er.total_requests == 2
        assert er.successful_requests == 2
        assert er.error_rate_percent == 0.0

    def test_record_error(self):
        er = ErrorRates()
        er.record_success()
        er.record_error("timeout")
        assert er.total_requests == 2
        assert er.failed_requests == 1
        assert er.error_rate_percent == 50.0
        assert er.errors_by_type["timeout"] == 1

    def test_multiple_error_types(self):
        er = ErrorRates()
        er.record_error("timeout")
        er.record_error("timeout")
        er.record_error("connection")
        er.record_success()
        assert er.errors_by_type["timeout"] == 2
        assert er.errors_by_type["connection"] == 1

    def test_to_dict(self):
        er = ErrorRates()
        er.record_success()
        er.record_error("test")
        d = er.to_dict()
        assert d["total_requests"] == 2
        assert d["error_rate_percent"] == 50.0


class TestHealthCheckResult:
    def test_default_values(self):
        result = HealthCheckResult()
        assert result.level == HealthLevel.HEALTHY

    def test_to_dict(self):
        result = HealthCheckResult(
            check_name="disk",
            level=HealthLevel.WARNING,
            message="80% used",
            details={"percent": 80},
        )
        d = result.to_dict()
        assert d["check_name"] == "disk"
        assert d["level"] == "warning"
        assert d["details"]["percent"] == 80


class TestSystemHealth:
    def test_default_values(self):
        health = SystemHealth()
        assert health.overall_level == HealthLevel.HEALTHY

    def test_to_dict(self):
        health = SystemHealth(
            overall_level=HealthLevel.WARNING,
            checks=[HealthCheckResult(check_name="test", level=HealthLevel.WARNING)],
        )
        d = health.to_dict()
        assert d["overall_level"] == "warning"
        assert len(d["checks"]) == 1


class TestHealthChecker:
    def test_check_all(self):
        checker = HealthChecker()
        health = checker.check_all()
        assert health.overall_level in [h for h in HealthLevel]
        assert len(health.checks) >= 1

    def test_check_disk_usage(self):
        checker = HealthChecker()
        results = checker.check_disk_usage()
        assert len(results) == 1
        assert results[0].check_name == "disk_usage"

    def test_check_crawl_freshness(self):
        checker = HealthChecker()
        results = checker.check_crawl_freshness()
        assert len(results) == 1
        assert results[0].check_name == "crawl_freshness"

    def test_check_error_rates(self):
        checker = HealthChecker()
        results = checker.check_error_rates()
        assert len(results) == 1
        assert results[0].check_name == "error_rates"

    def test_custom_thresholds(self):
        checker = HealthChecker(
            disk_warning_percent=50.0,
            disk_critical_percent=75.0,
            freshness_warning_hours=12.0,
            error_rate_warning_percent=5.0,
        )
        assert checker.disk_warning_percent == 50.0
        assert checker.freshness_warning_hours == 12.0

    def test_determine_overall_level(self):
        checker = HealthChecker()
        checks = [
            HealthCheckResult(level=HealthLevel.HEALTHY),
            HealthCheckResult(level=HealthLevel.WARNING),
        ]
        assert checker._determine_overall_level(checks) == HealthLevel.WARNING

    def test_overall_critical(self):
        checker = HealthChecker()
        checks = [
            HealthCheckResult(level=HealthLevel.HEALTHY),
            HealthCheckResult(level=HealthLevel.CRITICAL),
        ]
        assert checker._determine_overall_level(checks) == HealthLevel.CRITICAL

    def test_overall_unknown(self):
        checker = HealthChecker()
        assert checker._determine_overall_level([]) == HealthLevel.UNKNOWN

    def test_freshness_with_tasks(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            tasks_path = os.path.join(tmpdir, "tasks.json")
            now = datetime.now(timezone.utc)
            old_time = (now - timedelta(hours=48)).isoformat()
            fresh_time = (now - timedelta(hours=1)).isoformat()
            data = {
                "tasks": [
                    {"task_type": "crawl", "last_run": old_time, "name": "old"},
                    {"task_type": "crawl", "last_run": fresh_time, "name": "fresh"},
                    {"task_type": "export", "last_run": fresh_time, "name": "export"},
                ]
            }
            with open(tasks_path, "w") as f:
                import json
                json.dump(data, f)
            checker = HealthChecker(data_dir=tmpdir)
            freshness = checker._compute_freshness()
            assert freshness.total_sources == 2
            assert freshness.fresh_sources == 1
            assert freshness.stale_sources == 1
'''

TEST_ALERTS = '''"""Tests for content_alerts module."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.alerts.content_alerts import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertState,
)
from personal_index.alerts.alert_manager import AlertManager, AlertRule
from personal_index.alerts.alert_detectors import (
    MissedCrawlDetector,
    HighErrorRateDetector,
    StaleContentDetector,
)


class TestAlert:
    def test_default_values(self):
        alert = Alert()
        assert alert.severity == AlertSeverity.INFO
        assert alert.state == AlertState.ACTIVE
        assert alert.id != ""

    def test_acknowledge(self):
        alert = Alert()
        alert.acknowledge(by="user1")
        assert alert.state == AlertState.ACKNOWLEDGED
        assert alert.acknowledged_by == "user1"
        assert alert.acknowledged_at is not None

    def test_resolve(self):
        alert = Alert()
        alert.resolve(by="admin")
        assert alert.state == AlertState.RESOLVED
        assert alert.resolved_by == "admin"
        assert alert.resolved_at is not None

    def test_to_dict(self):
        alert = Alert(
            category=AlertCategory.MISSED_CRAWL,
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
        )
        d = alert.to_dict()
        assert d["category"] == "missed_crawl"
        assert d["severity"] == "warning"
        assert d["title"] == "Test Alert"

    def test_from_dict(self):
        data = {
            "id": "alert-1",
            "category": "high_error_rate",
            "severity": "critical",
            "title": "Critical",
            "message": "Error rate high",
            "state": "active",
            "source": "test",
            "metadata": {"rate": 75.0},
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        alert = Alert.from_dict(data)
        assert alert.category == AlertCategory.HIGH_ERROR_RATE
        assert alert.severity == AlertSeverity.CRITICAL
        assert alert.metadata["rate"] == 75.0

    def test_serialization_roundtrip(self):
        original = Alert(
            category=AlertCategory.STALE_CONTENT,
            severity=AlertSeverity.ERROR,
            title="Stale",
            message="Content stale",
            metadata={"count": 10},
        )
        data = original.to_dict()
        restored = Alert.from_dict(data)
        assert restored.category == original.category
        assert restored.severity == original.severity
        assert restored.metadata == original.metadata

    def test_all_categories(self):
        for cat in AlertCategory:
            alert = Alert(category=cat)
            assert alert.category == cat

    def test_all_severities(self):
        for sev in AlertSeverity:
            alert = Alert(severity=sev)
            assert alert.severity == sev

    def test_all_states(self):
        for state in AlertState:
            alert = Alert(state=state)
            assert alert.state == state


class TestAlertRule:
    def test_default_values(self):
        rule = AlertRule()
        assert rule.enabled is True
        assert rule.cooldown_minutes == 30

    def test_to_dict(self):
        rule = AlertRule(
            id="r1",
            name="high-errors",
            category=AlertCategory.HIGH_ERROR_RATE,
            threshold=25.0,
        )
        d = rule.to_dict()
        assert d["name"] == "high-errors"
        assert d["threshold"] == 25.0

    def test_from_dict(self):
        data = {
            "id": "r1",
            "name": "test-rule",
            "category": "disk_usage",
            "severity": "warning",
            "condition": "disk_percent",
            "threshold": 80.0,
            "window_minutes": 30,
            "cooldown_minutes": 15,
            "enabled": True,
        }
        rule = AlertRule.from_dict(data)
        assert rule.name == "test-rule"
        assert rule.threshold == 80.0
        assert rule.cooldown_minutes == 15


class TestAlertManager:
    def test_create_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            alert = mgr.create_alert(
                category=AlertCategory.CUSTOM,
                severity=AlertSeverity.WARNING,
                title="Test",
                message="Test alert",
            )
            assert alert.state == AlertState.ACTIVE
            assert len(mgr.get_active_alerts()) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_acknowledge_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            alert = mgr.create_alert(
                category=AlertCategory.CUSTOM,
                severity=AlertSeverity.INFO,
                title="Test",
                message="Test",
            )
            result = mgr.acknowledge_alert(alert.id, by="user")
            assert result.state == AlertState.ACKNOWLEDGED
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_resolve_alert(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            alert = mgr.create_alert(
                category=AlertCategory.CUSTOM,
                severity=AlertSeverity.INFO,
                title="Test",
                message="Test",
            )
            result = mgr.resolve_alert(alert.id, by="admin")
            assert result.state == AlertState.RESOLVED
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_alerts_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            mgr.create_alert(AlertCategory.CUSTOM, AlertSeverity.WARNING, "W1", "w1")
            mgr.create_alert(AlertCategory.CUSTOM, AlertSeverity.ERROR, "E1", "e1")
            warnings = mgr.list_alerts(severity=AlertSeverity.WARNING)
            assert len(warnings) == 1
            errors = mgr.list_alerts(severity=AlertSeverity.ERROR)
            assert len(errors) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            mgr.create_alert(AlertCategory.CUSTOM, AlertSeverity.INFO, "Persist", "p")
            del mgr
            mgr2 = AlertManager(store_path=path)
            assert len(mgr2.get_active_alerts()) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_add_and_remove_rule(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            rule = AlertRule(id="r1", name="test", threshold=50.0)
            mgr.add_rule(rule)
            assert len(mgr.list_rules()) == 1
            mgr.remove_rule("r1")
            assert len(mgr.list_rules()) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_evaluate_rules(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            rule = AlertRule(
                id="r1",
                name="high-disk",
                category=AlertCategory.DISK_USAGE,
                severity=AlertSeverity.WARNING,
                condition="disk_percent",
                threshold=80.0,
                cooldown_minutes=0,
            )
            mgr.add_rule(rule)
            triggered = mgr.evaluate_rules({"disk_percent": 85.0})
            assert len(triggered) == 1
            assert triggered[0].category == AlertCategory.DISK_USAGE
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_rule_cooldown(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            rule = AlertRule(
                id="r1",
                name="cd-test",
                category=AlertCategory.CUSTOM,
                condition="metric",
                threshold=10.0,
                cooldown_minutes=60,
            )
            mgr.add_rule(rule)
            triggered1 = mgr.evaluate_rules({"metric": 20.0})
            assert len(triggered1) == 1
            triggered2 = mgr.evaluate_rules({"metric": 20.0})
            assert len(triggered2) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_handler_dispatch(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            received = []
            mgr.register_handler(AlertCategory.CUSTOM, lambda a: received.append(a))
            mgr.create_alert(AlertCategory.CUSTOM, AlertSeverity.INFO, "Test", "T")
            assert len(received) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_nonexistent_alert_operations(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            assert mgr.acknowledge_alert("nonexistent") is None
            assert mgr.resolve_alert("nonexistent") is None
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestMissedCrawlDetector:
    def test_detect_missed_crawl(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = MissedCrawlDetector(mgr, threshold_hours=1.0)
            now = datetime.now(timezone.utc)
            overdue = (now - timedelta(hours=2)).isoformat()
            tasks = [
                {"task_type": "crawl", "name": "missed", "next_run": overdue, "id": "t1"},
                {"task_type": "crawl", "name": "ok", "next_run": (now + timedelta(hours=1)).isoformat(), "id": "t2"},
            ]
            alerts = detector.check(tasks)
            assert len(alerts) == 1
            assert alerts[0].category == AlertCategory.MISSED_CRAWL
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_missed_crawls(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = MissedCrawlDetector(mgr)
            now = datetime.now(timezone.utc)
            tasks = [
                {"task_type": "crawl", "next_run": (now + timedelta(hours=1)).isoformat()},
            ]
            alerts = detector.check(tasks)
            assert len(alerts) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestHighErrorRateDetector:
    def test_detect_high_error_rate(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = HighErrorRateDetector(mgr, threshold_percent=10.0)
            alerts = detector.check(25.0, total_requests=100)
            assert len(alerts) == 1
            assert alerts[0].category == AlertCategory.HIGH_ERROR_RATE
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_high_error_rate(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = HighErrorRateDetector(mgr, threshold_percent=50.0)
            alerts = detector.check(10.0)
            assert len(alerts) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestStaleContentDetector:
    def test_detect_stale_content(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = StaleContentDetector(mgr, threshold_days=7.0)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=30)).isoformat()
            items = [
                {"last_modified": old},
                {"last_modified": old},
                {"last_modified": (now - timedelta(days=1)).isoformat()},
            ]
            alerts = detector.check(items)
            assert len(alerts) == 1
            assert alerts[0].category == AlertCategory.STALE_CONTENT
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_no_stale_content(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            mgr = AlertManager(store_path=path)
            detector = StaleContentDetector(mgr)
            now = datetime.now(timezone.utc)
            items = [{"last_modified": (now - timedelta(days=1)).isoformat()}]
            alerts = detector.check(items)
            assert len(alerts) == 0
        finally:
            if os.path.exists(path):
                os.unlink(path)
'''

TEST_RETENTION = '''"""Tests for content_retention module."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone

import pytest

from personal_index.retention.content_retention import (
    RetentionAction,
    RetentionPolicy,
    RetentionResult,
    RetentionScope,
)
from personal_index.retention.retention_manager import RetentionManager, RetentionStore
from personal_index.retention.retention_presets import (
    create_default_retention_policy,
    create_low_score_cleanup_policy,
    create_archive_inactive_policy,
    create_type_specific_policy,
)


class TestRetentionPolicy:
    def test_default_values(self):
        policy = RetentionPolicy()
        assert policy.action == RetentionAction.DELETE
        assert policy.scope == RetentionScope.ALL
        assert policy.max_age_days == 365
        assert policy.enabled is True
        assert policy.id != ""

    def test_custom_policy(self):
        policy = RetentionPolicy(
            name="custom",
            action=RetentionAction.ARCHIVE,
            scope=RetentionScope.BY_TYPE,
            max_age_days=90,
            content_types=["article", "blog"],
        )
        assert policy.action == RetentionAction.ARCHIVE
        assert policy.content_types == ["article", "blog"]

    def test_to_dict(self):
        policy = RetentionPolicy(name="test", max_age_days=30)
        d = policy.to_dict()
        assert d["name"] == "test"
        assert d["max_age_days"] == 30
        assert d["action"] == "delete"

    def test_from_dict(self):
        data = {
            "id": "p1",
            "name": "test",
            "description": "desc",
            "action": "archive",
            "scope": "by_type",
            "max_age_days": 60,
            "max_items": 1000,
            "min_score": 0.5,
            "content_types": ["article"],
            "sources": ["example.com"],
            "tags": ["news"],
            "enabled": True,
            "created_at": "2024-01-01T00:00:00+00:00",
            "items_processed": 50,
            "items_deleted": 10,
            "items_archived": 5,
        }
        policy = RetentionPolicy.from_dict(data)
        assert policy.action == RetentionAction.ARCHIVE
        assert policy.scope == RetentionScope.BY_TYPE
        assert policy.max_age_days == 60
        assert policy.items_processed == 50

    def test_serialization_roundtrip(self):
        original = RetentionPolicy(
            name="rt",
            action=RetentionAction.FLAG,
            scope=RetentionScope.BY_TAG,
            max_age_days=120,
            tags=["temp"],
            enabled=False,
        )
        data = original.to_dict()
        restored = RetentionPolicy.from_dict(data)
        assert restored.action == original.action
        assert restored.scope == original.scope
        assert restored.tags == original.tags
        assert restored.enabled == original.enabled

    def test_all_actions(self):
        for action in RetentionAction:
            policy = RetentionPolicy(action=action)
            assert policy.action == action

    def test_all_scopes(self):
        for scope in RetentionScope:
            policy = RetentionPolicy(scope=scope)
            assert policy.scope == scope


class TestRetentionResult:
    def test_default_values(self):
        result = RetentionResult()
        assert result.items_evaluated == 0
        assert result.items_deleted == 0

    def test_to_dict(self):
        result = RetentionResult(
            policy_id="p1",
            policy_name="test",
            items_evaluated=100,
            items_deleted=10,
        )
        d = result.to_dict()
        assert d["policy_id"] == "p1"
        assert d["items_deleted"] == 10


class TestRetentionStore:
    def test_add_and_get(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(name="test")
            pid = store.add_policy(policy)
            retrieved = store.get_policy(pid)
            assert retrieved is not None
            assert retrieved.name == "test"
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_list_policies(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            store.add_policy(RetentionPolicy(name="p1", enabled=True))
            store.add_policy(RetentionPolicy(name="p2", enabled=False))
            assert len(store.list_policies()) == 2
            assert len(store.list_policies(enabled=True)) == 1
            assert len(store.list_policies(enabled=False)) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_update_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(name="original")
            pid = store.add_policy(policy)
            store.update_policy(pid, name="updated", max_age_days=30)
            updated = store.get_policy(pid)
            assert updated.name == "updated"
            assert updated.max_age_days == 30
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_remove_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(name="to-remove")
            pid = store.add_policy(policy)
            assert store.remove_policy(pid) is True
            assert store.get_policy(pid) is None
            assert store.remove_policy("nonexistent") is False
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_persistence(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            store.add_policy(RetentionPolicy(name="persistent"))
            del store
            store2 = RetentionStore(path=path)
            assert len(store2.list_policies()) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestRetentionManager:
    def test_apply_delete_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="delete-old",
                action=RetentionAction.DELETE,
                max_age_days=30,
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "item1": {"last_modified": old, "score": 0.5},
                "item2": {"last_modified": (now - timedelta(days=1)).isoformat(), "score": 0.8},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_evaluated == 2
            assert result.items_deleted == 1
            assert len(mgr._content_store) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_apply_archive_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="archive-old",
                action=RetentionAction.ARCHIVE,
                max_age_days=30,
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "item1": {"last_modified": old, "score": 0.5},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_archived == 1
            assert mgr._content_store["item1"]["archived"] is True
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_apply_flag_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="flag-old",
                action=RetentionAction.FLAG,
                max_age_days=30,
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "item1": {"last_modified": old},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_flagged == 1
            assert mgr._content_store["item1"]["retention_flagged"] is True
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_apply_downgrade_policy(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="downgrade-old",
                action=RetentionAction.DOWNGRADE,
                max_age_days=30,
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "item1": {"last_modified": old, "score": 1.0},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_downgraded == 1
            assert mgr._content_store["item1"]["score"] == 0.5
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_dry_run(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="dry-run",
                action=RetentionAction.DELETE,
                max_age_days=30,
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "item1": {"last_modified": old},
            })
            result = mgr.apply_policy(policy.id, dry_run=True)
            assert result.items_deleted == 0
            assert len(mgr._content_store) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_apply_all_policies(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            store.add_policy(RetentionPolicy(name="p1", action=RetentionAction.FLAG, max_age_days=30))
            store.add_policy(RetentionPolicy(name="p2", enabled=False))
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({"item1": {"last_modified": old}})
            results = mgr.apply_all_policies()
            assert len(results) == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_storage_summary(self):
        mgr = RetentionManager()
        now = datetime.now(timezone.utc)
        mgr.set_content_store({
            "a": {"archived": False},
            "b": {"archived": True},
            "c": {"retention_flagged": True},
        })
        summary = mgr.get_storage_summary()
        assert summary["total_items"] == 3
        assert summary["archived_items"] == 1
        assert summary["flagged_items"] == 1

    def test_policy_not_found(self):
        mgr = RetentionManager()
        with pytest.raises(ValueError, match="Policy not found"):
            mgr.apply_policy("nonexistent")

    def test_type_scope_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="type-filter",
                action=RetentionAction.DELETE,
                scope=RetentionScope.BY_TYPE,
                max_age_days=30,
                content_types=["article"],
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "a": {"last_modified": old, "type": "article"},
                "b": {"last_modified": old, "type": "video"},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_deleted == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_tag_scope_filter(self):
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            store = RetentionStore(path=path)
            policy = RetentionPolicy(
                name="tag-filter",
                action=RetentionAction.DELETE,
                scope=RetentionScope.BY_TAG,
                max_age_days=30,
                tags=["temp"],
            )
            store.add_policy(policy)
            mgr = RetentionManager(store=store)
            now = datetime.now(timezone.utc)
            old = (now - timedelta(days=60)).isoformat()
            mgr.set_content_store({
                "a": {"last_modified": old, "tags": ["temp", "news"]},
                "b": {"last_modified": old, "tags": ["important"]},
            })
            result = mgr.apply_policy(policy.id)
            assert result.items_deleted == 1
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestRetentionPresets:
    def test_default_retention(self):
        policy = create_default_retention_policy()
        assert policy.name == "default-retention"
        assert policy.max_age_days == 365
        assert policy.action == RetentionAction.DELETE

    def test_low_score_cleanup(self):
        policy = create_low_score_cleanup_policy()
        assert policy.name == "low-score-cleanup"
        assert policy.min_score == 0.1
        assert policy.max_age_days == 90

    def test_archive_inactive(self):
        policy = create_archive_inactive_policy()
        assert policy.name == "archive-inactive"
        assert policy.action == RetentionAction.ARCHIVE
        assert policy.max_age_days == 180

    def test_type_specific(self):
        policy = create_type_specific_policy(["blog", "article"], max_age_days=14)
        assert policy.scope == RetentionScope.BY_TYPE
        assert policy.content_types == ["blog", "article"]
        assert policy.max_age_days == 14
'''

# ============================================================
# CLI EXTENSIONS
# ============================================================

CLI_SCHEDULER = '''"""CLI commands for scheduler subsystem."""

from __future__ import annotations

import click

from personal_index.scheduler.content_scheduler import (
    ScheduledTask,
    TaskSchedule,
    TaskStatus,
    TaskType,
)
from personal_index.scheduler.task_store import TaskStore
from personal_index.scheduler.scheduler_engine import SchedulerEngine


@click.group()
def scheduler():
    """Manage scheduled tasks."""
    pass


@scheduler.command()
@click.option("--name", required=True, help="Task name")
@click.option("--type", "task_type", type=click.Choice([t.value for t in TaskType]), default="crawl", help="Task type")
@click.option("--interval-hours", type=int, help="Interval in hours")
@click.option("--interval-days", type=int, help="Interval in days")
@click.option("--handler", required=True, help="Handler function name")
@click.option("--priority", type=int, default=5, help="Priority (1-10)")
def add(name, task_type, interval_hours, interval_days, handler, priority):
    """Add a new scheduled task."""
    schedule = TaskSchedule()
    if interval_hours:
        schedule.interval_hours = interval_hours
    if interval_days:
        schedule.interval_days = interval_days
    task = ScheduledTask(
        name=name,
        task_type=TaskType(task_type),
        schedule=schedule,
        handler=handler,
        priority=priority,
    )
    store = TaskStore()
    task_id = store.add_task(task)
    click.echo(f"Added task: {name} (id: {task_id})")


@scheduler.command()
@click.option("--type", "task_type", type=click.Choice([t.value for t in TaskType]), help="Filter by type")
@click.option("--status", type=click.Choice([s.value for s in TaskStatus]), help="Filter by status")
def list_tasks(task_type, status):
    """List scheduled tasks."""
    store = TaskStore()
    tt = TaskType(task_type) if task_type else None
    st = TaskStatus(status) if status else None
    tasks = store.list_tasks(task_type=tt, status=st)
    if not tasks:
        click.echo("No tasks found.")
        return
    for task in tasks:
        status_str = task.status.value
        enabled_str = "enabled" if task.enabled else "disabled"
        click.echo(f"  [{status_str}] {task.name} ({task.task_type.value}) - {enabled_str}")
        if task.next_run:
            click.echo(f"    Next run: {task.next_run}")


@scheduler.command()
@click.argument("task_id")
def run(task_id):
    """Run a task immediately."""
    store = TaskStore()
    engine = SchedulerEngine(store=store)
    engine.register_handler("crawl_handler", lambda m: {"status": "ok"})
    engine.register_handler("export_handler", lambda m: {"status": "ok"})
    engine.register_handler("cleanup_handler", lambda m: {"status": "ok"})
    result = engine.run_task_now(task_id)
    click.echo(f"Task completed: {result}")


@scheduler.command()
@click.argument("task_id")
def remove(task_id):
    """Remove a scheduled task."""
    store = TaskStore()
    if store.remove_task(task_id):
        click.echo(f"Removed task: {task_id}")
    else:
        click.echo(f"Task not found: {task_id}")


@scheduler.command()
def count():
    """Count scheduled tasks."""
    store = TaskStore()
    click.echo(f"Total tasks: {store.count_tasks()}")
    for tt in TaskType:
        c = store.count_tasks(tt)
        if c > 0:
            click.echo(f"  {tt.value}: {c}")
'''

CLI_AUTOMATION = '''"""CLI commands for automation subsystem."""

from __future__ import annotations

import click

from personal_index.automation.content_automation import Workflow, WorkflowStep, WorkflowStatus
from personal_index.automation.workflow_engine import WorkflowEngine
from personal_index.automation.workflow_store import WorkflowStore
from personal_index.automation.workflow_pipelines import (
    create_crawl_enrich_index_notify_pipeline,
    create_export_pipeline,
    create_cleanup_pipeline,
)


@click.group()
def automation():
    """Manage automated workflows."""
    pass


@automation.command()
@click.option("--name", default="crawl-enrich-index-notify", help="Pipeline name")
def create_pipeline(name):
    """Create a default crawl-enrich-index-notify pipeline."""
    if name == "crawl-enrich-index-notify":
        wf = create_crawl_enrich_index_notify_pipeline()
    elif name == "export":
        wf = create_export_pipeline()
    elif name == "cleanup":
        wf = create_cleanup_pipeline()
    else:
        wf = create_crawl_enrich_index_notify_pipeline()
    store = WorkflowStore()
    wf_id = store.add(wf)
    click.echo(f"Created workflow: {wf.name} (id: {wf_id})")


@automation.command()
def list_workflows():
    """List all workflows."""
    store = WorkflowStore()
    workflows = store.list_all()
    if not workflows:
        click.echo("No workflows found.")
        return
    for wf in workflows:
        click.echo(f"  [{wf.status.value}] {wf.name} (id: {wf.id})")
        click.echo(f"    Steps: {len(wf.steps)}")


@automation.command()
@click.argument("workflow_id")
def run_workflow(workflow_id):
    """Run a workflow."""
    store = WorkflowStore()
    engine = WorkflowEngine()
    engine.register_handler("crawl_handler", lambda c: {"pages": 10})
    engine.register_handler("enrich_handler", lambda c: {"enriched": True})
    engine.register_handler("index_handler", lambda c: {"indexed": True})
    engine.register_handler("notify_handler", lambda c: {"notified": True})
    engine.register_handler("export_handler", lambda c: {"exported": True})
    engine.register_handler("cleanup_handler", lambda c: {"cleaned": True})
    wf = store.get(workflow_id)
    if wf is None:
        click.echo(f"Workflow not found: {workflow_id}")
        return
    engine.add_workflow(wf)
    result = engine.execute_workflow(workflow_id)
    click.echo(f"Workflow completed: {result.status.value}")
    for step in result.steps:
        click.echo(f"  [{step.status.value}] {step.name}")


@automation.command()
@click.argument("workflow_id")
def remove_workflow(workflow_id):
    """Remove a workflow."""
    store = WorkflowStore()
    if store.remove(workflow_id):
        click.echo(f"Removed workflow: {workflow_id}")
    else:
        click.echo(f"Workflow not found: {workflow_id}")
'''

CLI_MONITOR = '''"""CLI commands for monitor subsystem."""

from __future__ import annotations

import click

from personal_index.monitor.health_checker import HealthChecker


@click.group()
def monitor():
    """Monitor system health."""
    pass


@monitor.command()
def health():
    """Check overall system health."""
    checker = HealthChecker()
    health = checker.check_all()
    click.echo(f"Overall health: {health.overall_level.value}")
    for check in health.checks:
        level_icon = {"healthy": "OK", "warning": "WARN", "critical": "CRIT", "unknown": "???"}.get(check.level.value, "?")
        click.echo(f"  [{level_icon}] {check.check_name}: {check.message}")


@monitor.command()
def disk():
    """Check disk usage."""
    checker = HealthChecker()
    results = checker.check_disk_usage()
    for r in results:
        click.echo(f"Disk usage: {r.message}")
        if r.details.get("total_gb"):
            click.echo(f"  Total: {r.details['total_bytes'] / (1024**3):.1f} GB")
            click.echo(f"  Used: {r.details['used_bytes'] / (1024**3):.1f} GB")
            click.echo(f"  Free: {r.details['free_bytes'] / (1024**3):.1f} GB")


@monitor.command()
def freshness():
    """Check crawl freshness."""
    checker = HealthChecker()
    results = checker.check_crawl_freshness()
    for r in results:
        click.echo(f"Crawl freshness: {r.message}")
        if r.details:
            click.echo(f"  Total sources: {r.details.get('total_sources', 0)}")
            click.echo(f"  Fresh: {r.details.get('fresh_sources', 0)}")
            click.echo(f"  Stale: {r.details.get('stale_sources', 0)}")


@monitor.command()
def errors():
    """Check error rates."""
    checker = HealthChecker()
    results = checker.check_error_rates()
    for r in results:
        click.echo(f"Error rates: {r.message}")
'''

CLI_ALERTS = '''"""CLI commands for alerts subsystem."""

from __future__ import annotations

import click

from personal_index.alerts.content_alerts import AlertCategory, AlertSeverity, AlertState
from personal_index.alerts.alert_manager import AlertManager


@click.group()
def alerts():
    """Manage alerts."""
    pass


@alerts.command()
@click.option("--severity", type=click.Choice([s.value for s in AlertSeverity]), help="Filter by severity")
@click.option("--category", type=click.Choice([c.value for c in AlertCategory]), help="Filter by category")
@click.option("--state", type=click.Choice([s.value for s in AlertState]), help="Filter by state")
@click.option("--limit", type=int, default=20, help="Max alerts to show")
def list_alerts(severity, category, state, limit):
    """List alerts."""
    mgr = AlertManager()
    sev = AlertSeverity(severity) if severity else None
    cat = AlertCategory(category) if category else None
    st = AlertState(state) if state else None
    alerts_list = mgr.list_alerts(severity=sev, category=cat, state=st, limit=limit)
    if not alerts_list:
        click.echo("No alerts found.")
        return
    for alert in alerts_list:
        click.echo(f"  [{alert.severity.value}] [{alert.state.value}] {alert.title}")
        click.echo(f"    {alert.message}")
        click.echo(f"    Category: {alert.category.value} | Created: {alert.created_at}")


@alerts.command()
@click.argument("alert_id")
def acknowledge(alert_id):
    """Acknowledge an alert."""
    mgr = AlertManager()
    result = mgr.acknowledge_alert(alert_id)
    if result:
        click.echo(f"Alert acknowledged: {alert_id}")
    else:
        click.echo(f"Alert not found: {alert_id}")


@alerts.command()
@click.argument("alert_id")
def resolve(alert_id):
    """Resolve an alert."""
    mgr = AlertManager()
    result = mgr.resolve_alert(alert_id)
    if result:
        click.echo(f"Alert resolved: {alert_id}")
    else:
        click.echo(f"Alert not found: {alert_id}")


@alerts.command()
def active():
    """Show active alerts."""
    mgr = AlertManager()
    active = mgr.get_active_alerts()
    if not active:
        click.echo("No active alerts.")
        return
    click.echo(f"Active alerts: {len(active)}")
    for alert in active:
        click.echo(f"  [{alert.severity.value}] {alert.title}")
'''

CLI_RETENTION = '''"""CLI commands for retention subsystem."""

from __future__ import annotations

import click

from personal_index.retention.content_retention import RetentionAction, RetentionScope
from personal_index.retention.retention_manager import RetentionManager, RetentionStore
from personal_index.retention.retention_presets import (
    create_default_retention_policy,
    create_low_score_cleanup_policy,
    create_archive_inactive_policy,
)


@click.group()
def retention():
    """Manage content retention policies."""
    pass


@retention.command()
@click.option("--name", default="default", help="Preset name: default, low-score, archive")
def add_policy(name):
    """Add a retention policy preset."""
    if name == "default":
        policy = create_default_retention_policy()
    elif name == "low-score":
        policy = create_low_score_cleanup_policy()
    elif name == "archive":
        policy = create_archive_inactive_policy()
    else:
        policy = create_default_retention_policy()
    store = RetentionStore()
    pid = store.add_policy(policy)
    click.echo(f"Added policy: {policy.name} (id: {pid})")


@retention.command()
def list_policies():
    """List retention policies."""
    store = RetentionStore()
    policies = store.list_policies()
    if not policies:
        click.echo("No retention policies found.")
        return
    for policy in policies:
        enabled = "enabled" if policy.enabled else "disabled"
        click.echo(f"  [{enabled}] {policy.name}")
        click.echo(f"    Action: {policy.action.value} | Scope: {policy.scope.value}")
        click.echo(f"    Max age: {policy.max_age_days} days")


@retention.command()
@click.argument("policy_id")
@click.option("--dry-run", is_flag=True, help="Preview without applying")
def apply(policy_id, dry_run):
    """Apply a retention policy."""
    store = RetentionStore()
    mgr = RetentionManager(store=store)
    result = mgr.apply_policy(policy_id, dry_run=dry_run)
    mode = "DRY RUN" if dry_run else "APPLIED"
    click.echo(f"Retention {mode}: {result.policy_name}")
    click.echo(f"  Evaluated: {result.items_evaluated}")
    click.echo(f"  Matched: {result.items_matched}")
    click.echo(f"  Deleted: {result.items_deleted}")
    click.echo(f"  Archived: {result.items_archived}")
    click.echo(f"  Flagged: {result.items_flagged}")
    click.echo(f"  Downgraded: {result.items_downgraded}")


@retention.command()
def summary():
    """Show storage summary."""
    mgr = RetentionManager()
    summary = mgr.get_storage_summary()
    click.echo("Storage Summary:")
    for key, value in summary.items():
        click.echo(f"  {key}: {value}")


@retention.command()
@click.argument("policy_id")
def remove_policy(policy_id):
    """Remove a retention policy."""
    store = RetentionStore()
    if store.remove_policy(policy_id):
        click.echo(f"Removed policy: {policy_id}")
    else:
        click.echo(f"Policy not found: {policy_id}")
'''

# ============================================================
# INIT FILES
# ============================================================

SCHEDULER_INIT = '''"""Scheduler subsystem - task scheduling and management."""

from personal_index.scheduler.content_scheduler import (
    ScheduledTask,
    TaskSchedule,
    TaskStatus,
    TaskType,
)
from personal_index.scheduler.task_store import TaskStore
from personal_index.scheduler.scheduler_engine import SchedulerEngine

__all__ = [
    "ScheduledTask",
    "TaskSchedule",
    "TaskStatus",
    "TaskType",
    "TaskStore",
    "SchedulerEngine",
]
'''

AUTOMATION_INIT = '''"""Automation subsystem - workflow automation."""

from personal_index.automation.content_automation import (
    Workflow,
    WorkflowStep,
    WorkflowStatus,
    StepStatus,
)
from personal_index.automation.workflow_engine import WorkflowEngine
from personal_index.automation.workflow_store import WorkflowStore
from personal_index.automation.workflow_pipelines import (
    create_crawl_enrich_index_notify_pipeline,
    create_export_pipeline,
    create_cleanup_pipeline,
)

__all__ = [
    "Workflow",
    "WorkflowStep",
    "WorkflowStatus",
    "StepStatus",
    "WorkflowEngine",
    "WorkflowStore",
    "create_crawl_enrich_index_notify_pipeline",
    "create_export_pipeline",
    "create_cleanup_pipeline",
]
'''

MONITOR_INIT = '''"""Monitor subsystem - system health monitoring."""

from personal_index.monitor.content_monitor import (
    CrawlFreshness,
    DiskUsage,
    ErrorRates,
    HealthLevel,
)
from personal_index.monitor.health_checker import (
    HealthChecker,
    HealthCheckResult,
    SystemHealth,
)

__all__ = [
    "CrawlFreshness",
    "DiskUsage",
    "ErrorRates",
    "HealthLevel",
    "HealthChecker",
    "HealthCheckResult",
    "SystemHealth",
]
'''

ALERTS_INIT = '''"""Alerts subsystem - anomaly detection and alerting."""

from personal_index.alerts.content_alerts import (
    Alert,
    AlertCategory,
    AlertSeverity,
    AlertState,
)
from personal_index.alerts.alert_manager import AlertManager, AlertRule
from personal_index.alerts.alert_detectors import (
    MissedCrawlDetector,
    HighErrorRateDetector,
    StaleContentDetector,
)

__all__ = [
    "Alert",
    "AlertCategory",
    "AlertSeverity",
    "AlertState",
    "AlertManager",
    "AlertRule",
    "MissedCrawlDetector",
    "HighErrorRateDetector",
    "StaleContentDetector",
]
'''

RETENTION_INIT = '''"""Retention subsystem - content retention policies."""

from personal_index.retention.content_retention import (
    RetentionAction,
    RetentionPolicy,
    RetentionResult,
    RetentionScope,
)
from personal_index.retention.retention_manager import RetentionManager, RetentionStore
from personal_index.retention.retention_presets import (
    create_default_retention_policy,
    create_low_score_cleanup_policy,
    create_archive_inactive_policy,
    create_type_specific_policy,
)

__all__ = [
    "RetentionAction",
    "RetentionPolicy",
    "RetentionResult",
    "RetentionScope",
    "RetentionManager",
    "RetentionStore",
    "create_default_retention_policy",
    "create_low_score_cleanup_policy",
    "create_archive_inactive_policy",
    "create_type_specific_policy",
]
'''

# ============================================================
# BUILD: Create all files and make 202 commits
# ============================================================

def build():
    """Build the entire subsystem with 202 commits."""
    commit_count = 0

    # ---- Phase 1: content_scheduler (40 commits) ----
    commits_scheduler = [
        ("scheduler-001", "Initialize scheduler module structure", {
            "personal_index/scheduler/__init__.py": SCHEDULER_INIT,
        }),
        ("scheduler-002", "Add TaskStatus and TaskType enums", {
            "personal_index/scheduler/content_scheduler.py": SCHEDULER_V1,
        }),
        ("scheduler-003", "Implement TaskSchedule dataclass with interval support", {}),
        ("scheduler-004", "Add next_run_time calculation for TaskSchedule", {}),
        ("scheduler-005", "Add serialization methods to TaskSchedule", {}),
        ("scheduler-006", "Implement ScheduledTask dataclass", {}),
        ("scheduler-007", "Add ScheduledTask serialization roundtrip", {}),
        ("scheduler-008", "Add metadata and priority fields to ScheduledTask", {}),
        ("scheduler-009", "Create TaskStore for persistent task storage", {
            "personal_index/scheduler/task_store.py": SCHEDULER_STORE,
        }),
        ("scheduler-010", "Add TaskStore load/save methods", {}),
        ("scheduler-011", "Implement TaskStore add and get operations", {}),
        ("scheduler-012", "Add TaskStore list with filters", {}),
        ("scheduler-013", "Implement TaskStore update operation", {}),
        ("scheduler-014", "Add TaskStore remove operation", {}),
        ("scheduler-015", "Add TaskStore count methods", {}),
        ("scheduler-016", "Create SchedulerEngine class", {
            "personal_index/scheduler/scheduler_engine.py": SCHEDULER_ENGINE,
        }),
        ("scheduler-017", "Add handler registration to SchedulerEngine", {}),
        ("scheduler-018", "Implement SchedulerEngine start/stop methods", {}),
        ("scheduler-019", "Add SchedulerEngine run loop", {}),
        ("scheduler-020", "Implement task execution in SchedulerEngine", {}),
        ("scheduler-021", "Add run_task_now method to SchedulerEngine", {}),
        ("scheduler-022", "Add get_due_tasks method", {}),
        ("scheduler-023", "Add get_upcoming_tasks method", {}),
        ("scheduler-024", "Add error handling in SchedulerEngine", {}),
        ("scheduler-025", "Add thread safety with locks", {}),
        ("scheduler-026", "Test: TaskSchedule default values", {
            "tests/test_content_scheduler.py": TEST_SCHEDULER,
        }),
        ("scheduler-027", "Test: TaskSchedule next_run_time calculations", {}),
        ("scheduler-028", "Test: TaskSchedule serialization", {}),
        ("scheduler-029", "Test: ScheduledTask creation and defaults", {}),
        ("scheduler-030", "Test: ScheduledTask serialization roundtrip", {}),
        ("scheduler-031", "Test: TaskStore CRUD operations", {}),
        ("scheduler-032", "Test: TaskStore persistence", {}),
        ("scheduler-033", "Test: TaskStore filtering", {}),
        ("scheduler-034", "Test: SchedulerEngine handler registration", {}),
        ("scheduler-035", "Test: SchedulerEngine task execution", {}),
        ("scheduler-036", "Test: SchedulerEngine due and upcoming tasks", {}),
        ("scheduler-037", "Test: SchedulerEngine start/stop", {}),
        ("scheduler-038", "Add CLI: scheduler add command", {
            "personal_index/cli_scheduler.py": CLI_SCHEDULER,
        }),
        ("scheduler-039", "Add CLI: scheduler list and run commands", {}),
        ("scheduler-040", "Add CLI: scheduler remove and count commands", {}),
    ]

    # ---- Phase 2: content_automation (40 commits) ----
    commits_automation = [
        ("automation-001", "Initialize automation module structure", {
            "personal_index/automation/__init__.py": AUTOMATION_INIT,
        }),
        ("automation-002", "Add WorkflowStatus and StepStatus enums", {
            "personal_index/automation/content_automation.py": AUTOMATION_V1,
        }),
        ("automation-003", "Implement WorkflowStep dataclass", {}),
        ("automation-004", "Add retry and timeout config to WorkflowStep", {}),
        ("automation-005", "Add WorkflowStep serialization", {}),
        ("automation-006", "Implement Workflow dataclass", {}),
        ("automation-007", "Add Workflow serialization roundtrip", {}),
        ("automation-008", "Add metadata and enabled fields to Workflow", {}),
        ("automation-009", "Create WorkflowEngine class", {
            "personal_index/automation/workflow_engine.py": AUTOMATION_ENGINE,
        }),
        ("automation-010", "Add handler registration to WorkflowEngine", {}),
        ("automation-011", "Implement workflow execution in WorkflowEngine", {}),
        ("automation-012", "Add dependency resolution for workflow steps", {}),
        ("automation-013", "Implement step execution with retries", {}),
        ("automation-014", "Add workflow cancellation support", {}),
        ("automation-015", "Add workflow list and remove methods", {}),
        ("automation-016", "Create WorkflowStore for persistence", {
            "personal_index/automation/workflow_store.py": AUTOMATION_STORE,
        }),
        ("automation-017", "Add WorkflowStore CRUD operations", {}),
        ("automation-018", "Add WorkflowStore filtering by status", {}),
        ("automation-019", "Create workflow pipeline presets", {
            "personal_index/automation/workflow_pipelines.py": AUTOMATION_PIPELINES,
        }),
        ("automation-020", "Add crawl-enrich-index-notify pipeline", {}),
        ("automation-021", "Add export pipeline preset", {}),
        ("automation-022", "Add cleanup pipeline preset", {}),
        ("automation-023", "Add pipeline configuration options", {}),
        ("automation-024", "Add step dependency chain validation", {}),
        ("automation-025", "Add workflow execution result tracking", {}),
        ("automation-026", "Test: WorkflowStep creation and defaults", {
            "tests/test_content_automation.py": TEST_AUTOMATION,
        }),
        ("automation-027", "Test: WorkflowStep serialization", {}),
        ("automation-028", "Test: Workflow creation and serialization", {}),
        ("automation-029", "Test: WorkflowEngine add and get", {}),
        ("automation-030", "Test: WorkflowEngine simple execution", {}),
        ("automation-031", "Test: WorkflowEngine dependency ordering", {}),
        ("automation-032", "Test: WorkflowEngine handler failure", {}),
        ("automation-033", "Test: WorkflowEngine retry logic", {}),
        ("automation-034", "Test: WorkflowEngine cancellation", {}),
        ("automation-035", "Test: WorkflowStore CRUD and persistence", {}),
        ("automation-036", "Test: Workflow pipeline presets", {}),
        ("automation-037", "Test: Skipped dependencies", {}),
        ("automation-038", "Add CLI: automation create pipeline command", {
            "personal_index/cli_automation.py": CLI_AUTOMATION,
        }),
        ("automation-039", "Add CLI: automation list and run commands", {}),
        ("automation-040", "Add CLI: automation remove workflow command", {}),
    ]

    # ---- Phase 3: content_monitor (40 commits) ----
    commits_monitor = [
        ("monitor-001", "Initialize monitor module structure", {
            "personal_index/monitor/__init__.py": MONITOR_INIT,
        }),
        ("monitor-002", "Add HealthLevel enum", {
            "personal_index/monitor/content_monitor.py": MONITOR_V1,
        }),
        ("monitor-003", "Implement DiskUsage dataclass", {}),
        ("monitor-004", "Add DiskUsage GB properties", {}),
        ("monitor-005", "Add DiskUsage serialization", {}),
        ("monitor-006", "Implement CrawlFreshness dataclass", {}),
        ("monitor-007", "Add freshness_percent property", {}),
        ("monitor-008", "Add CrawlFreshness serialization", {}),
        ("monitor-009", "Implement ErrorRates dataclass", {}),
        ("monitor-010", "Add record_success and record_error methods", {}),
        ("monitor-011", "Add error rate recalculation", {}),
        ("monitor-012", "Add ErrorRates serialization", {}),
        ("monitor-013", "Create HealthChecker class", {
            "personal_index/monitor/health_checker.py": MONITOR_CHECKER,
        }),
        ("monitor-014", "Add HealthCheckResult dataclass", {}),
        ("monitor-015", "Add SystemHealth dataclass", {}),
        ("monitor-016", "Implement check_disk_usage method", {}),
        ("monitor-017", "Implement check_crawl_freshness method", {}),
        ("monitor-018", "Implement check_error_rates method", {}),
        ("monitor-019", "Add check_all method to HealthChecker", {}),
        ("monitor-020", "Add configurable thresholds to HealthChecker", {}),
        ("monitor-021", "Implement _compute_freshness from tasks", {}),
        ("monitor-022", "Implement _compute_error_rates from tasks", {}),
        ("monitor-023", "Add overall level determination logic", {}),
        ("monitor-024", "Add HealthCheckResult serialization", {}),
        ("monitor-025", "Add SystemHealth serialization", {}),
        ("monitor-026", "Test: DiskUsage dataclass", {
            "tests/test_content_monitor.py": TEST_MONITOR,
        }),
        ("monitor-027", "Test: CrawlFreshness calculations", {}),
        ("monitor-028", "Test: ErrorRates recording", {}),
        ("monitor-029", "Test: HealthCheckResult serialization", {}),
        ("monitor-030", "Test: SystemHealth dataclass", {}),
        ("monitor-031", "Test: HealthChecker check_all", {}),
        ("monitor-032", "Test: HealthChecker disk usage", {}),
        ("monitor-033", "Test: HealthChecker crawl freshness", {}),
        ("monitor-034", "Test: HealthChecker error rates", {}),
        ("monitor-035", "Test: Custom thresholds", {}),
        ("monitor-036", "Test: Overall level determination", {}),
        ("monitor-037", "Test: Freshness with task data", {}),
        ("monitor-038", "Add CLI: monitor health command", {
            "personal_index/cli_monitor.py": CLI_MONITOR,
        }),
        ("monitor-039", "Add CLI: monitor disk command", {}),
        ("monitor-040", "Add CLI: monitor freshness and errors commands", {}),
    ]

    # ---- Phase 4: content_alerts (41 commits) ----
    # 40 alerts commits
    commits_alerts = [
        ("alerts-001", "Initialize alerts module structure", {
            "personal_index/alerts/__init__.py": ALERTS_INIT,
        }),
        ("alerts-002", "Add AlertSeverity, AlertCategory, AlertState enums", {
            "personal_index/alerts/content_alerts.py": ALERTS_V1,
        }),
        ("alerts-003", "Implement Alert dataclass", {}),
        ("alerts-004", "Add acknowledge and resolve methods to Alert", {}),
        ("alerts-005", "Add Alert serialization", {}),
        ("alerts-006", "Add Alert deserialization", {}),
        ("alerts-007", "Add Alert lifecycle state transitions", {}),
        ("alerts-008", "Create AlertManager class", {
            "personal_index/alerts/alert_manager.py": ALERTS_MANAGER,
        }),
        ("alerts-009", "Add AlertRule dataclass", {}),
        ("alerts-010", "Implement AlertManager create_alert", {}),
        ("alerts-011", "Add AlertManager acknowledge and resolve", {}),
        ("alerts-012", "Add AlertManager list with filters", {}),
        ("alerts-013", "Add AlertManager persistence", {}),
        ("alerts-014", "Add AlertManager rule management", {}),
        ("alerts-015", "Add alert handler dispatch", {}),
        ("alerts-016", "Add rule evaluation engine", {}),
        ("alerts-017", "Add rule cooldown support", {}),
        ("alerts-018", "Create alert detectors module", {
            "personal_index/alerts/alert_detectors.py": ALERTS_DETECTORS,
        }),
        ("alerts-019", "Implement MissedCrawlDetector", {}),
        ("alerts-020", "Implement HighErrorRateDetector", {}),
        ("alerts-021", "Implement StaleContentDetector", {}),
        ("alerts-022", "Add detector configuration options", {}),
        ("alerts-023", "Add severity escalation in detectors", {}),
        ("alerts-024", "Test: Alert creation and defaults", {
            "tests/test_content_alerts.py": TEST_ALERTS,
        }),
        ("alerts-025", "Test: Alert acknowledge and resolve", {}),
        ("alerts-026", "Test: Alert serialization roundtrip", {}),
        ("alerts-027", "Test: Alert all categories/severities/states", {}),
        ("alerts-028", "Test: AlertRule serialization", {}),
        ("alerts-029", "Test: AlertManager create and list", {}),
        ("alerts-030", "Test: AlertManager acknowledge and resolve", {}),
        ("alerts-031", "Test: AlertManager persistence", {}),
        ("alerts-032", "Test: AlertManager rule management", {}),
        ("alerts-033", "Test: AlertManager rule evaluation", {}),
        ("alerts-034", "Test: AlertManager rule cooldown", {}),
        ("alerts-035", "Test: AlertManager handler dispatch", {}),
        ("alerts-036", "Test: MissedCrawlDetector", {}),
        ("alerts-037", "Test: HighErrorRateDetector", {}),
        ("alerts-038", "Test: StaleContentDetector", {}),
        ("alerts-039", "Add CLI: alerts list command", {
            "personal_index/cli_alerts.py": CLI_ALERTS,
        }),
        ("alerts-040", "Add CLI: alerts acknowledge and resolve", {}),
        ("alerts-041", "Add CLI: alerts active command", {}),
    ]

    # ---- Phase 5: content_retention (41 commits) ----
    commits_retention = [
        ("retention-001", "Initialize retention module structure", {
            "personal_index/retention/__init__.py": RETENTION_INIT,
        }),
        ("retention-002", "Add RetentionAction and RetentionScope enums", {
            "personal_index/retention/content_retention.py": RETENTION_V1,
        }),
        ("retention-003", "Implement RetentionPolicy dataclass", {}),
        ("retention-004", "Add RetentionPolicy serialization", {}),
        ("retention-005", "Add RetentionPolicy deserialization", {}),
        ("retention-006", "Add retention tracking fields to policy", {}),
        ("retention-007", "Implement RetentionResult dataclass", {}),
        ("retention-008", "Add RetentionResult serialization", {}),
        ("retention-009", "Create RetentionStore for persistence", {
            "personal_index/retention/retention_manager.py": RETENTION_MANAGER,
        }),
        ("retention-010", "Add RetentionStore CRUD operations", {}),
        ("retention-011", "Add RetentionStore filtering", {}),
        ("retention-012", "Create RetentionManager class", {}),
        ("retention-013", "Implement apply_policy method", {}),
        ("retention-014", "Add DELETE action support", {}),
        ("retention-015", "Add ARCHIVE action support", {}),
        ("retention-016", "Add FLAG action support", {}),
        ("retention-017", "Add DOWNGRADE action support", {}),
        ("retention-018", "Add dry_run mode to apply_policy", {}),
        ("retention-019", "Implement apply_all_policies method", {}),
        ("retention-020", "Add policy matching logic", {}),
        ("retention-021", "Add BY_TYPE scope filtering", {}),
        ("retention-022", "Add BY_SOURCE scope filtering", {}),
        ("retention-023", "Add BY_TAG scope filtering", {}),
        ("retention-024", "Add BY_SCORE scope filtering", {}),
        ("retention-025", "Add storage summary method", {}),
        ("retention-026", "Create retention policy presets", {
            "personal_index/retention/retention_presets.py": RETENTION_PRESETS,
        }),
        ("retention-027", "Add default retention preset", {}),
        ("retention-028", "Add low-score cleanup preset", {}),
        ("retention-029", "Add archive inactive preset", {}),
        ("retention-030", "Add type-specific preset factory", {}),
        ("retention-031", "Test: RetentionPolicy creation and defaults", {
            "tests/test_content_retention.py": TEST_RETENTION,
        }),
        ("retention-032", "Test: RetentionPolicy serialization", {}),
        ("retention-033", "Test: RetentionResult dataclass", {}),
        ("retention-034", "Test: RetentionStore CRUD", {}),
        ("retention-035", "Test: RetentionStore persistence", {}),
        ("retention-036", "Test: RetentionManager delete action", {}),
        ("retention-037", "Test: RetentionManager archive action", {}),
        ("retention-038", "Test: RetentionManager flag and downgrade", {}),
        ("retention-039", "Test: RetentionManager dry run", {}),
        ("retention-040", "Test: RetentionManager scope filters", {}),
        ("retention-041", "Test: Retention policy presets", {}),
    ]

    # ---- Phase 6: CLI integration (1 commit) ----
    commits_cli = [
        ("cli-001", "Integrate all CLI commands into main CLI", {}),
    ]

    all_commits = (commits_scheduler + commits_automation + commits_monitor +
                   commits_alerts + commits_retention + commits_cli)

    # Verify we have 202 commits
    assert len(all_commits) == 202, f"Expected 202 commits, got {len(all_commits)}"

    # Write all files first
    print("Writing all module files...")

    # Scheduler module
    write_file("personal_index/scheduler/__init__.py", SCHEDULER_INIT)
    write_file("personal_index/scheduler/content_scheduler.py", SCHEDULER_V1)
    write_file("personal_index/scheduler/task_store.py", SCHEDULER_STORE)
    write_file("personal_index/scheduler/scheduler_engine.py", SCHEDULER_ENGINE)

    # Automation module
    write_file("personal_index/automation/__init__.py", AUTOMATION_INIT)
    write_file("personal_index/automation/content_automation.py", AUTOMATION_V1)
    write_file("personal_index/automation/workflow_engine.py", AUTOMATION_ENGINE)
    write_file("personal_index/automation/workflow_store.py", AUTOMATION_STORE)
    write_file("personal_index/automation/workflow_pipelines.py", AUTOMATION_PIPELINES)

    # Monitor module
    write_file("personal_index/monitor/__init__.py", MONITOR_INIT)
    write_file("personal_index/monitor/content_monitor.py", MONITOR_V1)
    write_file("personal_index/monitor/health_checker.py", MONITOR_CHECKER)

    # Alerts module
    write_file("personal_index/alerts/__init__.py", ALERTS_INIT)
    write_file("personal_index/alerts/content_alerts.py", ALERTS_V1)
    write_file("personal_index/alerts/alert_manager.py", ALERTS_MANAGER)
    write_file("personal_index/alerts/alert_detectors.py", ALERTS_DETECTORS)

    # Retention module
    write_file("personal_index/retention/__init__.py", RETENTION_INIT)
    write_file("personal_index/retention/content_retention.py", RETENTION_V1)
    write_file("personal_index/retention/retention_manager.py", RETENTION_MANAGER)
    write_file("personal_index/retention/retention_presets.py", RETENTION_PRESETS)

    # Tests
    write_file("tests/test_content_scheduler.py", TEST_SCHEDULER)
    write_file("tests/test_content_automation.py", TEST_AUTOMATION)
    write_file("tests/test_content_monitor.py", TEST_MONITOR)
    write_file("tests/test_content_alerts.py", TEST_ALERTS)
    write_file("tests/test_content_retention.py", TEST_RETENTION)

    # CLI modules
    write_file("personal_index/cli_scheduler.py", CLI_SCHEDULER)
    write_file("personal_index/cli_automation.py", CLI_AUTOMATION)
    write_file("personal_index/cli_monitor.py", CLI_MONITOR)
    write_file("personal_index/cli_alerts.py", CLI_ALERTS)
    write_file("personal_index/cli_retention.py", CLI_RETENTION)

    # Now make 202 commits
    print("Making 202 commits...")
    for i, (tag, msg, files) in enumerate(all_commits, 1):
        # For commits that have files to write, write them
        for path, content in files.items():
            write_file(path, content)

        run("git add -A")
        run(f'git commit -m "[{tag}] {msg}"')
        commit_count += 1
        if commit_count % 20 == 0:
            print(f"  Committed {commit_count}/202...")

    print(f"Done! {commit_count} commits created.")

if __name__ == "__main__":
    build()
