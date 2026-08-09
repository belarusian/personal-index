"""Content offline module - offline access to saved content."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional, Union


class OfflineStatus(str, Enum):
    """Status of an offline content item."""

    AVAILABLE = "available"
    PENDING = "pending"
    FAILED = "failed"
    EXPIRED = "expired"


class OfflinePriority(int, Enum):
    """Priority level for offline content."""

    HIGH = 0
    NORMAL = 1
    LOW = 2


@dataclass
class OfflineContentItem:
    """An item stored for offline access."""

    url: str
    title: str = ""
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    content: Optional[str] = None
    author: str = ""
    published_at: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    status: OfflineStatus = OfflineStatus.AVAILABLE
    priority: OfflinePriority = OfflinePriority.NORMAL
    content_length: int = 0
    expires_at: Optional[str] = None
    last_accessed_at: Optional[str] = None
    access_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: Optional[str] = None

    def __post_init__(self) -> None:
        """Set content_length from content if provided."""
        if self.content is not None and self.content_length == 0:
            self.content_length = len(self.content)

    def mark_available(self, content: str) -> None:
        """Mark the item as available with content."""
        self.status = OfflineStatus.AVAILABLE
        self.content = content
        self.content_length = len(content) if content else 0
        self.error = None

    def mark_failed(self, error: str) -> None:
        """Mark the item as failed."""
        self.status = OfflineStatus.FAILED
        self.error = error

    def mark_expired(self) -> None:
        """Mark the item as expired."""
        self.status = OfflineStatus.EXPIRED
        self.content = None
        self.content_length = 0

    def mark_pending(self) -> None:
        """Mark the item as pending re-download."""
        self.status = OfflineStatus.PENDING
        self.content = None
        self.content_length = 0
        self.error = None

    def record_access(self) -> None:
        """Record an access to this item."""
        self.last_accessed_at = datetime.now(timezone.utc).isoformat()
        self.access_count += 1

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def is_expired(self) -> bool:
        """Check if the item has expired."""
        if not self.expires_at:
            return False
        try:
            exp = datetime.fromisoformat(self.expires_at)
            return datetime.now(timezone.utc) > exp
        except (ValueError, TypeError):
            return False

    def set_expiry_days(self, days: int) -> None:
        """Set expiry to N days from now."""
        self.expires_at = (
            datetime.now(timezone.utc) + timedelta(days=days)
        ).isoformat()

    def get_preview(self, max_length: int = 100) -> str:
        """Get a text preview of the content."""
        if not self.content:
            return ""
        text = self.content
        if len(text) > max_length:
            return text[:max_length]
        return text

    def update_content(self, content: str) -> None:
        """Update the stored content."""
        self.content = content
        self.content_length = len(content) if content else 0
        self.status = OfflineStatus.AVAILABLE
        self.error = None

    def update_metadata(self, title: Optional[str] = None, author: Optional[str] = None) -> None:
        """Update metadata fields."""
        if title is not None:
            self.title = title
        if author is not None:
            self.author = author

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "item_id": self.item_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "published_at": self.published_at,
            "tags": list(self.tags),
            "status": self.status.value,
            "priority": self.priority.name.lower(),
            "content_length": self.content_length,
            "expires_at": self.expires_at,
            "last_accessed_at": self.last_accessed_at,
            "access_count": self.access_count,
            "created_at": self.created_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OfflineContentItem":
        """Deserialize from dictionary."""
        status = data.get("status", "available")
        if isinstance(status, str):
            status = OfflineStatus(status)
        elif not isinstance(status, OfflineStatus):
            status = OfflineStatus.AVAILABLE

        priority = data.get("priority", "normal")
        if isinstance(priority, str):
            priority = OfflinePriority[priority.upper()]
        elif not isinstance(priority, OfflinePriority):
            priority = OfflinePriority.NORMAL

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            item_id=data.get("item_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            title=data.get("title", ""),
            content=data.get("content"),
            author=data.get("author", ""),
            published_at=data.get("published_at"),
            tags=data.get("tags", []),
            status=status,
            priority=priority,
            content_length=data.get("content_length", 0),
            expires_at=data.get("expires_at"),
            last_accessed_at=data.get("last_accessed_at"),
            access_count=data.get("access_count", 0),
            created_at=created_at,
            error=data.get("error"),
        )


@dataclass
class OfflineStore:
    """A store for offline content items."""

    name: str = "default"
    items: list[OfflineContentItem] = field(default_factory=list)
    max_items: int = 1000
    max_storage_bytes: int = 104857600  # 100MB default

    def add_item(self, item: OfflineContentItem) -> None:
        """Add an item, keeping first if URL already exists."""
        existing = self.get_item_by_url(item.url)
        if existing:
            # Keep the first item, don't replace
            return
        self.items.append(item)
        self._enforce_limits()

    def remove_item(self, item_id: str) -> None:
        """Remove an item by ID."""
        self.items = [i for i in self.items if i.item_id != item_id]

    def get_item(self, item_id: str) -> Optional[OfflineContentItem]:
        """Get an item by ID."""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def get_item_by_url(self, url: str) -> Optional[OfflineContentItem]:
        """Get an item by URL."""
        for item in self.items:
            if item.url == url:
                return item
        return None

    def get_available_items(self) -> list[OfflineContentItem]:
        """Get all available items."""
        return [i for i in self.items if i.status == OfflineStatus.AVAILABLE]

    def get_pending_items(self) -> list[OfflineContentItem]:
        """Get all pending items."""
        return [i for i in self.items if i.status == OfflineStatus.PENDING]

    def get_failed_items(self) -> list[OfflineContentItem]:
        """Get all failed items."""
        return [i for i in self.items if i.status == OfflineStatus.FAILED]

    def get_expired_items(self) -> list[OfflineContentItem]:
        """Get all expired items."""
        return [i for i in self.items if i.is_expired()]

    def search(self, query: str) -> list[OfflineContentItem]:
        """Search items by title or URL."""
        query_lower = query.lower()
        results = []
        for item in self.items:
            if query_lower in item.title.lower() or query_lower in item.url.lower():
                results.append(item)
        return results

    def search_by_tag(self, tag: str) -> list[OfflineContentItem]:
        """Search items by tag."""
        return [i for i in self.items if tag in i.tags]

    def _enforce_limits(self) -> None:
        """Enforce max items and storage limits."""
        if len(self.items) > self.max_items:
            self._evict_least_accessed()
        if self.get_total_content_size() > self.max_storage_bytes:
            self._evict_least_accessed()

    def _evict_least_accessed(self) -> None:
        """Evict the least accessed item."""
        if not self.items:
            return
        sorted_items = sorted(self.items, key=lambda i: i.access_count)
        self.items = sorted_items[1:]

    def evict_expired(self) -> None:
        """Remove all expired items."""
        self.items = [i for i in self.items if not i.is_expired()]

    def evict_least_accessed(self) -> None:
        """Manually evict least accessed item."""
        self._evict_least_accessed()

    def get_stats(self) -> dict:
        """Get store statistics."""
        stats = {
            "total": len(self.items),
            "available": 0,
            "pending": 0,
            "failed": 0,
            "expired": 0,
            "total_content_size": self.get_total_content_size(),
        }
        for item in self.items:
            if item.status == OfflineStatus.AVAILABLE:
                stats["available"] += 1
            elif item.status == OfflineStatus.PENDING:
                stats["pending"] += 1
            elif item.status == OfflineStatus.FAILED:
                stats["failed"] += 1
            elif item.status == OfflineStatus.EXPIRED:
                stats["expired"] += 1
        return stats

    def get_total_content_size(self) -> int:
        """Get total size of all content in bytes."""
        return sum(i.content_length for i in self.items)

    def retry_failed(self) -> None:
        """Mark all failed items as pending for retry."""
        for item in self.items:
            if item.status == OfflineStatus.FAILED:
                item.mark_pending()

    def refresh_expired(self) -> None:
        """Mark all expired items as pending for refresh."""
        for item in self.items:
            if item.is_expired():
                item.mark_pending()

    def get_items_sorted_by_access(self) -> list[OfflineContentItem]:
        """Get items sorted by access count (descending)."""
        return sorted(self.items, key=lambda i: i.access_count, reverse=True)

    def get_items_sorted_by_date(self) -> list[OfflineContentItem]:
        """Get items sorted by created date (descending)."""
        return sorted(self.items, key=lambda i: i.created_at, reverse=True)

    def batch_add(self, items_or_urls: Union[list[str], list[OfflineContentItem]], status: OfflineStatus = OfflineStatus.AVAILABLE) -> None:
        """Add multiple items or URLs."""
        if not items_or_urls:
            return
        if isinstance(items_or_urls[0], str):
            for url in items_or_urls:
                item = OfflineContentItem(url=url, status=status)
                self.add_item(item)
        else:
            for item in items_or_urls:
                self.add_item(item)

    def contains_url(self, url: str) -> bool:
        """Check if a URL is in the store."""
        return self.get_item_by_url(url) is not None

    def update_item_content(self, item_id: str, content: str) -> None:
        """Update content for an item."""
        item = self.get_item(item_id)
        if item:
            item.update_content(content)

    def update_item_tags(self, item_id: str, tags: list[str]) -> None:
        """Update tags for an item."""
        item = self.get_item(item_id)
        if item:
            item.tags = list(tags)

    def clear_all(self) -> None:
        """Remove all items."""
        self.items.clear()

    def to_dict(self) -> dict:
        """Serialize the store."""
        return {
            "name": self.name,
            "max_items": self.max_items,
            "max_storage_bytes": self.max_storage_bytes,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "OfflineStore":
        """Deserialize the store."""
        store = cls(
            name=data.get("name", "default"),
            max_items=data.get("max_items", 1000),
            max_storage_bytes=data.get("max_storage_bytes", 104857600),
        )
        store.items = [
            OfflineContentItem.from_dict(item_data)
            for item_data in data.get("items", [])
        ]
        return store
