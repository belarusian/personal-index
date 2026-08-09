"""Content read queue module - queue for reading later."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


class QueueStatus(str, Enum):
    """Status of a queue item."""

    PENDING = "pending"
    READ = "read"
    SKIPPED = "skipped"


class QueuePriority(str, Enum):
    """Priority level for queue items."""

    URGENT = 0
    HIGH = 1
    NORMAL = 2
    LOW = 3


@dataclass
class QueueItem:
    """An item in the read queue."""

    url: str
    item_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    notes: str = ""
    priority: QueuePriority = QueuePriority.NORMAL
    status: QueueStatus = QueueStatus.PENDING
    tags: list[str] = field(default_factory=list)
    due_at: Optional[str] = None
    read_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def mark_read(self) -> None:
        """Mark the item as read."""
        self.status = QueueStatus.READ
        self.read_at = datetime.now(timezone.utc).isoformat()

    def mark_skipped(self) -> None:
        """Mark the item as skipped."""
        self.status = QueueStatus.SKIPPED

    def mark_pending(self) -> None:
        """Mark the item as pending again."""
        self.status = QueueStatus.PENDING
        self.read_at = None

    def is_overdue(self) -> bool:
        """Check if the item is overdue."""
        if self.status != QueueStatus.PENDING:
            return False
        if not self.due_at:
            return False
        try:
            due = datetime.fromisoformat(self.due_at)
            return datetime.now(timezone.utc) > due
        except (ValueError, TypeError):
            return False

    def add_tag(self, tag: str) -> None:
        """Add a tag."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag."""
        if tag in self.tags:
            self.tags.remove(tag)

    def update_notes(self, notes: str) -> None:
        """Update the notes."""
        self.notes = notes

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "item_id": self.item_id,
            "url": self.url,
            "title": self.title,
            "notes": self.notes,
            "priority": self.priority.name.lower(),
            "status": self.status.value,
            "tags": list(self.tags),
            "due_at": self.due_at,
            "read_at": self.read_at,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "QueueItem":
        """Deserialize from dictionary."""
        priority = data.get("priority", "normal")
        if isinstance(priority, str):
            priority = QueuePriority[priority.upper()]
        elif not isinstance(priority, QueuePriority):
            priority = QueuePriority.NORMAL

        status = data.get("status", "pending")
        if isinstance(status, str):
            status = QueueStatus(status)
        elif not isinstance(status, QueueStatus):
            status = QueueStatus.PENDING

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            item_id=data.get("item_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            title=data.get("title", ""),
            notes=data.get("notes", ""),
            priority=priority,
            status=status,
            tags=data.get("tags", []),
            due_at=data.get("due_at"),
            read_at=data.get("read_at"),
            created_at=created_at,
        )


@dataclass
class ReadQueue:
    """A named read queue."""

    name: str
    queue_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    description: str = ""
    items: list[QueueItem] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_item(self, item: QueueItem) -> None:
        """Add an item to the queue."""
        if not any(i.item_id == item.item_id for i in self.items):
            self.items.append(item)

    def remove_item(self, item_id: str) -> None:
        """Remove an item by ID."""
        self.items = [i for i in self.items if i.item_id != item_id]

    def get_pending(self) -> list[QueueItem]:
        """Get all pending items."""
        return [i for i in self.items if i.status == QueueStatus.PENDING]

    def get_read(self) -> list[QueueItem]:
        """Get all read items."""
        return [i for i in self.items if i.status == QueueStatus.READ]

    def get_overdue(self) -> list[QueueItem]:
        """Get all overdue items."""
        return [i for i in self.items if i.is_overdue()]

    def get_sorted(self) -> list[QueueItem]:
        """Get items sorted by priority."""
        return sorted(self.items, key=lambda i: i.priority.value)

    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """Get an item by ID."""
        for item in self.items:
            if item.item_id == item_id:
                return item
        return None

    def item_count(self) -> int:
        """Get total item count."""
        return len(self.items)

    def pending_count(self) -> int:
        """Get pending item count."""
        return len(self.get_pending())

    def clear_read_items(self) -> None:
        """Remove all read items."""
        self.items = [i for i in self.items if i.status != QueueStatus.READ]

    def clear_all(self) -> None:
        """Remove all items."""
        self.items = []

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "queue_id": self.queue_id,
            "name": self.name,
            "description": self.description,
            "items": [i.to_dict() for i in self.items],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReadQueue":
        """Deserialize from dictionary."""
        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        items = [QueueItem.from_dict(idata) for idata in data.get("items", [])]

        return cls(
            queue_id=data.get("queue_id", uuid.uuid4().hex[:12]),
            name=data["name"],
            description=data.get("description", ""),
            items=items,
            created_at=created_at,
        )


