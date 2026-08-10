"""Notification system for personal index events."""

from __future__ import annotations

import json
import logging
import os
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List

logger = logging.getLogger(__name__)


class NotificationLevel(Enum):
    """Severity levels for notifications."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class NotificationType(Enum):
    """Types of notifications."""
    CRAWL_COMPLETE = "crawl_complete"
    CRAWL_ERROR = "crawl_error"
    SEARCH_HIT = "search_hit"
    NEW_CONTENT = "new_content"
    INTEREST_MATCH = "interest_match"
    BACKUP_COMPLETE = "backup_complete"
    BACKUP_ERROR = "backup_error"
    SCHEDULE_TRIGGER = "schedule_trigger"
    RATE_LIMIT = "rate_limit"
    STORAGE_FULL = "storage_full"


@dataclass
class Notification:
    """A single notification event."""
    notification_id: str = ""
    notification_type: str = ""
    level: str = "info"
    title: str = ""
    message: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    read: bool = False

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        if not self.notification_id:
            self.notification_id = f"notif_{int(time.time() * 1000)}_{id(self) % 10000}"

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the notification to a dictionary.

        Returns:
            Dictionary representation of the notification.
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Notification:
        """Create a Notification from a dictionary.

        Args:
            data: Dictionary with notification fields.

        Returns:
            A new Notification instance.
        """
        return cls(**data)


class NotificationHandler(ABC):
    """Abstract base for notification handlers."""

    @abstractmethod
    def handle(self, notification: Notification) -> bool:
        """Handle a notification. Return True if handled successfully."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Clean up resources."""
        pass


class ConsoleHandler(NotificationHandler):
    """Print notifications to console."""

    def __init__(self, colors: bool = True):
        self.colors = colors

    def handle(self, notification: Notification) -> bool:
        """Print the notification to console.

        Args:
            notification: The notification to display.

        Returns:
            True if handled successfully.
        """
        prefix = {
            NotificationLevel.INFO: "[INFO]",
            NotificationLevel.WARNING: "[WARN]",
            NotificationLevel.ERROR: "[ERROR]",
            NotificationLevel.CRITICAL: "[CRIT]",
        }
        label = prefix.get(NotificationLevel(notification.level), "[????]")
        print(f"  {label} {notification.title}: {notification.message}")
        return True

    def close(self) -> None:
        """No cleanup needed for console handler."""
        pass


class FileHandler(NotificationHandler):
    """Write notifications to a log file."""

    def __init__(self, filepath: str = "~/.personal_index/notifications.log"):
        self.filepath = os.path.expanduser(filepath)
        Path(self.filepath).parent.mkdir(parents=True, exist_ok=True)

    def handle(self, notification: Notification) -> bool:
        """Append the notification as JSON to the log file.

        Args:
            notification: The notification to write.

        Returns:
            True if written successfully.
        """
        try:
            with open(self.filepath, "a") as f:
                f.write(json.dumps(notification.to_dict()) + "\n")
            return True
        except OSError as e:
            logger.error(f"Failed to write notification: {e}")
            return False

    def close(self) -> None:
        """No cleanup needed for file handler."""
        pass


class InMemoryHandler(NotificationHandler):
    """Store notifications in memory for testing/inspection."""

    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self._notifications: List[Notification] = []

    def handle(self, notification: Notification) -> bool:
        """Store the notification in memory.

        Args:
            notification: The notification to store.

        Returns:
            True if handled successfully.
        """
        self._notifications.append(notification)
        if len(self._notifications) > self.max_size:
            self._notifications = self._notifications[-self.max_size:]
        return True

    def get_all(self) -> List[Notification]:
        """Get all stored notifications.

        Returns:
            List of all notifications.
        """
        return list(self._notifications)

    def get_unread(self) -> List[Notification]:
        """Get all unread notifications.

        Returns:
            List of unread notifications.
        """
        return [n for n in self._notifications if not n.read]

    def mark_all_read(self) -> int:
        """Mark all notifications as read.

        Returns:
            Number of notifications marked as read.
        """
        count = 0
        for n in self._notifications:
            if not n.read:
                n.read = True
                count += 1
        return count

    def clear(self) -> int:
        """Clear all stored notifications.

        Returns:
            Number of notifications cleared.
        """
        count = len(self._notifications)
        self._notifications.clear()
        return count

    def close(self) -> None:
        """Clear all stored notifications."""
        self._notifications.clear()


class NotificationManager:
    """Central notification manager that dispatches to handlers."""

    def __init__(self):
        self._handlers: List[NotificationHandler] = []
        self._filters: List[Callable[[Notification], bool]] = []

    def add_handler(self, handler: NotificationHandler) -> None:
        """Add a notification handler."""
        self._handlers.append(handler)

    def remove_handler(self, handler: NotificationHandler) -> bool:
        """Remove a notification handler."""
        if handler in self._handlers:
            self._handlers.remove(handler)
            return True
        return False

    def add_filter(self, filter_fn: Callable[[Notification], bool]) -> None:
        """Add a filter. Notifications passing the filter are dispatched."""
        self._filters.append(filter_fn)

    def notify(self, notification: Notification) -> int:
        """Dispatch a notification to all handlers. Returns count of successful deliveries."""
        if self._filters and not all(f(notification) for f in self._filters):
            return 0
        success_count = 0
        for handler in self._handlers:
            try:
                if handler.handle(notification):
                    success_count += 1
            except Exception as e:
                logger.error(f"Handler {handler.__class__.__name__} failed: {e}")
        return success_count

    def notify_crawl_complete(self, url: str, pages_found: int, duration: float) -> None:
        """Send a crawl complete notification."""
        self.notify(Notification(
            notification_type=NotificationType.CRAWL_COMPLETE.value,
            level=NotificationLevel.INFO.value,
            title="Crawl Complete",
            message=f"Crawled {url}: {pages_found} pages in {duration:.1f}s",
            metadata={"url": url, "pages_found": pages_found, "duration": duration},
        ))

    def notify_crawl_error(self, url: str, error: str) -> None:
        """Send a crawl error notification."""
        self.notify(Notification(
            notification_type=NotificationType.CRAWL_ERROR.value,
            level=NotificationLevel.ERROR.value,
            title="Crawl Error",
            message=f"Failed to crawl {url}: {error}",
            metadata={"url": url, "error": error},
        ))

    def notify_new_content(self, url: str, title: str, matched_interests: List[str]) -> None:
        """Send a new content notification."""
        self.notify(Notification(
            notification_type=NotificationType.NEW_CONTENT.value,
            level=NotificationLevel.INFO.value,
            title="New Content Found",
            message=f"New page: {title} ({url})",
            metadata={"url": url, "title": title, "matched_interests": matched_interests},
        ))

    def notify_interest_match(self, url: str, interest: str, score: float) -> None:
        """Send an interest match notification."""
        self.notify(Notification(
            notification_type=NotificationType.INTEREST_MATCH.value,
            level=NotificationLevel.INFO.value,
            title="Interest Match",
            message=f"'{interest}' matched at {url} (score: {score:.2f})",
            metadata={"url": url, "interest": interest, "score": score},
        ))

    def close(self) -> None:
        """Close all handlers."""
        for handler in self._handlers:
            handler.close()
        self._handlers.clear()
