"""Content monitor for tracking changes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_monitor.alert import AlertLevel, AlertManager
from personal_index.content_monitor.health import HealthChecker, HealthStatus


@dataclass
class ContentMonitor:
    """Monitors content for changes and health issues.

    Attributes:
        alert_manager: Manages alerts.
        health_checker: Checks content health.
        previous_state: Previous content state for comparison.
    """

    alert_manager: AlertManager = field(default_factory=AlertManager)
    health_checker: HealthChecker = field(default_factory=HealthChecker)
    previous_state: dict[str, dict[str, Any]] = field(default_factory=dict)

    def check_health(
        self,
        items: list[dict[str, Any]],
    ) -> HealthStatus:
        """Check content health and generate alerts.

        Args:
            items: Content items to check.

        Returns:
            HealthStatus with check results.
        """
        status = self.health_checker.check(items)

        if not status.healthy:
            self.alert_manager.add_alert(
                level=AlertLevel.WARNING,
                message=f"Content health check failed: score={status.score}",
                source="health_checker",
                data={"score": status.score, "checks": len(status.checks)},
            )

        return status

    def detect_changes(
        self,
        items: list[dict[str, Any]],
        id_field: str = "id",
    ) -> dict[str, Any]:
        """Detect changes in content since last check.

        Args:
            items: Current content items.
            id_field: Field name for item ID.

        Returns:
            Dictionary with change information.
        """
        current_state = {
            str(item.get(id_field)): item
            for item in items
        }

        added = []
        removed = []
        modified = []

        # Check for added items
        for item_id, item in current_state.items():
            if item_id not in self.previous_state:
                added.append(item)

        # Check for removed items
        for item_id in self.previous_state:
            if item_id not in current_state:
                removed.append(self.previous_state[item_id])

        # Check for modified items
        for item_id, item in current_state.items():
            if item_id in self.previous_state:
                old = self.previous_state[item_id]
                if item != old:
                    modified.append({"id": item_id, "old": old, "new": item})

        # Generate alerts for significant changes
        if added:
            self.alert_manager.add_alert(
                level=AlertLevel.INFO,
                message=f"{len(added)} new items detected",
                source="change_detector",
            )
        if removed:
            self.alert_manager.add_alert(
                level=AlertLevel.WARNING,
                message=f"{len(removed)} items removed",
                source="change_detector",
            )

        # Update state
        self.previous_state = current_state

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "added_count": len(added),
            "removed_count": len(removed),
            "modified_count": len(modified),
        }

    def get_status(self) -> dict[str, Any]:
        """Get overall monitor status.

        Returns:
            Dictionary with monitor status information.
        """
        return {
            "pending_alerts": self.alert_manager.pending_count,
            "total_alerts": len(self.alert_manager.alerts),
            "tracked_items": len(self.previous_state),
        }
