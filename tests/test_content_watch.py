"""Tests for content_watch module - monitor saved URLs for changes."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_watch import (
    WatchEntry,
    WatchChange,
    WatchChangeType,
    WatchManager,
    WatchStatus,
)


class TestWatchEntry:
    """Tests for WatchEntry dataclass."""

    def test_create_watch_entry_basic(self):
        entry = WatchEntry(url="https://example.com/article")
        assert entry.url == "https://example.com/article"
        assert entry.watch_id is not None
        assert entry.status == WatchStatus.ACTIVE
        assert entry.check_interval_minutes == 60
        assert entry.created_at is not None

    def test_create_watch_entry_with_interval(self):
        entry = WatchEntry(
            url="https://example.com/news",
            check_interval_minutes=15,
        )
        assert entry.check_interval_minutes == 15

    def test_create_watch_entry_with_tags(self):
        entry = WatchEntry(
            url="https://example.com/blog",
            tags=["blog", "tech"],
        )
        assert entry.tags == ["blog", "tech"]

    def test_create_watch_entry_inactive(self):
        entry = WatchEntry(
            url="https://example.com/old",
            status=WatchStatus.PAUSED,
        )
        assert entry.status == WatchStatus.PAUSED

    def test_watch_entry_to_dict(self):
        entry = WatchEntry(
            url="https://example.com/page",
            check_interval_minutes=30,
            tags=["test"],
        )
        d = entry.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["check_interval_minutes"] == 30
        assert d["tags"] == ["test"]
        assert d["watch_id"] is not None

    def test_watch_entry_from_dict(self):
        data = {
            "watch_id": "w1",
            "url": "https://example.com/page",
            "check_interval_minutes": 45,
            "status": "active",
            "tags": ["news"],
            "created_at": "2024-01-01T00:00:00+00:00",
            "last_checked_at": "2024-01-02T00:00:00+00:00",
            "last_hash": "abc123",
            "change_count": 5,
        }
        entry = WatchEntry.from_dict(data)
        assert entry.watch_id == "w1"
        assert entry.url == "https://example.com/page"
        assert entry.check_interval_minutes == 45
        assert entry.status == WatchStatus.ACTIVE
        assert entry.tags == ["news"]
        assert entry.last_hash == "abc123"
        assert entry.change_count == 5

    def test_watch_entry_from_dict_defaults(self):
        data = {"url": "https://example.com/minimal"}
        entry = WatchEntry.from_dict(data)
        assert entry.check_interval_minutes == 60
        assert entry.status == WatchStatus.ACTIVE
        assert entry.tags == []

    def test_watch_entry_update_hash(self):
        entry = WatchEntry(url="https://example.com/page")
        entry.update_hash("new_hash_value")
        assert entry.last_hash == "new_hash_value"
        assert entry.last_checked_at is not None

    def test_watch_entry_is_due(self):
        past = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()
        entry = WatchEntry(
            url="https://example.com/page",
            check_interval_minutes=60,
            last_checked_at=past,
        )
        assert entry.is_due() is True

    def test_watch_entry_not_due(self):
        recent = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        entry = WatchEntry(
            url="https://example.com/page",
            check_interval_minutes=60,
            last_checked_at=recent,
        )
        assert entry.is_due() is False

    def test_watch_entry_is_due_never_checked(self):
        entry = WatchEntry(url="https://example.com/page")
        assert entry.is_due() is True

    def test_watch_entry_is_due_when_paused(self):
        entry = WatchEntry(
            url="https://example.com/page",
            status=WatchStatus.PAUSED,
        )
        assert entry.is_due() is False


class TestWatchChange:
    """Tests for WatchChange dataclass."""

    def test_create_change_basic(self):
        change = WatchChange(
            watch_id="w1",
            change_type=WatchChangeType.CONTENT_CHANGED,
        )
        assert change.watch_id == "w1"
        assert change.change_type == WatchChangeType.CONTENT_CHANGED
        assert change.detected_at is not None

    def test_create_change_with_details(self):
        change = WatchChange(
            watch_id="w1",
            change_type=WatchChangeType.TITLE_CHANGED,
            old_value="Old Title",
            new_value="New Title",
        )
        assert change.old_value == "Old Title"
        assert change.new_value == "New Title"

    def test_create_change_status_code(self):
        change = WatchChange(
            watch_id="w1",
            change_type=WatchChangeType.STATUS_CHANGED,
            old_value="200",
            new_value="404",
        )
        assert change.change_type == WatchChangeType.STATUS_CHANGED

    def test_change_to_dict(self):
        change = WatchChange(
            watch_id="w1",
            change_type=WatchChangeType.CONTENT_CHANGED,
            old_value="old",
            new_value="new",
        )
        d = change.to_dict()
        assert d["watch_id"] == "w1"
        assert d["change_type"] == "content_changed"
        assert d["old_value"] == "old"

    def test_change_from_dict(self):
        data = {
            "change_id": "ch1",
            "watch_id": "w1",
            "change_type": "title_changed",
            "old_value": "Old",
            "new_value": "New",
            "detected_at": "2024-01-01T00:00:00+00:00",
        }
        change = WatchChange.from_dict(data)
        assert change.change_id == "ch1"
        assert change.change_type == WatchChangeType.TITLE_CHANGED
        assert change.old_value == "Old"

    def test_change_from_dict_defaults(self):
        data = {"watch_id": "w1", "change_type": "content_changed"}
        change = WatchChange.from_dict(data)
        assert change.old_value is None
        assert change.new_value is None


class TestWatchManager:
    """Tests for WatchManager class."""

    def test_add_watch(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        assert wid is not None
        entry = mgr.get_watch(wid)
        assert entry is not None
        assert entry.url == "https://example.com/page"

    def test_add_watch_with_interval(self):
        mgr = WatchManager()
        wid = mgr.add_watch(
            "https://example.com/news",
            check_interval_minutes=15,
        )
        entry = mgr.get_watch(wid)
        assert entry.check_interval_minutes == 15

    def test_add_watch_with_tags(self):
        mgr = WatchManager()
        wid = mgr.add_watch(
            "https://example.com/blog",
            tags=["blog", "tech"],
        )
        entry = mgr.get_watch(wid)
        assert entry.tags == ["blog", "tech"]

    def test_add_duplicate_watch(self):
        mgr = WatchManager()
        w1 = mgr.add_watch("https://example.com/page")
        w2 = mgr.add_watch("https://example.com/page")
        assert w1 == w2

    def test_get_watch_not_found(self):
        mgr = WatchManager()
        assert mgr.get_watch("nonexistent") is None

    def test_list_watches(self):
        mgr = WatchManager()
        mgr.add_watch("https://example.com/a")
        mgr.add_watch("https://example.com/b")
        watches = mgr.list_watches()
        assert len(watches) == 2

    def test_list_watches_filtered_by_tag(self):
        mgr = WatchManager()
        mgr.add_watch("https://example.com/a", tags=["tech"])
        mgr.add_watch("https://example.com/b", tags=["news"])
        mgr.add_watch("https://example.com/c", tags=["tech"])
        tech_watches = mgr.list_watches(tags=["tech"])
        assert len(tech_watches) == 2

    def test_list_watches_active_only(self):
        mgr = WatchManager()
        mgr.add_watch("https://example.com/a")
        w2 = mgr.add_watch("https://example.com/b")
        mgr.pause_watch(w2)
        active = mgr.list_watches(status=WatchStatus.ACTIVE)
        assert len(active) == 1

    def test_remove_watch(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        result = mgr.remove_watch(wid)
        assert result is True
        assert mgr.get_watch(wid) is None

    def test_remove_watch_not_found(self):
        mgr = WatchManager()
        result = mgr.remove_watch("nonexistent")
        assert result is False

    def test_pause_watch(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.pause_watch(wid)
        entry = mgr.get_watch(wid)
        assert entry.status == WatchStatus.PAUSED

    def test_resume_watch(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.pause_watch(wid)
        mgr.resume_watch(wid)
        entry = mgr.get_watch(wid)
        assert entry.status == WatchStatus.ACTIVE

    def test_get_due_watches(self):
        mgr = WatchManager()
        past = (datetime.now(timezone.utc) - timedelta(minutes=65)).isoformat()
        mgr.add_watch("https://example.com/a", check_interval_minutes=60, last_checked_at=past)
        mgr.add_watch("https://example.com/b", check_interval_minutes=60)
        due = mgr.get_due_watches()
        assert len(due) == 2

    def test_record_change(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        change = mgr.record_change(
            wid,
            WatchChangeType.CONTENT_CHANGED,
            old_value="old_hash",
            new_value="new_hash",
        )
        assert change.watch_id == wid
        assert change.change_type == WatchChangeType.CONTENT_CHANGED

    def test_get_changes_for_watch(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.record_change(wid, WatchChangeType.CONTENT_CHANGED)
        mgr.record_change(wid, WatchChangeType.TITLE_CHANGED)
        changes = mgr.get_changes(wid)
        assert len(changes) == 2

    def test_get_changes_empty(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        changes = mgr.get_changes(wid)
        assert changes == []

    def test_update_watch_hash(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.update_hash(wid, "hash123")
        entry = mgr.get_watch(wid)
        assert entry.last_hash == "hash123"

    def test_check_watch_no_change(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.update_hash(wid, "same_hash")
        result = mgr.check_watch(wid, "same_hash")
        assert result is None

    def test_check_watch_change_detected(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.update_hash(wid, "old_hash")
        result = mgr.check_watch(wid, "new_hash")
        assert result is not None
        assert result.change_type == WatchChangeType.CONTENT_CHANGED

    def test_check_watch_first_time(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        result = mgr.check_watch(wid, "initial_hash")
        assert result is None  # No change on first check

    def test_get_watch_by_url(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        entry = mgr.get_watch_by_url("https://example.com/page")
        assert entry is not None
        assert entry.watch_id == wid

    def test_get_watch_count(self):
        mgr = WatchManager()
        assert mgr.get_watch_count() == 0
        mgr.add_watch("https://example.com/a")
        mgr.add_watch("https://example.com/b")
        assert mgr.get_watch_count() == 2

    def test_get_all_changes(self):
        mgr = WatchManager()
        w1 = mgr.add_watch("https://example.com/a")
        w2 = mgr.add_watch("https://example.com/b")
        mgr.record_change(w1, WatchChangeType.CONTENT_CHANGED)
        mgr.record_change(w2, WatchChangeType.TITLE_CHANGED)
        all_changes = mgr.get_all_changes()
        assert len(all_changes) == 2

    def test_get_recent_changes(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        for _ in range(5):
            mgr.record_change(wid, WatchChangeType.CONTENT_CHANGED)
        recent = mgr.get_recent_changes(wid, limit=3)
        assert len(recent) == 3

    def test_serialize_deserialize(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page", tags=["test"])
        mgr.record_change(wid, WatchChangeType.CONTENT_CHANGED)
        data = mgr.to_dict()
        new_mgr = WatchManager.from_dict(data)
        assert new_mgr.get_watch_count() == 1
        entry = new_mgr.get_watch(wid)
        assert entry.url == "https://example.com/page"
        assert entry.tags == ["test"]

    def test_check_watch_paused(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.pause_watch(wid)
        result = mgr.check_watch(wid, "any_hash")
        assert result is None

    def test_remove_watch_cleans_changes(self):
        mgr = WatchManager()
        wid = mgr.add_watch("https://example.com/page")
        mgr.record_change(wid, WatchChangeType.CONTENT_CHANGED)
        mgr.remove_watch(wid)
        assert mgr.get_changes(wid) == []
