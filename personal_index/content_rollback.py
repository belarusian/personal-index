"""Content rollback management module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RollbackPoint:
    """A snapshot of content that can be rolled back to."""

    url: str
    content: str
    title: str = ""
    timestamp: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class ContentRollback:
    """Manage content rollback points."""

    def __init__(self) -> None:
        self._rollback_points: dict[str, list[RollbackPoint]] = {}

    def create_rollback_point(self, point: RollbackPoint) -> None:
        """Create a new rollback point for a URL."""
        if point.url not in self._rollback_points:
            self._rollback_points[point.url] = []
        self._rollback_points[point.url].append(point)

    def get_rollback_points(self, url: str) -> list[RollbackPoint]:
        """Get all rollback points for a URL."""
        return list(self._rollback_points.get(url, []))

    def rollback(self, url: str, index: int = 0) -> RollbackPoint | None:
        """Roll back a URL to a previous version."""
        points = self._rollback_points.get(url, [])
        if not points:
            return None
        return points[index]

    def clear(self, url: str | None = None) -> None:
        """Clear rollback points."""
        if url:
            self._rollback_points.pop(url, None)
        else:
            self._rollback_points.clear()