class ReadQueueManager:
    """Manages read queues."""

    def __init__(self) -> None:
        self._queues: dict[str, ReadQueue] = {}
        self._item_to_queue: dict[str, str] = {}
        self._url_to_item: dict[str, str] = {}
        # Create default queue
        default = ReadQueue(name="Default")
        self._queues[default.queue_id] = default

    def create_queue(self, name: str, description: str = "") -> str:
        """Create a new queue. Returns the queue ID."""
        queue = ReadQueue(name=name, description=description)
        self._queues[queue.queue_id] = queue
        return queue.queue_id

    def get_queue(self, queue_id: str) -> Optional[ReadQueue]:
        """Get a queue by ID."""
        return self._queues.get(queue_id)

    def get_default_queue(self) -> ReadQueue:
        """Get the default queue."""
        for q in self._queues.values():
            if q.name == "Default":
                return q
        # Create if missing
        default = ReadQueue(name="Default")
        self._queues[default.queue_id] = default
        return default

    def add_to_queue(
        self,
        url: str,
        title: str = "",
        notes: str = "",
        priority: QueuePriority = QueuePriority.NORMAL,
        tags: Optional[list[str]] = None,
        due_at: Optional[str] = None,
        queue_id: Optional[str] = None,
    ) -> str:
        """Add an item to a queue. Returns the item ID."""
        if url in self._url_to_item:
            return self._url_to_item[url]
        item = QueueItem(
            url=url,
            title=title,
            notes=notes,
            priority=priority,
            tags=tags or [],
            due_at=due_at,
        )
        target_queue_id = queue_id or self.get_default_queue().queue_id
        queue = self._queues.get(target_queue_id)
        if queue:
            queue.add_item(item)
        self._item_to_queue[item.item_id] = target_queue_id
        self._url_to_item[url] = item.item_id
        return item.item_id

    def get_item(self, item_id: str) -> Optional[QueueItem]:
        """Get an item by ID."""
        queue_id = self._item_to_queue.get(item_id)
        if queue_id:
            queue = self._queues.get(queue_id)
            if queue:
                return queue.get_item(item_id)
        return None

    def get_item_by_url(self, url: str) -> Optional[QueueItem]:
        """Get an item by URL."""
        item_id = self._url_to_item.get(url)
        if item_id:
            return self.get_item(item_id)
        return None

    def mark_item_read(self, item_id: str) -> None:
        """Mark an item as read."""
        item = self.get_item(item_id)
        if item:
            item.mark_read()

    def mark_item_skipped(self, item_id: str) -> None:
        """Mark an item as skipped."""
        item = self.get_item(item_id)
        if item:
            item.mark_skipped()

    def mark_item_pending(self, item_id: str) -> None:
        """Mark an item as pending."""
        item = self.get_item(item_id)
        if item:
            item.mark_pending()

    def remove_item(self, item_id: str) -> bool:
        """Remove an item. Returns True if removed."""
        queue_id = self._item_to_queue.get(item_id)
        if queue_id:
            queue = self._queues.get(queue_id)
            if queue:
                item = queue.get_item(item_id)
                if item:
                    queue.remove_item(item_id)
                    self._url_to_item.pop(item.url, None)
                    self._item_to_queue.pop(item_id, None)
                    return True
        return False

    def get_pending_items(self) -> list[QueueItem]:
        """Get all pending items across all queues, sorted by priority."""
        pending = []
        for queue in self._queues.values():
            pending.extend(queue.get_pending())
        pending.sort(key=lambda i: i.priority.value)
        return pending

    def get_overdue_items(self) -> list[QueueItem]:
        """Get all overdue items."""
        overdue = []
        for queue in self._queues.values():
            overdue.extend(queue.get_overdue())
        return overdue

    def get_queue_stats(self) -> dict:
        """Get stats across all queues."""
        stats = {"total": 0, "pending": 0, "read": 0, "skipped": 0, "overdue": 0}
        for queue in self._queues.values():
            for item in queue.items:
                stats["total"] += 1
                if item.status == QueueStatus.PENDING:
                    stats["pending"] += 1
                elif item.status == QueueStatus.READ:
                    stats["read"] += 1
                elif item.status == QueueStatus.SKIPPED:
                    stats["skipped"] += 1
                if item.is_overdue():
                    stats["overdue"] += 1
        return stats

    def list_queues(self) -> list[ReadQueue]:
        """List all queues."""
        return list(self._queues.values())

    def delete_queue(self, queue_id: str) -> bool:
        """Delete a queue. Returns True if deleted."""
        queue = self._queues.get(queue_id)
        if queue and queue.name != "Default":
            for item in queue.items:
                self._item_to_queue.pop(item.item_id, None)
                self._url_to_item.pop(item.url, None)
            del self._queues[queue_id]
            return True
        return False

    def move_item_to_queue(self, item_id: str, target_queue_id: str) -> None:
        """Move an item to a different queue."""
        source_queue_id = self._item_to_queue.get(item_id)
        if not source_queue_id:
            return
        source_queue = self._queues.get(source_queue_id)
        target_queue = self._queues.get(target_queue_id)
        if not source_queue or not target_queue:
            return
        item = source_queue.get_item(item_id)
        if item:
            source_queue.remove_item(item_id)
            target_queue.add_item(item)
            self._item_to_queue[item_id] = target_queue_id

    def update_item_notes(self, item_id: str, notes: str) -> None:
        """Update item notes."""
        item = self.get_item(item_id)
        if item:
            item.update_notes(notes)

    def update_item_priority(self, item_id: str, priority: QueuePriority) -> None:
        """Update item priority."""
        item = self.get_item(item_id)
        if item:
            item.priority = priority

    def update_item_due_date(self, item_id: str, due_at: str) -> None:
        """Update item due date."""
        item = self.get_item(item_id)
        if item:
            item.due_at = due_at

    def clear_read_items(self) -> None:
        """Clear all read items across all queues."""
        for queue in self._queues.values():
            queue.clear_read_items()

    def get_items_by_tag(self, tag: str) -> list[QueueItem]:
        """Get items with a specific tag."""
        result = []
        for queue in self._queues.values():
            for item in queue.items:
                if tag in item.tags:
                    result.append(item)
        return result

    def batch_add(self, urls: list[str]) -> list[str]:
        """Add multiple URLs to the queue. Returns item IDs."""
        return [self.add_to_queue(url) for url in urls]

    def to_dict(self) -> dict:
        """Serialize the manager state."""
        return {
            "queues": {qid: q.to_dict() for qid, q in self._queues.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReadQueueManager":
        """Deserialize manager state."""
        mgr = cls()
        mgr._queues = {}
        mgr._item_to_queue = {}
        mgr._url_to_item = {}
        for qid, qdata in data.get("queues", {}).items():
            queue = ReadQueue.from_dict(qdata)
            mgr._queues[qid] = queue
            for item in queue.items:
                mgr._item_to_queue[item.item_id] = qid
                mgr._url_to_item[item.url] = item.item_id
        return mgr
