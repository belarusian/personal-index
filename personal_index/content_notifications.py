"""Content notifications - in-app notification system."""

from __future__ import annotations

import uuid
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class NotificationType(str, Enum):
    """Types of notifications."""
    ITEM_SAVED = "item_saved"
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_ERROR = "crawl_error"
    INDEX_UPDATE = "index_update"
    SYSTEM = "system"
    ALERT = "alert"


class NotificationLevel(str, Enum):
    """Severity level of a notification."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"

    @property
    def severity(self) -> int:
        """Numeric severity for sorting/filtering."""
        severities = {
            NotificationLevel.INFO: 0,
            NotificationLevel.SUCCESS: 1,
            NotificationLevel.WARNING: 2,
            NotificationLevel.ERROR: 3,
        }
        return severities.get(self, 0)


@dataclass
class Notification:
    """An in-app notification."""
    title: str
    message: str
    notification_type: NotificationType
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    level: NotificationLevel = NotificationLevel.INFO
    data: dict = field(default_factory=dict)
    read: bool = False
    read_at: Optional[str] = None
    created_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    ttl_days: Optional[int] = None

    def mark_read(self) -> None:
        """Mark this notification as read."""
        self.read = True
        self.read_at = datetime.now(timezone.utc).isoformat()

    def mark_unread(self) -> None:
        """Mark this notification as unread."""
        self.read = False
        self.read_at = None

    def is_expired(self) -> bool:
        """Check if the notification has expired."""
        if self.ttl_days is None:
            return False
        expiry = self.created_at + __import__('datetime').timedelta(days=self.ttl_days)
        return datetime.now(timezone.utc) > expiry

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "message": self.message,
            "notification_type": self.notification_type.value,
            "level": self.level.value,
            "data": self.data,
            "read": self.read,
            "read_at": self.read_at,
            "created_at": self.created_at.isoformat(),
            "ttl_days": self.ttl_days,
        }


@dataclass
class NotificationFilter:
    """Filter criteria for notifications."""
    types: list[NotificationType] = field(default_factory=list)
    levels: list[NotificationLevel] = field(default_factory=list)
    unread_only: bool = False

    def matches(self, notification: Notification) -> bool:
        """Check if a notification matches this filter."""
        if self.types and notification.notification_type not in self.types:
            return False
        if self.levels and notification.level not in self.levels:
            return False
        if self.unread_only and notification.read:
            return False
        return True


@dataclass
class NotificationPreferences:
    """User notification preferences."""
    enabled: bool = True
    enabled_types: list[NotificationType] = field(
        default_factory=lambda: list(NotificationType)
    )

    def disable_type(self, notification_type: NotificationType) -> None:
        """Disable notifications of a specific type."""
        if notification_type in self.enabled_types:
            self.enabled_types.remove(notification_type)

    def enable_type(self, notification_type: NotificationType) -> None:
        """Enable notifications of a specific type."""
        if notification_type not in self.enabled_types:
            self.enabled_types.append(notification_type)

    def should_notify(self, notification_type: NotificationType) -> bool:
        """Check if notifications should be sent for this type."""
        if not self.enabled:
            return False
        return notification_type in self.enabled_types

    def to_dict(self) -> dict:
        return {
            "enabled": self.enabled,
            "enabled_types": [t.value for t in self.enabled_types],
        }


class NotificationStore:
    """Manages in-app notifications."""

    def __init__(self):
        self._notifications: dict[str, Notification] = {}
        self._preferences = NotificationPreferences()

    def add(self, notification: Notification) -> None:
        """Add a notification."""
        self._notifications[notification.id] = notification

    def get(self, notification_id: str) -> Optional[Notification]:
        """Get a notification by ID."""
        return self._notifications.get(notification_id)

    def list_all(self) -> list[Notification]:
        """List all notifications, newest first."""
        return sorted(
            self._notifications.values(),
            key=lambda n: n.created_at,
            reverse=True,
        )

    def list_unread(self) -> list[Notification]:
        """List unread notifications."""
        return [
            n for n in self.list_all()
            if not n.read
        ]

    def list_by_type(self, notification_type: NotificationType) -> list[Notification]:
        """List notifications of a specific type."""
        return [
            n for n in self.list_all()
            if n.notification_type == notification_type
        ]

    def mark_read(self, notification_id: str) -> bool:
        """Mark a notification as read."""
        notif = self._notifications.get(notification_id)
        if notif:
            notif.mark_read()
            return True
        return False

    def mark_all_read(self) -> int:
        """Mark all notifications as read. Returns count of marked."""
        count = 0
        for notif in self._notifications.values():
            if not notif.read:
                notif.mark_read()
                count += 1
        return count

    def delete(self, notification_id: str) -> bool:
        """Delete a notification."""
        if notification_id in self._notifications:
            del self._notifications[notification_id]
            return True
        return False

    def cleanup_expired(self) -> int:
        """Remove expired notifications. Returns count removed."""
        expired_ids = [
            nid for nid, n in self._notifications.items()
            if n.is_expired()
        ]
        for nid in expired_ids:
            del self._notifications[nid]
        return len(expired_ids)

    def filter(self, notification_filter: NotificationFilter) -> list[Notification]:
        """Filter notifications using a NotificationFilter."""
        return [
            n for n in self.list_all()
            if notification_filter.matches(n)
        ]

    def get_preferences(self) -> NotificationPreferences:
        """Get notification preferences."""
        return self._preferences

    def set_preferences(self, preferences: NotificationPreferences) -> None:
        """Set notification preferences."""
        self._preferences = preferences

    @property
    def unread_count(self) -> int:
        return sum(1 for n in self._notifications.values() if not n.read)

    @property
    def total_count(self) -> int:
        return len(self._notifications)
