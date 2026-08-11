"""Alert management for content monitoring."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class AlertLevel(Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Alert:
    """A content monitoring alert.

    Attributes:
        alert_id: Unique alert identifier.
        level: Alert severity level.
        message: Alert message.
        source: Source of the alert.
        timestamp: When the alert was created.
        data: Additional alert data.
        acknowledged: Whether the alert has been acknowledged.
    """

    alert_id: str
    level: AlertLevel
    message: str
    source: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: dict[str, Any] = field(default_factory=dict)
    acknowledged: bool = False


@dataclass
class AlertManager:
    """Manages content monitoring alerts.

    Attributes:
        alerts: List of alerts.
        max_alerts: Maximum number of alerts to retain.
    """

    alerts: list[Alert] = field(default_factory=list)
    max_alerts: int = 1000

    def add_alert(
        self,
        level: AlertLevel,
        message: str,
        source: str,
        data: dict[str, Any] | None = None,
    ) -> Alert:
        """Add a new alert.

        Args:
            level: Alert severity level.
            message: Alert message.
            source: Source of the alert.
            data: Additional alert data.

        Returns:
            The created Alert.
        """
        alert = Alert(
            alert_id=f"alert_{len(self.alerts)}",
            level=level,
            message=message,
            source=source,
            data=data or {},
        )
        self.alerts.append(alert)

        # Enforce max alerts
        if len(self.alerts) > self.max_alerts:
            self.alerts = self.alerts[-self.max_alerts:]

        return alert

    def get_alerts(
        self,
        level: AlertLevel | None = None,
        acknowledged: bool | None = None,
    ) -> list[Alert]:
        """Get alerts filtered by criteria.

        Args:
            level: Filter by alert level.
            acknowledged: Filter by acknowledgment status.

        Returns:
            List of matching alerts.
        """
        result = self.alerts
        if level is not None:
            result = [a for a in result if a.level == level]
        if acknowledged is not None:
            result = [a for a in result if a.acknowledged == acknowledged]
        return result

    def acknowledge(self, alert_id: str) -> bool:
        """Acknowledge an alert.

        Args:
            alert_id: Alert identifier.

        Returns:
            True if alert was found and acknowledged.
        """
        for alert in self.alerts:
            if alert.alert_id == alert_id:
                alert.acknowledged = True
                return True
        return False

    def clear_acknowledged(self) -> int:
        """Clear all acknowledged alerts.

        Returns:
            Number of alerts cleared.
        """
        before = len(self.alerts)
        self.alerts = [a for a in self.alerts if not a.acknowledged]
        return before - len(self.alerts)

    @property
    def pending_count(self) -> int:
        """Number of unacknowledged alerts."""
        return sum(1 for a in self.alerts if not a.acknowledged)
