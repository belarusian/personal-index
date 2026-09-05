"""Content health checking."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class HealthCheck:
    """Result of a health check.

    Attributes:
        check_name: Name of the health check.
        healthy: Whether the check passed.
        message: Check result message.
        details: Additional check details.
    """

    check_name: str
    healthy: bool
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthStatus:
    """Overall health status.

    Attributes:
        healthy: Whether overall health is good.
        checks: List of individual health checks.
        score: Health score (0.0 to 1.0).
    """

    healthy: bool
    checks: list[HealthCheck]
    score: float = 0.0


@dataclass
class HealthChecker:
    """Checks content health and reports status.

    Attributes:
        min_items: Minimum items for healthy status.
        max_stale_hours: Max hours since last update.
    """

    min_items: int = 1
    max_stale_hours: int = 24

    def check(self, items: list[dict[str, Any]]) -> HealthStatus:
        """Run the three built-in health checks on ``items`` and aggregate.

        Runs, in order, appending each ``HealthCheck`` to ``checks``:

        - ``item_count``: healthy when ``len(items) >= self.min_items``.
        - ``scores``: healthy when every item has an ``int``/``float``
          ``"score"`` value, or when ``items`` is empty.
        - ``duplicates``: healthy when the count of unique ``str(id)`` values
          equals ``len(items)`` (i.e. zero duplicates).

        The aggregate ``healthy`` is ``True`` only when all three checks are
        healthy. The aggregate ``score`` is the fraction of healthy checks
        (``sum(healthy) / len(checks)``), rounded to 4 places, or ``0.0`` when
        there are no checks.

        Args:
            items: Content items to check.

        Returns:
            A ``HealthStatus`` with ``healthy`` (all checks passed),
            ``checks`` (the three ``HealthCheck`` results, in the order above),
            and ``score`` (the rounded fraction of healthy checks).
        """
        checks: list[HealthCheck] = []
        checks.append(self._check_item_count(items))
        checks.append(self._check_scores(items))
        checks.append(self._check_duplicates(items))

        healthy = all(c.healthy for c in checks)
        score = sum(1 for c in checks if c.healthy) / len(checks) if checks else 0.0

        return HealthStatus(
            healthy=healthy,
            checks=checks,
            score=round(score, 4),
        )

    def _check_item_count(
        self,
        items: list[dict[str, Any]],
    ) -> HealthCheck:
        """Check if there are enough items."""
        count = len(items)
        healthy = count >= self.min_items
        return HealthCheck(
            check_name="item_count",
            healthy=healthy,
            message=f"{count} items found" if healthy else f"Only {count} items (min: {self.min_items})",
            details={"count": count},
        )

    def _check_scores(
        self,
        items: list[dict[str, Any]],
    ) -> HealthCheck:
        """Check if items have valid scores."""
        scored = [
            i for i in items
            if isinstance(i.get("score"), (int, float))
        ]
        healthy = len(scored) == len(items) or len(items) == 0
        return HealthCheck(
            check_name="scores",
            healthy=healthy,
            message=f"{len(scored)}/{len(items)} items scored",
            details={"scored": len(scored), "total": len(items)},
        )

    def _check_duplicates(
        self,
        items: list[dict[str, Any]],
    ) -> HealthCheck:
        """Check for duplicate items."""
        ids = [str(i.get("id", "")) for i in items]
        unique = len(set(ids))
        duplicates = len(ids) - unique
        healthy = duplicates == 0
        return HealthCheck(
            check_name="duplicates",
            healthy=healthy,
            message=f"{duplicates} duplicates found" if not healthy else "No duplicates",
            details={"duplicates": duplicates, "unique": unique},
        )
