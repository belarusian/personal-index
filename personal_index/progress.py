"""Progress tracking for long-running operations."""

from __future__ import annotations

import json
import math
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ProgressState(Enum):
    """States of a progress tracker."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class ProgressStep:
    """A single step within a progress operation."""
    step_id: str
    description: str
    completed: bool = False
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the progress step to a dictionary.

        Returns:
            Dictionary representation of the step.
        """
        return {
            "step_id": self.step_id,
            "description": self.description,
            "completed": self.completed,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "details": self.details,
        }


@dataclass
class ProgressTracker:
    """Track progress of a long-running operation."""
    operation_id: str = ""
    operation_name: str = ""
    state: str = "pending"
    total_steps: int = 0
    current_step: int = 0
    steps: List[Dict[str, Any]] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.operation_id:
            ts = int(time.time() * 1000)
            short_uuid = uuid.uuid4().hex[:6]
            self.operation_id = f"op_{ts}_{short_uuid}"
        if self.started_at is None and self.state == "running":
            self.started_at = datetime.now(timezone.utc).isoformat()

    @property
    def progress_percent(self) -> float:
        """Get progress as percentage (0-100)."""
        if self.total_steps == 0:
            return 0.0
        return min(100.0, (self.current_step / self.total_steps) * 100.0)

    @property
    def elapsed_seconds(self) -> float:
        """Get elapsed time in seconds."""
        if not self.started_at:
            return 0.0
        start = datetime.fromisoformat(self.started_at)
        now = datetime.now(timezone.utc)
        return (now - start).total_seconds()

    @property
    def estimated_remaining(self) -> float:
        """Estimate remaining time in seconds."""
        if self.current_step == 0 or self.elapsed_seconds == 0:
            return 0.0
        elapsed_per_step = self.elapsed_seconds / self.current_step
        remaining_steps = self.total_steps - self.current_step
        return elapsed_per_step * remaining_steps

    def start(self) -> None:
        """Start the operation."""
        self.state = ProgressState.RUNNING.value
        self.started_at = datetime.now(timezone.utc).isoformat()

    def pause(self) -> None:
        """Pause the operation."""
        if self.state == ProgressState.RUNNING.value:
            self.state = ProgressState.PAUSED.value

    def resume(self) -> None:
        """Resume a paused operation."""
        if self.state == ProgressState.PAUSED.value:
            self.state = ProgressState.RUNNING.value

    def complete(self) -> None:
        """Mark the operation as completed."""
        self.state = ProgressState.COMPLETED.value
        self.current_step = self.total_steps
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def fail(self, error_message: str = "") -> None:
        """Mark the operation as failed."""
        self.state = ProgressState.FAILED.value
        self.message = error_message
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def cancel(self) -> None:
        """Cancel the operation."""
        self.state = ProgressState.CANCELLED.value
        self.completed_at = datetime.now(timezone.utc).isoformat()

    def advance(self, step_description: str = "",
                step_details: Optional[Dict[str, Any]] = None) -> None:
        """Advance to the next step."""
        if self.state != ProgressState.RUNNING.value:
            return
        self.current_step = min(self.current_step + 1, self.total_steps)
        step = {
            "step_id": f"step_{self.current_step}",
            "description": step_description or f"Step {self.current_step}",
            "completed": True,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "details": step_details or {},
        }
        self.steps.append(step)

    def set_total(self, total: int) -> None:
        """Set the total number of steps."""
        self.total_steps = total

    def set_message(self, message: str) -> None:
        """Set a status message."""
        self.message = message

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the progress tracker to a dictionary.

        Returns:
            Dictionary representation of the tracker.
        """
        return {
            "operation_id": self.operation_id,
            "operation_name": self.operation_name,
            "state": self.state,
            "total_steps": self.total_steps,
            "current_step": self.current_step,
            "progress_percent": round(self.progress_percent, 1),
            "steps": self.steps,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "message": self.message,
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "estimated_remaining": round(self.estimated_remaining, 2),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ProgressTracker:
        """Create a ProgressTracker from a dictionary, ignoring extra keys."""
        valid_keys = {
            "operation_id", "operation_name", "state", "total_steps",
            "current_step", "steps", "started_at", "completed_at",
            "message", "metadata",
        }
        filtered = {k: v for k, v in data.items() if k in valid_keys}
        return cls(**filtered)

    def format_bar(self, width: int = 40) -> str:
        """Format a progress bar string."""
        filled = int(self.progress_percent / 100.0 * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}] {self.progress_percent:.1f}%"


class ProgressStore:
    """Store and retrieve progress trackers."""

    def __init__(self, storage_path: Optional[str] = None):
        self._trackers: Dict[str, ProgressTracker] = {}
        self._storage_path = storage_path

    def create(self, operation_name: str, total_steps: int = 0,
               metadata: Optional[Dict[str, Any]] = None) -> ProgressTracker:
        """Create a new progress tracker."""
        tracker = ProgressTracker(
            operation_name=operation_name,
            total_steps=total_steps,
            metadata=metadata or {},
        )
        self._trackers[tracker.operation_id] = tracker
        return tracker

    def get(self, operation_id: str) -> Optional[ProgressTracker]:
        """Get a tracker by ID."""
        return self._trackers.get(operation_id)

    def list_active(self) -> List[ProgressTracker]:
        """List all active (running/paused) trackers."""
        return [
            t for t in self._trackers.values()
            if t.state in (ProgressState.RUNNING.value, ProgressState.PAUSED.value)
        ]

    def list_completed(self, limit: int = 20) -> List[ProgressTracker]:
        """List completed trackers, most recent first."""
        completed = [
            t for t in self._trackers.values()
            if t.state in (ProgressState.COMPLETED.value,
                          ProgressState.FAILED.value,
                          ProgressState.CANCELLED.value)
        ]
        completed.sort(key=lambda t: t.completed_at or "", reverse=True)
        return completed[:limit]

    def remove(self, operation_id: str) -> bool:
        """Remove a tracker."""
        if operation_id in self._trackers:
            del self._trackers[operation_id]
            return True
        return False

    def cleanup(self, max_keep: int = 50) -> int:
        """Remove old completed trackers. Returns count removed."""
        completed = self.list_completed(limit=max_keep + 10000)
        removed = 0
        if len(completed) > max_keep:
            for tracker in completed[max_keep:]:
                self.remove(tracker.operation_id)
                removed += 1
        return removed

    def save_all(self) -> None:
        """Save all trackers to disk."""
        if not self._storage_path:
            return
        path = Path(self._storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            oid: t.to_dict() for oid, t in self._trackers.items()
        }
        with open(str(path), "w") as f:
            json.dump(data, f, indent=2)

    def load_all(self) -> int:
        """Load trackers from disk. Returns count loaded."""
        if not self._storage_path:
            return 0
        path = Path(self._storage_path)
        if not path.exists():
            return 0
        with open(str(path)) as f:
            data = json.load(f)
        for oid, d in data.items():
            tracker = ProgressTracker.from_dict(d)
            self._trackers[oid] = tracker
        return len(self._trackers)
