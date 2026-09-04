"""Content notification system for personal-index.

Manages notification rules, triggers, and delivery for
content-related events such as new bookmarks, score changes,
and crawl results.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class NotificationType(Enum):
    """Types of content notifications."""

    NEW_BOOKMARK = "new_bookmark"
    SCORE_CHANGE = "score_change"
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_ERROR = "crawl_error"
    TAG_ADDED = "tag_added"
    COLLECTION_UPDATED = "collection_updated"
    DIGEST_READY = "digest_ready"
    HEALTH_WARNING = "health_warning"
    BACKUP_COMPLETE = "backup_complete"
    SEARCH_RESULT = "search_result"


class NotificationChannel(Enum):
    """Channels for delivering notifications."""

    LOG = "log"
    CONSOLE = "console"
    WEBHOOK = "webhook"
    EMAIL = "email"
    FILE = "file"


@dataclass
class NotificationRule:
    """A rule that determines when notifications are triggered.

    Attributes:
        rule_id: Unique identifier for the rule.
        name: Human-readable rule name.
        notification_type: Type of notification to trigger.
        channels: Channels to deliver to.
        conditions: Conditions that must be met.
        enabled: Whether the rule is active.
        cooldown_seconds: Minimum seconds between notifications.
    """

    rule_id: str
    name: str
    notification_type: NotificationType
    channels: list[NotificationChannel] = field(default_factory=list)
    conditions: dict[str, Any] = field(default_factory=dict)
    enabled: bool = True
    cooldown_seconds: int = 300

    def matches(self, event: dict[str, Any]) -> bool:
        """Check if an event matches this rule's conditions."""
        if not self.enabled:
            return False
        for key, value in self.conditions.items():
            if event.get(key) != value:
                return False
        return True


@dataclass
class Notification:
    """A single notification.

    Attributes:
        notification_id: Unique identifier.
        notification_type: Type of notification.
        title: Notification title.
        message: Notification message body.
        timestamp: When the notification was created.
        channels: Channels to deliver to.
        data: Additional notification data.
        delivered: Whether the notification has been delivered.
        delivered_at: When the notification was delivered.
    """

    notification_id: str
    notification_type: NotificationType
    title: str
    message: str
    timestamp: datetime
    channels: list[NotificationChannel] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)
    delivered: bool = False
    delivered_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "notification_id": self.notification_id,
            "type": self.notification_type.value,
            "title": self.title,
            "message": self.message,
            "timestamp": self.timestamp.isoformat(),
            "channels": [c.value for c in self.channels],
            "data": self.data,
            "delivered": self.delivered,
        }


class NotificationManager:
    """Manages notification rules and delivery state.

    Stores rules, evaluates events against rules to generate
    notifications, and tracks their delivery state.
    """

    def __init__(self) -> None:
        self.rules: list[NotificationRule] = []
        self.notifications: list[Notification] = []
        self._last_sent: dict[str, datetime] = {}
        self._id_counter = 0

    def add_rule(self, rule: NotificationRule) -> None:
        """Add a notification rule."""
        self.rules.append(rule)

    def remove_rule(self, rule_id: str) -> bool:
        """Remove a notification rule by ID."""
        for i, rule in enumerate(self.rules):
            if rule.rule_id == rule_id:
                self.rules.pop(i)
                return True
        return False

    def evaluate_event(self, event: dict[str, Any]) -> list[Notification]:
        """Evaluate an event against all rules and generate notifications.

        Args:
            event: Event data to evaluate.

        Returns:
            List of generated notifications.
        """
        generated = []
        now = datetime.now(timezone.utc)

        for rule in self.rules:
            if not rule.matches(event):
                continue

            # Check cooldown
            last = self._last_sent.get(rule.rule_id)
            if last and (now - last).total_seconds() < rule.cooldown_seconds:
                continue

            notification = self._create_notification(rule, event)
            self.notifications.append(notification)
            self._last_sent[rule.rule_id] = now
            generated.append(notification)

        return generated

    def get_undelivered(self) -> list[Notification]:
        """Get all undelivered notifications."""
        return [n for n in self.notifications if not n.delivered]

    def mark_delivered(self, notification_id: str) -> bool:
        """Mark a notification as delivered."""
        for n in self.notifications:
            if n.notification_id == notification_id:
                n.delivered = True
                n.delivered_at = datetime.now(timezone.utc)
                return True
        return False

    def mark_all_delivered(self) -> int:
        """Mark all undelivered notifications as delivered."""
        count = 0
        for n in self.notifications:
            if not n.delivered:
                n.delivered = True
                n.delivered_at = datetime.now(timezone.utc)
                count += 1
        return count

    def get_recent(
        self,
        limit: int = 10,
        notification_type: NotificationType | None = None,
    ) -> list[Notification]:
        """Get recent notifications, optionally filtered by type."""
        filtered = self.notifications
        if notification_type:
            filtered = [
                n for n in filtered
                if n.notification_type == notification_type
            ]
        return filtered[-limit:]

    def clear_old(self, older_than: datetime) -> int:
        """Clear notifications older than the given time."""
        before = len(self.notifications)
        self.notifications = [
            n for n in self.notifications
            if n.timestamp >= older_than
        ]
        return before - len(self.notifications)

    def _create_notification(
        self,
        rule: NotificationRule,
        event: dict[str, Any],
    ) -> Notification:
        """Create a notification from a rule and event."""
        self._id_counter += 1
        return Notification(
            notification_id=f"notif-{self._id_counter}",
            notification_type=rule.notification_type,
            title=rule.name,
            message=self._format_message(rule, event),
            timestamp=datetime.now(timezone.utc),
            channels=rule.channels,
            data=event,
        )

    def _format_message(
        self,
        rule: NotificationRule,
        event: dict[str, Any],
    ) -> str:
        """Format a notification message."""
        parts = [rule.name]
        for key, value in event.items():
            if key in ("title", "url", "message"):
                parts.append(f"{key}: {value}")
        return ". ".join(parts) if len(parts) > 1 else parts[0]
