"""Tests for content_restore module - recover deleted items."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_restore import (
    RestoreEntry,
    RestorePoint,
    RestoreManager,
    RestoreStatus,
    RestoreSource,
)


class TestRestoreEntry:
    """Tests for RestoreEntry dataclass."""

    def test_create_restore_entry_basic(self):
        entry = RestoreEntry(
            url="https://example.com/article",
            title="Test Article",
        )
        assert entry.url == "https://example.com/article"
        assert entry.title == "Test Article"
        assert entry.entry_id is not None
        assert entry.status == RestoreStatus.PENDING
        assert entry.created_at is not None

    def test_create_restore_entry_with_content(self):
        entry = RestoreEntry(
            url="https://example.com/article",
            title="Test",
            content="<html>test</html>",
        )
        assert entry.content == "<html>test</html>"
        assert entry.content_length == 17

    def test_create_restore_entry_with_metadata(self):
        entry = RestoreEntry(
            url="https://example.com/article",
            title="Test",
            author="John Doe",
            tags=["tech"],
            deleted_at="2024-01-01T00:00:00+00:00",
        )
        assert entry.author == "John Doe"
        assert entry.tags == ["tech"]
        assert entry.deleted_at == "2024-01-01T00:00:00+00:00"

    def test_restore_entry_to_dict(self):
        entry = RestoreEntry(
            url="https://example.com/article",
            title="Test",
            content="<html>test</html>",
            source=RestoreSource.BACKUP,
        )
        d = entry.to_dict()
        assert d["url"] == "https://example.com/article"
        assert d["title"] == "Test"
        assert d["source"] == "backup"
        assert d["content_length"] == 17

    def test_restore_entry_from_dict(self):
        data = {
            "entry_id": "r1",
            "url": "https://example.com/article",
            "title": "Test",
            "content": "<html>test</html>",
            "author": "Jane",
            "tags": ["tech"],
            "status": "restored",
            "source": "trash",
            "content_length": 17,
            "deleted_at": "2024-01-01T00:00:00+00:00",
            "restored_at": "2024-01-02T00:00:00+00:00",
            "created_at": "2024-01-01T00:00:00+00:00",
            "error": None,
        }
        entry = RestoreEntry.from_dict(data)
        assert entry.entry_id == "r1"
        assert entry.url == "https://example.com/article"
        assert entry.status == RestoreStatus.RESTORED
        assert entry.source == RestoreSource.TRASH

    def test_restore_entry_from_dict_minimal(self):
        data = {"url": "https://example.com/minimal"}
        entry = RestoreEntry.from_dict(data)
        assert entry.status == RestoreStatus.PENDING
        assert entry.source == RestoreSource.TRASH

    def test_restore_entry_mark_restored(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        entry.mark_restored()
        assert entry.status == RestoreStatus.RESTORED
        assert entry.restored_at is not None

    def test_restore_entry_mark_failed(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        entry.mark_failed("Data corrupted")
        assert entry.status == RestoreStatus.FAILED
        assert entry.error == "Data corrupted"

    def test_restore_entry_mark_pending(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        entry.mark_restored()
        entry.mark_pending()
        assert entry.status == RestoreStatus.PENDING
        assert entry.restored_at is None

    def test_restore_entry_add_tag(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        entry.add_tag("tech")
        assert "tech" in entry.tags

    def test_restore_entry_remove_tag(self):
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", tags=["tech", "news"]
        )
        entry.remove_tag("tech")
        assert "tech" not in entry.tags

    def test_restore_entry_set_content(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        entry.set_content("<html>content</html>")
        assert entry.content == "<html>content</html>"
        assert entry.content_length == 20

    def test_restore_entry_is_expired(self):
        past = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", deleted_at=past
        )
        assert entry.is_expired(retention_days=30) is True

    def test_restore_entry_is_not_expired(self):
        recent = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", deleted_at=recent
        )
        assert entry.is_expired(retention_days=30) is False

    def test_restore_entry_is_not_expired_no_delete_date(self):
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        assert entry.is_expired(retention_days=30) is False


class TestRestorePoint:
    """Tests for RestorePoint class."""

    def test_create_restore_point(self):
        point = RestorePoint()
        assert point.point_id is not None
        assert len(point.entries) == 0

    def test_create_restore_point_with_name(self):
        point = RestorePoint(name="before-delete")
        assert point.name == "before-delete"

    def test_add_entry(self):
        point = RestorePoint()
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        point.add_entry(entry)
        assert len(point.entries) == 1

    def test_add_duplicate_url(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="Test 1"))
        point.add_entry(RestoreEntry(url="https://example.com/a", title="Test 2"))
        assert len(point.entries) == 1
        assert point.get_entry_by_url("https://example.com/a").title == "Test 2"

    def test_remove_entry(self):
        point = RestorePoint()
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        point.add_entry(entry)
        point.remove_entry(entry.entry_id)
        assert len(point.entries) == 0

    def test_get_entry_by_url(self):
        point = RestorePoint()
        entry = RestoreEntry(url="https://example.com/a", title="Test")
        point.add_entry(entry)
        found = point.get_entry_by_url("https://example.com/a")
        assert found == entry

    def test_get_entry_by_url_not_found(self):
        point = RestorePoint()
        found = point.get_entry_by_url("https://example.com/notfound")
        assert found is None

    def test_get_restored_entries(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="A", status=RestoreStatus.RESTORED))
        point.add_entry(RestoreEntry(url="https://example.com/b", title="B", status=RestoreStatus.PENDING))
        restored = point.get_restored_entries()
        assert len(restored) == 1

    def test_get_failed_entries(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="A", status=RestoreStatus.FAILED))
        point.add_entry(RestoreEntry(url="https://example.com/b", title="B", status=RestoreStatus.RESTORED))
        failed = point.get_failed_entries()
        assert len(failed) == 1

    def test_get_stats(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="A", status=RestoreStatus.RESTORED))
        point.add_entry(RestoreEntry(url="https://example.com/b", title="B", status=RestoreStatus.FAILED))
        stats = point.get_stats()
        assert stats["total"] == 2
        assert stats["restored"] == 1
        assert stats["failed"] == 1

    def test_get_stats_empty(self):
        point = RestorePoint()
        stats = point.get_stats()
        assert stats["total"] == 0

    def test_to_dict(self):
        point = RestorePoint(name="test-point")
        point.add_entry(RestoreEntry(url="https://example.com/a", title="Test"))
        d = point.to_dict()
        assert d["name"] == "test-point"
        assert len(d["entries"]) == 1

    def test_from_dict(self):
        data = {
            "point_id": "p1",
            "name": "restored-point",
            "entries": [
                {
                    "entry_id": "e1",
                    "url": "https://example.com/a",
                    "title": "Test",
                    "content": "<html>a</html>",
                    "author": "",
                    "tags": [],
                    "status": "restored",
                    "source": "trash",
                    "content_length": 11,
                    "deleted_at": None,
                    "restored_at": "2024-01-02T00:00:00+00:00",
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "error": None,
                }
            ],
        }
        point = RestorePoint.from_dict(data)
        assert point.point_id == "p1"
        assert point.name == "restored-point"
        assert len(point.entries) == 1

    def test_clear_all(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="Test"))
        point.clear_all()
        assert len(point.entries) == 0

    def test_contains_url(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="Test"))
        assert point.contains_url("https://example.com/a") is True
        assert point.contains_url("https://example.com/b") is False

    def test_batch_add(self):
        point = RestorePoint()
        entries = [
            RestoreEntry(url="https://example.com/a", title="A"),
            RestoreEntry(url="https://example.com/b", title="B"),
        ]
        point.batch_add(entries)
        assert len(point.entries) == 2

    def test_get_entries_sorted_by_date(self):
        point = RestorePoint()
        point.add_entry(RestoreEntry(url="https://example.com/a", title="A", created_at="2024-01-01T00:00:00+00:00"))
        point.add_entry(RestoreEntry(url="https://example.com/b", title="B", created_at="2024-06-01T00:00:00+00:00"))
        sorted_entries = point.get_entries_sorted_by_date()
        assert sorted_entries[0].url == "https://example.com/b"


class TestRestoreManager:
    """Tests for RestoreManager class."""

    def test_create_manager(self):
        mgr = RestoreManager()
        assert len(mgr.restore_points) == 0
        assert len(mgr.trash) == 0

    def test_move_to_trash(self):
        mgr = RestoreManager()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", content="<html>test</html>"
        )
        mgr.move_to_trash(entry)
        assert len(mgr.trash) == 1
        assert mgr.trash[0].url == "https://example.com/a"

    def test_move_to_trash_duplicate(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test 1"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test 2"))
        assert len(mgr.trash) == 1
        assert mgr.trash[0].title == "Test 2"

    def test_restore_from_trash(self):
        mgr = RestoreManager()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", content="<html>test</html>"
        )
        mgr.move_to_trash(entry)
        restored = mgr.restore_from_trash("https://example.com/a")
        assert restored is not None
        assert restored.url == "https://example.com/a"
        assert restored.status == RestoreStatus.RESTORED

    def test_restore_from_trash_not_found(self):
        mgr = RestoreManager()
        restored = mgr.restore_from_trash("https://example.com/notfound")
        assert restored is None

    def test_restore_from_trash_removes_entry(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test"))
        mgr.restore_from_trash("https://example.com/a")
        assert len(mgr.trash) == 0

    def test_empty_trash(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test"))
        mgr.empty_trash()
        assert len(mgr.trash) == 0

    def test_empty_trash_partial(self):
        mgr = RestoreManager()
        past = (datetime.now(timezone.utc) - timedelta(days=31)).isoformat()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A", deleted_at=past))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="B"))
        mgr.empty_trash(retention_days=30)
        assert len(mgr.trash) == 1
        assert mgr.trash[0].url == "https://example.com/b"

    def test_create_restore_point(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test"))
        point_id = mgr.create_restore_point("before-empty")
        assert point_id is not None
        assert len(mgr.restore_points) == 1

    def test_restore_from_point(self):
        mgr = RestoreManager()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", content="<html>test</html>"
        )
        mgr.move_to_trash(entry)
        point_id = mgr.create_restore_point("snapshot")
        restored = mgr.restore_from_point(point_id, "https://example.com/a")
        assert restored is not None
        assert restored.url == "https://example.com/a"

    def test_restore_all_from_point(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A", content="<html>a</html>"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="B", content="<html>b</html>"))
        point_id = mgr.create_restore_point("snapshot")
        restored = mgr.restore_all_from_point(point_id)
        assert len(restored) == 2

    def test_restore_all_from_point_not_found(self):
        mgr = RestoreManager()
        restored = mgr.restore_all_from_point("nonexistent")
        assert len(restored) == 0

    def test_list_trash(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="B"))
        trash = mgr.list_trash()
        assert len(trash) == 2

    def test_list_restore_points(self):
        mgr = RestoreManager()
        mgr.create_restore_point("point-1")
        mgr.create_restore_point("point-2")
        points = mgr.list_restore_points()
        assert len(points) == 2

    def test_delete_restore_point(self):
        mgr = RestoreManager()
        point_id = mgr.create_restore_point("test")
        mgr.delete_restore_point(point_id)
        assert len(mgr.restore_points) == 0

    def test_get_restore_point(self):
        mgr = RestoreManager()
        point_id = mgr.create_restore_point("test")
        point = mgr.get_restore_point(point_id)
        assert point is not None

    def test_get_restore_point_not_found(self):
        mgr = RestoreManager()
        point = mgr.get_restore_point("nonexistent")
        assert point is None

    def test_get_trash_stats(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A"))
        stats = mgr.get_trash_stats()
        assert stats["total"] == 1

    def test_get_trash_stats_empty(self):
        mgr = RestoreManager()
        stats = mgr.get_trash_stats()
        assert stats["total"] == 0

    def test_search_trash(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Python Tutorial"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="JavaScript Guide"))
        results = mgr.search_trash("Python")
        assert len(results) == 1
        assert results[0].title == "Python Tutorial"

    def test_restore_by_source(self):
        mgr = RestoreManager()
        entry = RestoreEntry(
            url="https://example.com/a", title="Test", source=RestoreSource.BACKUP
        )
        mgr.move_to_trash(entry)
        restored = mgr.restore_from_trash("https://example.com/a")
        assert restored is not None
        assert restored.source == RestoreSource.BACKUP

    def test_batch_restore(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="B"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/c", title="C"))
        restored = mgr.batch_restore(["https://example.com/a", "https://example.com/b"])
        assert len(restored) == 2
        assert len(mgr.trash) == 1

    def test_to_dict(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="Test"))
        d = mgr.to_dict()
        assert len(d["trash"]) == 1

    def test_from_dict(self):
        data = {
            "trash": [
                {
                    "entry_id": "e1",
                    "url": "https://example.com/a",
                    "title": "Test",
                    "content": "<html>a</html>",
                    "author": "",
                    "tags": [],
                    "status": "pending",
                    "source": "trash",
                    "content_length": 11,
                    "deleted_at": "2024-01-01T00:00:00+00:00",
                    "restored_at": None,
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "error": None,
                }
            ],
            "restore_points": [],
        }
        mgr = RestoreManager.from_dict(data)
        assert len(mgr.trash) == 1
        assert mgr.trash[0].url == "https://example.com/a"

    def test_get_total_trash_size(self):
        mgr = RestoreManager()
        mgr.move_to_trash(RestoreEntry(url="https://example.com/a", title="A", content="12345"))
        mgr.move_to_trash(RestoreEntry(url="https://example.com/b", title="B", content="1234567890"))
        size = mgr.get_total_trash_size()
        assert size == 15

    def test_get_total_trash_size_empty(self):
        mgr = RestoreManager()
        size = mgr.get_total_trash_size()
        assert size == 0


class TestRestoreStatus:
    """Tests for RestoreStatus enum."""

    def test_status_values(self):
        assert RestoreStatus.PENDING.value == "pending"
        assert RestoreStatus.RESTORED.value == "restored"
        assert RestoreStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        assert RestoreStatus("pending") == RestoreStatus.PENDING
        assert RestoreStatus("restored") == RestoreStatus.RESTORED

    def test_status_invalid(self):
        with pytest.raises(ValueError):
            RestoreStatus("invalid")


class TestRestoreSource:
    """Tests for RestoreSource enum."""

    def test_source_values(self):
        assert RestoreSource.TRASH.value == "trash"
        assert RestoreSource.BACKUP.value == "backup"
        assert RestoreSource.SYNC.value == "sync"

    def test_source_from_string(self):
        assert RestoreSource("trash") == RestoreSource.TRASH
        assert RestoreSource("backup") == RestoreSource.BACKUP
        assert RestoreSource("sync") == RestoreSource.SYNC
