"""Tests for content_read_queue module - queue for reading later."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_read_queue import (
    QueueItem,
    ReadQueue,
    ReadQueueManager,
    QueueStatus,
    QueuePriority,
)


class TestQueueItem:
    """Tests for QueueItem dataclass."""

    def test_create_queue_item_basic(self):
        item = QueueItem(url="https://example.com/article")
        assert item.url == "https://example.com/article"
        assert item.item_id is not None
        assert item.status == QueueStatus.PENDING
        assert item.priority == QueuePriority.NORMAL
        assert item.created_at is not None

    def test_create_queue_item_with_title(self):
        item = QueueItem(
            url="https://example.com/article",
            title="My Article",
        )
        assert item.title == "My Article"

    def test_create_queue_item_with_notes(self):
        item = QueueItem(
            url="https://example.com/article",
            notes="Read this later",
        )
        assert item.notes == "Read this later"

    def test_create_queue_item_high_priority(self):
        item = QueueItem(
            url="https://example.com/article",
            priority=QueuePriority.HIGH,
        )
        assert item.priority == QueuePriority.HIGH

    def test_create_queue_item_low_priority(self):
        item = QueueItem(
            url="https://example.com/article",
            priority=QueuePriority.LOW,
        )
        assert item.priority == QueuePriority.LOW

    def test_create_queue_item_with_due_date(self):
        due = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        item = QueueItem(
            url="https://example.com/article",
            due_at=due,
        )
        assert item.due_at == due

    def test_create_queue_item_with_tags(self):
        item = QueueItem(
            url="https://example.com/article",
            tags=["tech", "important"],
        )
        assert item.tags == ["tech", "important"]

    def test_create_queue_item_read(self):
        item = QueueItem(
            url="https://example.com/article",
            status=QueueStatus.READ,
        )
        assert item.status == QueueStatus.READ

    def test_create_queue_item_skipped(self):
        item = QueueItem(
            url="https://example.com/article",
            status=QueueStatus.SKIPPED,
        )
        assert item.status == QueueStatus.SKIPPED

    def test_queue_item_to_dict(self):
        item = QueueItem(
            url="https://example.com/article",
            title="Test",
            priority=QueuePriority.HIGH,
            tags=["tag1"],
        )
        d = item.to_dict()
        assert d["url"] == "https://example.com/article"
        assert d["title"] == "Test"
        assert d["priority"] == "high"
        assert d["tags"] == ["tag1"]

    def test_queue_item_from_dict(self):
        data = {
            "item_id": "i1",
            "url": "https://example.com/article",
            "title": "Test Article",
            "notes": "Read this",
            "priority": "high",
            "status": "pending",
            "tags": ["tech"],
            "due_at": "2024-02-01T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00",
            "read_at": None,
        }
        item = QueueItem.from_dict(data)
        assert item.item_id == "i1"
        assert item.title == "Test Article"
        assert item.priority == QueuePriority.HIGH
        assert item.status == QueueStatus.PENDING
        assert item.tags == ["tech"]

    def test_queue_item_from_dict_defaults(self):
        data = {"url": "https://example.com/minimal"}
        item = QueueItem.from_dict(data)
        assert item.status == QueueStatus.PENDING
        assert item.priority == QueuePriority.NORMAL
        assert item.title == ""

    def test_queue_item_mark_read(self):
        item = QueueItem(url="https://example.com/article")
        item.mark_read()
        assert item.status == QueueStatus.READ
        assert item.read_at is not None

    def test_queue_item_mark_skipped(self):
        item = QueueItem(url="https://example.com/article")
        item.mark_skipped()
        assert item.status == QueueStatus.SKIPPED

    def test_queue_item_mark_pending(self):
        item = QueueItem(url="https://example.com/article")
        item.mark_read()
        item.mark_pending()
        assert item.status == QueueStatus.PENDING

    def test_queue_item_is_overdue(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        item = QueueItem(
            url="https://example.com/article",
            due_at=past,
            status=QueueStatus.PENDING,
        )
        assert item.is_overdue() is True

    def test_queue_item_is_not_overdue(self):
        future = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        item = QueueItem(
            url="https://example.com/article",
            due_at=future,
            status=QueueStatus.PENDING,
        )
        assert item.is_overdue() is False

    def test_queue_item_is_not_overdue_no_due(self):
        item = QueueItem(url="https://example.com/article")
        assert item.is_overdue() is False

    def test_queue_item_is_not_overdue_when_read(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        item = QueueItem(
            url="https://example.com/article",
            due_at=past,
            status=QueueStatus.READ,
        )
        assert item.is_overdue() is False

    def test_queue_item_add_tag(self):
        item = QueueItem(url="https://example.com/article")
        item.add_tag("tech")
        assert "tech" in item.tags

    def test_queue_item_add_duplicate_tag(self):
        item = QueueItem(url="https://example.com/article")
        item.add_tag("tech")
        item.add_tag("tech")
        assert item.tags.count("tech") == 1

    def test_queue_item_remove_tag(self):
        item = QueueItem(
            url="https://example.com/article",
            tags=["tech", "news"],
        )
        item.remove_tag("tech")
        assert "tech" not in item.tags
        assert "news" in item.tags

    def test_queue_item_update_notes(self):
        item = QueueItem(url="https://example.com/article")
        item.update_notes("Updated notes")
        assert item.notes == "Updated notes"

    def test_queue_item_priority_value(self):
        assert QueuePriority.URGENT.value < QueuePriority.HIGH.value
        assert QueuePriority.HIGH.value < QueuePriority.NORMAL.value
        assert QueuePriority.NORMAL.value < QueuePriority.LOW.value


class TestReadQueue:
    """Tests for ReadQueue class."""

    def test_create_queue(self):
        q = ReadQueue(name="My Queue")
        assert q.name == "My Queue"
        assert q.queue_id is not None
        assert q.items == []

    def test_create_queue_with_description(self):
        q = ReadQueue(name="My Queue", description="Reading list")
        assert q.description == "Reading list"

    def test_queue_add_item(self):
        q = ReadQueue(name="My Queue")
        item = QueueItem(url="https://example.com/article")
        q.add_item(item)
        assert len(q.items) == 1

    def test_queue_add_duplicate_item(self):
        q = ReadQueue(name="My Queue")
        item = QueueItem(url="https://example.com/article")
        q.add_item(item)
        q.add_item(item)
        assert len(q.items) == 1

    def test_queue_remove_item(self):
        q = ReadQueue(name="My Queue")
        item = QueueItem(url="https://example.com/article")
        q.add_item(item)
        q.remove_item(item.item_id)
        assert len(q.items) == 0

    def test_queue_remove_item_not_found(self):
        q = ReadQueue(name="My Queue")
        q.remove_item("nonexistent")
        assert len(q.items) == 0

    def test_queue_get_pending(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", status=QueueStatus.PENDING))
        q.add_item(QueueItem(url="https://example.com/b", status=QueueStatus.READ))
        pending = q.get_pending()
        assert len(pending) == 1

    def test_queue_get_read(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", status=QueueStatus.READ))
        q.add_item(QueueItem(url="https://example.com/b", status=QueueStatus.PENDING))
        read = q.get_read()
        assert len(read) == 1

    def test_queue_get_overdue(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", due_at=past))
        q.add_item(QueueItem(url="https://example.com/b"))
        overdue = q.get_overdue()
        assert len(overdue) == 1

    def test_queue_get_sorted(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", priority=QueuePriority.LOW))
        q.add_item(QueueItem(url="https://example.com/b", priority=QueuePriority.URGENT))
        q.add_item(QueueItem(url="https://example.com/c", priority=QueuePriority.HIGH))
        sorted_items = q.get_sorted()
        assert sorted_items[0].priority == QueuePriority.URGENT
        assert sorted_items[1].priority == QueuePriority.HIGH
        assert sorted_items[2].priority == QueuePriority.LOW

    def test_queue_get_item(self):
        q = ReadQueue(name="My Queue")
        item = QueueItem(url="https://example.com/article")
        q.add_item(item)
        found = q.get_item(item.item_id)
        assert found is not None
        assert found.url == "https://example.com/article"

    def test_queue_get_item_not_found(self):
        q = ReadQueue(name="My Queue")
        found = q.get_item("nonexistent")
        assert found is None

    def test_queue_item_count(self):
        q = ReadQueue(name="My Queue")
        assert q.item_count() == 0
        q.add_item(QueueItem(url="https://example.com/a"))
        q.add_item(QueueItem(url="https://example.com/b"))
        assert q.item_count() == 2

    def test_queue_pending_count(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", status=QueueStatus.PENDING))
        q.add_item(QueueItem(url="https://example.com/b", status=QueueStatus.READ))
        assert q.pending_count() == 1

    def test_queue_to_dict(self):
        q = ReadQueue(name="My Queue", description="Test")
        item = QueueItem(url="https://example.com/article")
        q.add_item(item)
        d = q.to_dict()
        assert d["name"] == "My Queue"
        assert d["description"] == "Test"
        assert len(d["items"]) == 1

    def test_queue_from_dict(self):
        data = {
            "queue_id": "q1",
            "name": "My Queue",
            "description": "Test",
            "items": [{
                "item_id": "i1",
                "url": "https://example.com/article",
                "title": "Test",
                "status": "pending",
                "priority": "normal",
                "created_at": "2024-01-01T00:00:00+00:00",
            }],
            "created_at": "2024-01-01T00:00:00+00:00",
        }
        q = ReadQueue.from_dict(data)
        assert q.queue_id == "q1"
        assert q.name == "My Queue"
        assert len(q.items) == 1

    def test_queue_from_dict_defaults(self):
        data = {"name": "Minimal"}
        q = ReadQueue.from_dict(data)
        assert q.description == ""
        assert q.items == []

    def test_queue_clear_read_items(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a", status=QueueStatus.READ))
        q.add_item(QueueItem(url="https://example.com/b", status=QueueStatus.PENDING))
        q.clear_read_items()
        assert q.item_count() == 1
        assert q.items[0].status == QueueStatus.PENDING

    def test_queue_clear_all(self):
        q = ReadQueue(name="My Queue")
        q.add_item(QueueItem(url="https://example.com/a"))
        q.add_item(QueueItem(url="https://example.com/b"))
        q.clear_all()
        assert q.item_count() == 0


class TestReadQueueManager:
    """Tests for ReadQueueManager class."""

    def test_create_queue(self):
        mgr = ReadQueueManager()
        qid = mgr.create_queue("My Queue")
        queue = mgr.get_queue(qid)
        assert queue is not None
        assert queue.name == "My Queue"

    def test_create_queue_with_description(self):
        mgr = ReadQueueManager()
        qid = mgr.create_queue("My Queue", description="Reading list")
        queue = mgr.get_queue(qid)
        assert queue.description == "Reading list"

    def test_get_default_queue(self):
        mgr = ReadQueueManager()
        queue = mgr.get_default_queue()
        assert queue is not None
        assert queue.name == "Default"

    def test_add_to_queue(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        item = mgr.get_item(item_id)
        assert item is not None
        assert item.url == "https://example.com/article"

    def test_add_to_queue_with_title(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue(
            "https://example.com/article",
            title="My Article",
        )
        item = mgr.get_item(item_id)
        assert item.title == "My Article"

    def test_add_to_queue_with_priority(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue(
            "https://example.com/article",
            priority=QueuePriority.HIGH,
        )
        item = mgr.get_item(item_id)
        assert item.priority == QueuePriority.HIGH

    def test_add_to_queue_with_notes(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue(
            "https://example.com/article",
            notes="Important read",
        )
        item = mgr.get_item(item_id)
        assert item.notes == "Important read"

    def test_add_to_queue_with_tags(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue(
            "https://example.com/article",
            tags=["tech"],
        )
        item = mgr.get_item(item_id)
        assert "tech" in item.tags

    def test_add_to_specific_queue(self):
        mgr = ReadQueueManager()
        qid = mgr.create_queue("Tech Queue")
        item_id = mgr.add_to_queue(
            "https://example.com/article",
            queue_id=qid,
        )
        queue = mgr.get_queue(qid)
        assert queue is not None
        assert any(i.item_id == item_id for i in queue.items)

    def test_add_duplicate_url(self):
        mgr = ReadQueueManager()
        i1 = mgr.add_to_queue("https://example.com/article")
        i2 = mgr.add_to_queue("https://example.com/article")
        assert i1 == i2

    def test_get_item_not_found(self):
        mgr = ReadQueueManager()
        assert mgr.get_item("nonexistent") is None

    def test_get_item_by_url(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        item = mgr.get_item_by_url("https://example.com/article")
        assert item is not None
        assert item.item_id == item_id

    def test_mark_item_read(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.mark_item_read(item_id)
        item = mgr.get_item(item_id)
        assert item.status == QueueStatus.READ

    def test_mark_item_skipped(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.mark_item_skipped(item_id)
        item = mgr.get_item(item_id)
        assert item.status == QueueStatus.SKIPPED

    def test_mark_item_pending(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.mark_item_read(item_id)
        mgr.mark_item_pending(item_id)
        item = mgr.get_item(item_id)
        assert item.status == QueueStatus.PENDING

    def test_remove_item(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        result = mgr.remove_item(item_id)
        assert result is True
        assert mgr.get_item(item_id) is None

    def test_remove_item_not_found(self):
        mgr = ReadQueueManager()
        result = mgr.remove_item("nonexistent")
        assert result is False

    def test_get_pending_items(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a")
        mgr.add_to_queue("https://example.com/b")
        mgr.mark_item_read(mgr.get_item_by_url("https://example.com/a").item_id)
        pending = mgr.get_pending_items()
        assert len(pending) == 1

    def test_get_pending_items_sorted(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a", priority=QueuePriority.LOW)
        mgr.add_to_queue("https://example.com/b", priority=QueuePriority.URGENT)
        pending = mgr.get_pending_items()
        assert pending[0].priority == QueuePriority.URGENT

    def test_get_overdue_items(self):
        past = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a", due_at=past)
        mgr.add_to_queue("https://example.com/b")
        overdue = mgr.get_overdue_items()
        assert len(overdue) == 1

    def test_get_queue_stats(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a")
        mgr.add_to_queue("https://example.com/b")
        mgr.mark_item_read(mgr.get_item_by_url("https://example.com/a").item_id)
        stats = mgr.get_queue_stats()
        assert stats["total"] == 2
        assert stats["pending"] == 1
        assert stats["read"] == 1

    def test_get_queue_stats_empty(self):
        mgr = ReadQueueManager()
        stats = mgr.get_queue_stats()
        assert stats["total"] == 0

    def test_list_queues(self):
        mgr = ReadQueueManager()
        mgr.create_queue("Queue 1")
        mgr.create_queue("Queue 2")
        queues = mgr.list_queues()
        assert len(queues) == 3  # includes default

    def test_delete_queue(self):
        mgr = ReadQueueManager()
        qid = mgr.create_queue("Temp Queue")
        result = mgr.delete_queue(qid)
        assert result is True
        assert mgr.get_queue(qid) is None

    def test_delete_default_queue(self):
        mgr = ReadQueueManager()
        default = mgr.get_default_queue()
        result = mgr.delete_queue(default.queue_id)
        assert result is False

    def test_move_item_to_queue(self):
        mgr = ReadQueueManager()
        qid = mgr.create_queue("Tech Queue")
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.move_item_to_queue(item_id, qid)
        queue = mgr.get_queue(qid)
        assert any(i.item_id == item_id for i in queue.items)

    def test_update_item_notes(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.update_item_notes(item_id, "Updated notes")
        item = mgr.get_item(item_id)
        assert item.notes == "Updated notes"

    def test_update_item_priority(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        mgr.update_item_priority(item_id, QueuePriority.URGENT)
        item = mgr.get_item(item_id)
        assert item.priority == QueuePriority.URGENT

    def test_update_item_due_date(self):
        mgr = ReadQueueManager()
        item_id = mgr.add_to_queue("https://example.com/article")
        due = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
        mgr.update_item_due_date(item_id, due)
        item = mgr.get_item(item_id)
        assert item.due_at == due

    def test_clear_read_items(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a")
        mgr.add_to_queue("https://example.com/b")
        mgr.mark_item_read(mgr.get_item_by_url("https://example.com/a").item_id)
        mgr.clear_read_items()
        stats = mgr.get_queue_stats()
        assert stats["read"] == 0

    def test_get_items_by_tag(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/a", tags=["tech"])
        mgr.add_to_queue("https://example.com/b", tags=["news"])
        mgr.add_to_queue("https://example.com/c", tags=["tech"])
        tech_items = mgr.get_items_by_tag("tech")
        assert len(tech_items) == 2

    def test_serialize_deserialize(self):
        mgr = ReadQueueManager()
        mgr.add_to_queue("https://example.com/article", title="Test", tags=["tech"])
        data = mgr.to_dict()
        new_mgr = ReadQueueManager.from_dict(data)
        item = new_mgr.get_items_by_tag("tech")[0]
        assert item.title == "Test"

    def test_batch_add(self):
        mgr = ReadQueueManager()
        urls = [
            "https://example.com/a",
            "https://example.com/b",
            "https://example.com/c",
        ]
        ids = mgr.batch_add(urls)
        assert len(ids) == 3
        for item_id in ids:
            item = mgr.get_item(item_id)
            assert item is not None
