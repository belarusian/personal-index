"""Content audit module - Audit logging, tracking, and reporting."""

from __future__ import annotations

import datetime
from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class AuditEventType(str, Enum):
    """Types of auditable events."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    ACCESS = "access"
    EXPORT = "export"
    LOGIN = "login"
    LOGOUT = "logout"
    CONFIG_CHANGE = "config_change"


class AuditLogLevel(str, Enum):
    """Log severity levels for audit entries."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    @property
    def level(self) -> int:
        """Return numeric severity level."""
        levels = {"info": 0, "warning": 1, "error": 2, "critical": 3}
        return levels[self.value]


@dataclass
class AuditEntry:
    """A single audit log entry."""

    event_type: AuditEventType
    resource_type: str
    resource_id: str
    user_id: str
    entry_id: str = field(default_factory=lambda: __import__("uuid").uuid4().hex[:12])
    timestamp: str = field(
        default_factory=lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    log_level: AuditLogLevel = AuditLogLevel.INFO
    details: dict[str, Any] = field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    session_id: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        """Convert entry to dictionary.

        Returns:
            Dictionary representation of the entry.
        """
        return {
            "entry_id": self.entry_id,
            "event_type": self.event_type.value,
            "resource_type": self.resource_type,
            "resource_id": self.resource_id,
            "user_id": self.user_id,
            "timestamp": self.timestamp,
            "log_level": self.log_level.value,
            "details": self.details,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "session_id": self.session_id,
        }


@dataclass
class AuditQuery:
    """Query parameters for filtering audit log entries."""

    event_type: Optional[AuditEventType] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    user_id: Optional[str] = None
    min_level: Optional[AuditLogLevel] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: int = 100


class AuditLog:
    """In-memory audit log with filtering and management."""

    def __init__(self, max_entries: int = 10000) -> None:
        self.entries: list[AuditEntry] = []
        self.max_entries = max_entries

    def add_entry(self, entry: AuditEntry) -> None:
        """Add an audit entry to the log.

        Args:
            entry: AuditEntry to add.
        """
        self.entries.append(entry)
        if len(self.entries) > self.max_entries:
            self.clear_old_entries(self.max_entries)

    def filter(
        self,
        event_type: Optional[AuditEventType] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        min_level: Optional[AuditLogLevel] = None,
    ) -> list[AuditEntry]:
        """Filter audit entries by criteria.

        Args:
            event_type: Filter by event type.
            resource_type: Filter by resource type.
            resource_id: Filter by resource ID.
            user_id: Filter by user ID.
            min_level: Minimum log level to include.

        Returns:
            List of matching AuditEntry objects.
        """
        results = self.entries
        if event_type is not None:
            results = [e for e in results if e.event_type == event_type]
        if resource_type is not None:
            results = [e for e in results if e.resource_type == resource_type]
        if resource_id is not None:
            results = [e for e in results if e.resource_id == resource_id]
        if user_id is not None:
            results = [e for e in results if e.user_id == user_id]
        if min_level is not None:
            results = [e for e in results if e.log_level.level >= min_level.level]
        return results

    def get_recent(self, count: int = 10) -> list[AuditEntry]:
        """Get the most recent entries.

        Args:
            count: Number of recent entries to return.

        Returns:
            List of most recent AuditEntry objects.
        """
        return list(reversed(self.entries[:count]))

    def clear_old_entries(self, max_entries: int) -> None:
        """Keep only the most recent entries up to max_entries.

        Args:
            max_entries: Maximum number of entries to retain.
        """
        if len(self.entries) > max_entries:
            self.entries = self.entries[-max_entries:]

    def get_all_entries(self) -> list[AuditEntry]:
        """Get all audit entries.

        Returns:
            List of all AuditEntry objects.
        """
        return list(self.entries)


class AuditReporter:
    """Generates reports and detects anomalies from audit logs."""

    ANOMALY_THRESHOLD = 10  # Events in short period triggers anomaly

    def generate_summary(self, audit_log: AuditLog) -> dict[str, Any]:
        """Generate a summary of audit log activity.

        Args:
            audit_log: AuditLog to summarize.

        Returns:
            Summary dictionary with counts and statistics.
        """
        entries = audit_log.get_all_entries()
        event_counts = Counter(e.event_type.value for e in entries)
        user_counts = Counter(e.user_id for e in entries)
        level_counts = Counter(e.log_level.value for e in entries)

        return {
            "total_entries": len(entries),
            "event_counts": dict(event_counts),
            "user_counts": dict(user_counts),
            "level_counts": dict(level_counts),
            "earliest": entries[0].timestamp if entries else None,
            "latest": entries[-1].timestamp if entries else None,
        }

    def generate_report_by_user(
        self, audit_log: AuditLog, user_id: str
    ) -> list[dict[str, Any]]:
        """Generate a report of all actions by a specific user.

        Args:
            audit_log: AuditLog to query.
            user_id: User ID to filter by.

        Returns:
            List of entry dictionaries for the user.
        """
        entries = audit_log.filter(user_id=user_id)
        return [e.to_dict() for e in entries]

    def detect_anomalies(
        self, audit_log: AuditLog, threshold: Optional[int] = None
    ) -> list[dict[str, Any]]:
        """Detect anomalous patterns in audit logs.

        Args:
            audit_log: AuditLog to analyze.
            threshold: Override default anomaly threshold.

        Returns:
            List of anomaly descriptions.
        """
        threshold = threshold or self.ANOMALY_THRESHOLD
        anomalies: list[dict[str, Any]] = []
        entries = audit_log.get_all_entries()

        # Check for excessive deletions
        delete_entries = audit_log.filter(event_type=AuditEventType.DELETE)
        if len(delete_entries) >= threshold:
            anomalies.append({
                "type": "excessive_deletions",
                "count": len(delete_entries),
                "threshold": threshold,
                "description": f"Detected {len(delete_entries)} delete events (threshold: {threshold})",
            })

        # Check for excessive errors
        error_entries = audit_log.filter(min_level=AuditLogLevel.ERROR)
        if len(error_entries) >= threshold:
            anomalies.append({
                "type": "excessive_errors",
                "count": len(error_entries),
                "threshold": threshold,
                "description": f"Detected {len(error_entries)} error-level events (threshold: {threshold})",
            })

        # Check for single user with many events
        user_counts = Counter(e.user_id for e in entries)
        for user_id, count in user_counts.items():
            if count >= threshold * 2:
                anomalies.append({
                    "type": "high_activity_user",
                    "user_id": user_id,
                    "count": count,
                    "description": f"User {user_id} has {count} events",
                })

        return anomalies
