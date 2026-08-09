"""Tests for content_snapshots module - archive point-in-time captures."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_snapshots import (
    Snapshot,
    SnapshotManager,
    SnapshotFormat,
    SnapshotStatus,
)


class TestSnapshot:
    """Tests for Snapshot dataclass."""

    def test_create_snapshot_basic(self):
        snap = Snapshot(url="https://example.com/page")
        assert snap.url == "https://example.com/page"
        assert snap.snapshot_id is not None
        assert snap.status == SnapshotStatus.COMPLETE
        assert snap.format == SnapshotFormat.HTML
        assert snap.created_at is not None

    def test_create_snapshot_with_content(self):
        snap = Snapshot(
            url="https://example.com/page",
            content="<html><body>Hello</body></html>",
        )
        assert snap.content == "<html><body>Hello</body></html>"

    def test_create_snapshot_with_title(self):
        snap = Snapshot(
            url="https://example.com/page",
            title="My Page",
        )
        assert snap.title == "My Page"

    def test_create_snapshot_pdf_format(self):
        snap = Snapshot(
            url="https://example.com/page",
            format=SnapshotFormat.PDF,
        )
        assert snap.format == SnapshotFormat.PDF

    def test_create_snapshot_text_format(self):
        snap = Snapshot(
            url="https://example.com/page",
            format=SnapshotFormat.TEXT,
        )
        assert snap.format == SnapshotFormat.TEXT

    def test_create_snapshot_mhtml_format(self):
        snap = Snapshot(
            url="https://example.com/page",
            format=SnapshotFormat.MHTML,
        )
        assert snap.format == SnapshotFormat.MHTML

    def test_create_snapshot_with_metadata(self):
        snap = Snapshot(
            url="https://example.com/page",
            metadata={"author": "John", "version": "1.0"},
        )
        assert snap.metadata == {"author": "John", "version": "1.0"}

    def test_create_snapshot_pending(self):
        snap = Snapshot(
            url="https://example.com/page",
            status=SnapshotStatus.PENDING,
        )
        assert snap.status == SnapshotStatus.PENDING

    def test_create_snapshot_failed(self):
        snap = Snapshot(
            url="https://example.com/page",
            status=SnapshotStatus.FAILED,
            error="Connection timeout",
        )
        assert snap.status == SnapshotStatus.FAILED
        assert snap.error == "Connection timeout"

    def test_snapshot_to_dict(self):
        snap = Snapshot(
            url="https://example.com/page",
            title="Test",
            content="<p>test</p>",
            format=SnapshotFormat.TEXT,
        )
        d = snap.to_dict()
        assert d["url"] == "https://example.com/page"
        assert d["title"] == "Test"
        assert d["format"] == "text"
        assert d["content_length"] == 9

    def test_snapshot_from_dict(self):
        data = {
            "snapshot_id": "s1",
            "url": "https://example.com/page",
            "title": "Test Page",
            "content": "<p>hi</p>",
            "format": "html",
            "status": "complete",
            "content_length": 6,
            "created_at": "2024-01-01T00:00:00+00:00",
            "metadata": {"key": "val"},
        }
        snap = Snapshot.from_dict(data)
        assert snap.snapshot_id == "s1"
        assert snap.title == "Test Page"
        assert snap.format == SnapshotFormat.HTML
        assert snap.metadata == {"key": "val"}

    def test_snapshot_from_dict_defaults(self):
        data = {"url": "https://example.com/minimal"}
        snap = Snapshot.from_dict(data)
        assert snap.content == ""
        assert snap.format == SnapshotFormat.HTML
        assert snap.status == SnapshotStatus.COMPLETE

    def test_snapshot_content_length(self):
        snap = Snapshot(
            url="https://example.com/page",
            content="Hello World",
        )
        assert snap.content_length == 11

    def test_snapshot_content_length_empty(self):
        snap = Snapshot(url="https://example.com/page")
        assert snap.content_length == 0

    def test_snapshot_is_complete(self):
        snap = Snapshot(url="https://example.com/page")
        assert snap.is_complete() is True

    def test_snapshot_is_complete_pending(self):
        snap = Snapshot(url="https://example.com/page", status=SnapshotStatus.PENDING)
        assert snap.is_complete() is False

    def test_snapshot_is_complete_failed(self):
        snap = Snapshot(url="https://example.com/page", status=SnapshotStatus.FAILED)
        assert snap.is_complete() is False

    def test_snapshot_update_content(self):
        snap = Snapshot(url="https://example.com/page")
        snap.update_content("<p>new content</p>")
        assert snap.content == "<p>new content</p>"
        assert snap.content_length == 17

    def test_snapshot_add_metadata(self):
        snap = Snapshot(url="https://example.com/page")
        snap.add_metadata("key1", "value1")
        assert snap.metadata["key1"] == "value1"

    def test_snapshot_get_metadata(self):
        snap = Snapshot(
            url="https://example.com/page",
            metadata={"key1": "val1", "key2": "val2"},
        )
        assert snap.get_metadata("key1") == "val1"
        assert snap.get_metadata("key3") is None


class TestSnapshotManager:
    """Tests for SnapshotManager class."""

    def test_create_snapshot(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot("https://example.com/page")
        snap = mgr.get_snapshot(sid)
        assert snap is not None
        assert snap.url == "https://example.com/page"

    def test_create_snapshot_with_content(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot(
            "https://example.com/page",
            content="<p>test</p>",
            title="Test Page",
        )
        snap = mgr.get_snapshot(sid)
        assert snap.content == "<p>test</p>"
        assert snap.title == "Test Page"

    def test_create_snapshot_pdf(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot(
            "https://example.com/page",
            format=SnapshotFormat.PDF,
        )
        snap = mgr.get_snapshot(sid)
        assert snap.format == SnapshotFormat.PDF

    def test_get_snapshot_not_found(self):
        mgr = SnapshotManager()
        assert mgr.get_snapshot("nonexistent") is None

    def test_list_snapshots(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/a")
        mgr.create_snapshot("https://example.com/b")
        snaps = mgr.list_snapshots()
        assert len(snaps) == 2

    def test_list_snapshots_by_url(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/page")
        mgr.create_snapshot("https://example.com/page")
        mgr.create_snapshot("https://example.com/other")
        snaps = mgr.list_snapshots(url="https://example.com/page")
        assert len(snaps) == 2

    def test_list_snapshots_by_format(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/a", format=SnapshotFormat.HTML)
        mgr.create_snapshot("https://example.com/b", format=SnapshotFormat.PDF)
        mgr.create_snapshot("https://example.com/c", format=SnapshotFormat.HTML)
        html_snaps = mgr.list_snapshots(format=SnapshotFormat.HTML)
        assert len(html_snaps) == 2

    def test_list_snapshots_by_status(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/a", status=SnapshotStatus.COMPLETE)
        mgr.create_snapshot("https://example.com/b", status=SnapshotStatus.PENDING)
        complete = mgr.list_snapshots(status=SnapshotStatus.COMPLETE)
        assert len(complete) == 1

    def test_get_latest_snapshot(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/page", title="v1")
        mgr.create_snapshot("https://example.com/page", title="v2")
        latest = mgr.get_latest_snapshot("https://example.com/page")
        assert latest is not None
        assert latest.title == "v2"

    def test_get_latest_snapshot_not_found(self):
        mgr = SnapshotManager()
        assert mgr.get_latest_snapshot("https://example.com/none") is None

    def test_get_snapshots_for_url(self):
        mgr = SnapshotManager()
        s1 = mgr.create_snapshot("https://example.com/page")
        s2 = mgr.create_snapshot("https://example.com/page")
        snaps = mgr.get_snapshots_for_url("https://example.com/page")
        assert len(snaps) == 2
        assert s1 in [s.snapshot_id for s in snaps]
        assert s2 in [s.snapshot_id for s in snaps]

    def test_delete_snapshot(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot("https://example.com/page")
        result = mgr.delete_snapshot(sid)
        assert result is True
        assert mgr.get_snapshot(sid) is None

    def test_delete_snapshot_not_found(self):
        mgr = SnapshotManager()
        result = mgr.delete_snapshot("nonexistent")
        assert result is False

    def test_update_snapshot_content(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot("https://example.com/page")
        mgr.update_snapshot_content(sid, "<p>updated</p>")
        snap = mgr.get_snapshot(sid)
        assert snap.content == "<p>updated</p>"

    def test_update_snapshot_title(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot("https://example.com/page")
        mgr.update_snapshot_title(sid, "New Title")
        snap = mgr.get_snapshot(sid)
        assert snap.title == "New Title"

    def test_get_snapshot_count(self):
        mgr = SnapshotManager()
        assert mgr.get_snapshot_count() == 0
        mgr.create_snapshot("https://example.com/a")
        mgr.create_snapshot("https://example.com/b")
        assert mgr.get_snapshot_count() == 2

    def test_get_snapshot_count_by_url(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/page")
        mgr.create_snapshot("https://example.com/page")
        mgr.create_snapshot("https://example.com/other")
        assert mgr.get_snapshot_count_by_url("https://example.com/page") == 2
        assert mgr.get_snapshot_count_by_url("https://example.com/other") == 1

    def test_get_total_size(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/a", content="12345")
        mgr.create_snapshot("https://example.com/b", content="1234567890")
        assert mgr.get_total_size() == 15

    def test_get_snapshots_by_date_range(self):
        mgr = SnapshotManager()
        past = (datetime.now(timezone.utc) - timedelta(days=10)).isoformat()
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mgr.create_snapshot("https://example.com/a", created_at=past)
        mgr.create_snapshot("https://example.com/b", created_at=recent)
        start = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        end = datetime.now(timezone.utc).isoformat()
        snaps = mgr.get_snapshots_by_date_range(start, end)
        assert len(snaps) == 1

    def test_restore_snapshot(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot("https://example.com/page", content="<p>old</p>")
        content = mgr.restore_snapshot(sid)
        assert content == "<p>old</p>"

    def test_restore_snapshot_not_found(self):
        mgr = SnapshotManager()
        content = mgr.restore_snapshot("nonexistent")
        assert content is None

    def test_compare_snapshots(self):
        mgr = SnapshotManager()
        s1 = mgr.create_snapshot("https://example.com/page", content="<p>v1</p>")
        s2 = mgr.create_snapshot("https://example.com/page", content="<p>v2</p>")
        diff = mgr.compare_snapshots(s1, s2)
        assert diff is not None
        assert diff["old_content_length"] == 7
        assert diff["new_content_length"] == 7
        assert diff["content_changed"] is True

    def test_compare_snapshots_same(self):
        mgr = SnapshotManager()
        s1 = mgr.create_snapshot("https://example.com/page", content="<p>same</p>")
        s2 = mgr.create_snapshot("https://example.com/page", content="<p>same</p>")
        diff = mgr.compare_snapshots(s1, s2)
        assert diff["content_changed"] is False

    def test_compare_snapshots_not_found(self):
        mgr = SnapshotManager()
        diff = mgr.compare_snapshots("nonexistent1", "nonexistent2")
        assert diff is None

    def test_serialize_deserialize(self):
        mgr = SnapshotManager()
        sid = mgr.create_snapshot(
            "https://example.com/page",
            content="<p>test</p>",
            title="Test",
            format=SnapshotFormat.TEXT,
        )
        data = mgr.to_dict()
        new_mgr = SnapshotManager.from_dict(data)
        snap = new_mgr.get_snapshot(sid)
        assert snap is not None
        assert snap.content == "<p>test</p>"
        assert snap.title == "Test"

    def test_get_snapshots_sorted(self):
        mgr = SnapshotManager()
        old = (datetime.now(timezone.utc) - timedelta(days=5)).isoformat()
        new = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mgr.create_snapshot("https://example.com/page", created_at=old)
        mgr.create_snapshot("https://example.com/page", created_at=new)
        snaps = mgr.list_snapshots(url="https://example.com/page", sort_by="date")
        assert len(snaps) == 2
        assert snaps[0].created_at > snaps[1].created_at

    def test_cleanup_old_snapshots(self):
        mgr = SnapshotManager()
        old = (datetime.now(timezone.utc) - timedelta(days=400)).isoformat()
        recent = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
        mgr.create_snapshot("https://example.com/a", created_at=old)
        mgr.create_snapshot("https://example.com/b", created_at=old)
        mgr.create_snapshot("https://example.com/c", created_at=recent)
        removed = mgr.cleanup_old_snapshots(days=365)
        assert removed == 2
        assert mgr.get_snapshot_count() == 1

    def test_get_urls_with_snapshots(self):
        mgr = SnapshotManager()
        mgr.create_snapshot("https://example.com/a")
        mgr.create_snapshot("https://example.com/a")
        mgr.create_snapshot("https://example.com/b")
        urls = mgr.get_urls_with_snapshots()
        assert "https://example.com/a" in urls
        assert "https://example.com/b" in urls
        assert len(urls) == 2
