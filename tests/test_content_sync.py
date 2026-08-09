"""Tests for content_sync module - sync across devices."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_sync import (
    SyncEntry,
    SyncManifest,
    SyncEngine,
    SyncStatus,
    SyncDirection,
    SyncConflict,
    ConflictResolution,
)


class TestSyncEntry:
    """Tests for SyncEntry dataclass."""

    def test_create_sync_entry_basic(self):
        entry = SyncEntry(
            url="https://example.com/article",
            content_hash="abc123",
        )
        assert entry.url == "https://example.com/article"
        assert entry.content_hash == "abc123"
        assert entry.entry_id is not None
        assert entry.status == SyncStatus.PENDING
        assert entry.created_at is not None

    def test_create_sync_entry_with_metadata(self):
        entry = SyncEntry(
            url="https://example.com/article",
            content_hash="abc123",
            title="Test Article",
            device_id="device-1",
            tags=["tech"],
        )
        assert entry.title == "Test Article"
        assert entry.device_id == "device-1"
        assert entry.tags == ["tech"]

    def test_sync_entry_to_dict(self):
        entry = SyncEntry(
            url="https://example.com/article",
            content_hash="abc123",
            title="Test",
            device_id="dev-1",
        )
        d = entry.to_dict()
        assert d["url"] == "https://example.com/article"
        assert d["content_hash"] == "abc123"
        assert d["device_id"] == "dev-1"
        assert d["status"] == "pending"

    def test_sync_entry_from_dict(self):
        data = {
            "entry_id": "e1",
            "url": "https://example.com/article",
            "content_hash": "abc123",
            "title": "Test",
            "device_id": "dev-1",
            "status": "synced",
            "direction": "upload",
            "tags": ["tech"],
            "created_at": "2024-01-01T00:00:00+00:00",
            "synced_at": "2024-01-01T01:00:00+00:00",
            "error": None,
        }
        entry = SyncEntry.from_dict(data)
        assert entry.entry_id == "e1"
        assert entry.url == "https://example.com/article"
        assert entry.status == SyncStatus.SYNCED
        assert entry.direction == SyncDirection.UPLOAD

    def test_sync_entry_from_dict_minimal(self):
        data = {"url": "https://example.com/minimal", "content_hash": "h1"}
        entry = SyncEntry.from_dict(data)
        assert entry.status == SyncStatus.PENDING
        assert entry.device_id == ""

    def test_sync_entry_mark_synced(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_synced()
        assert entry.status == SyncStatus.SYNCED
        assert entry.synced_at is not None

    def test_sync_entry_mark_failed(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_failed("Network error")
        assert entry.status == SyncStatus.FAILED
        assert entry.error == "Network error"

    def test_sync_entry_mark_pending(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_synced()
        entry.mark_pending()
        assert entry.status == SyncStatus.PENDING
        assert entry.synced_at is None

    def test_sync_entry_mark_conflict(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_conflict("Remote has newer version")
        assert entry.status == SyncStatus.CONFLICT
        assert entry.error == "Remote has newer version"

    def test_sync_entry_add_tag(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.add_tag("tech")
        assert "tech" in entry.tags

    def test_sync_entry_remove_tag(self):
        entry = SyncEntry(
            url="https://example.com/a", content_hash="h1", tags=["tech", "news"]
        )
        entry.remove_tag("tech")
        assert "tech" not in entry.tags

    def test_sync_entry_update_content_hash(self):
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        entry.update_content_hash("h2")
        assert entry.content_hash == "h2"
        assert entry.status == SyncStatus.PENDING


class TestSyncManifest:
    """Tests for SyncManifest class."""

    def test_create_manifest(self):
        manifest = SyncManifest()
        assert manifest.manifest_id is not None
        assert len(manifest.entries) == 0
        assert manifest.device_id == ""

    def test_create_manifest_with_device(self):
        manifest = SyncManifest(device_id="device-1")
        assert manifest.device_id == "device-1"

    def test_add_entry(self):
        manifest = SyncManifest(device_id="dev-1")
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        manifest.add_entry(entry)
        assert len(manifest.entries) == 1

    def test_add_duplicate_url(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1"))
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2"))
        assert len(manifest.entries) == 1
        assert manifest.get_entry_by_url("https://example.com/a").content_hash == "h2"

    def test_remove_entry(self):
        manifest = SyncManifest(device_id="dev-1")
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        manifest.add_entry(entry)
        manifest.remove_entry(entry.entry_id)
        assert len(manifest.entries) == 0

    def test_get_pending_entries(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.PENDING))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED))
        pending = manifest.get_pending_entries()
        assert len(pending) == 1

    def test_get_synced_entries(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.SYNCED))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.PENDING))
        synced = manifest.get_synced_entries()
        assert len(synced) == 1

    def test_get_failed_entries(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.FAILED))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED))
        failed = manifest.get_failed_entries()
        assert len(failed) == 1

    def test_get_conflict_entries(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.CONFLICT))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED))
        conflicts = manifest.get_conflict_entries()
        assert len(conflicts) == 1

    def test_get_entry_by_url(self):
        manifest = SyncManifest(device_id="dev-1")
        entry = SyncEntry(url="https://example.com/a", content_hash="h1")
        manifest.add_entry(entry)
        found = manifest.get_entry_by_url("https://example.com/a")
        assert found == entry

    def test_get_entry_by_url_not_found(self):
        manifest = SyncManifest()
        found = manifest.get_entry_by_url("https://example.com/notfound")
        assert found is None

    def test_get_manifest_stats(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.PENDING))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED))
        manifest.add_entry(SyncEntry(url="https://example.com/c", content_hash="h3", status=SyncStatus.FAILED))
        stats = manifest.get_stats()
        assert stats["total"] == 3
        assert stats["pending"] == 1
        assert stats["synced"] == 1
        assert stats["failed"] == 1

    def test_get_manifest_stats_empty(self):
        manifest = SyncManifest()
        stats = manifest.get_stats()
        assert stats["total"] == 0

    def test_to_dict(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1"))
        d = manifest.to_dict()
        assert d["device_id"] == "dev-1"
        assert len(d["entries"]) == 1

    def test_from_dict(self):
        data = {
            "manifest_id": "m1",
            "device_id": "dev-1",
            "entries": [
                {
                    "entry_id": "e1",
                    "url": "https://example.com/a",
                    "content_hash": "h1",
                    "title": "Test",
                    "status": "synced",
                    "direction": "upload",
                    "tags": [],
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "synced_at": "2024-01-01T01:00:00+00:00",
                    "error": None,
                }
            ],
        }
        manifest = SyncManifest.from_dict(data)
        assert manifest.manifest_id == "m1"
        assert manifest.device_id == "dev-1"
        assert len(manifest.entries) == 1

    def test_clear_all(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1"))
        manifest.clear_all()
        assert len(manifest.entries) == 0

    def test_retry_failed(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.FAILED))
        manifest.retry_failed()
        assert len(manifest.get_pending_entries()) == 1

    def test_get_entries_by_direction(self):
        manifest = SyncManifest(device_id="dev-1")
        manifest.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", direction=SyncDirection.UPLOAD))
        manifest.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", direction=SyncDirection.DOWNLOAD))
        uploads = manifest.get_entries_by_direction(SyncDirection.UPLOAD)
        assert len(uploads) == 1

    def test_merge_with_remote_manifest(self):
        local = SyncManifest(device_id="dev-1")
        local.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.SYNCED))
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED))
        merged = local.merge_with(remote)
        assert len(merged.entries) == 2

    def test_merge_detects_conflicts(self):
        local = SyncManifest(device_id="dev-1")
        local.add_entry(SyncEntry(url="https://example.com/a", content_hash="h1", status=SyncStatus.SYNCED))
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2", status=SyncStatus.SYNCED))
        merged = local.merge_with(remote)
        conflict_entry = merged.get_entry_by_url("https://example.com/a")
        assert conflict_entry.status == SyncStatus.CONFLICT


class TestSyncEngine:
    """Tests for SyncEngine class."""

    def test_create_engine(self):
        engine = SyncEngine(device_id="dev-1")
        assert engine.device_id == "dev-1"
        assert engine.manifest.device_id == "dev-1"

    def test_add_item_for_sync(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test Article")
        assert len(engine.manifest.entries) == 1
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.title == "Test Article"
        assert entry.status == SyncStatus.PENDING

    def test_add_item_already_synced(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test Updated")
        assert len(engine.manifest.entries) == 1

    def test_add_item_hash_changed(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_synced()
        engine.add_item_for_sync("https://example.com/a", "h2", "Test Updated")
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.content_hash == "h2"
        assert entry.status == SyncStatus.PENDING

    def test_run_sync_no_pending(self):
        engine = SyncEngine(device_id="dev-1")
        result = engine.run_sync()
        assert result["synced"] == 0
        assert result["failed"] == 0

    def test_run_sync_marks_as_synced(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        result = engine.run_sync()
        assert result["synced"] == 1
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.status == SyncStatus.SYNCED

    def test_run_sync_with_callback(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        synced_urls = []
        def on_sync(url, entry):
            synced_urls.append(url)
        engine.run_sync(on_sync=on_sync)
        assert "https://example.com/a" in synced_urls

    def test_run_sync_with_failure_callback(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        failed_urls = []
        def on_sync(url, entry):
            raise Exception("Network error")
        def on_fail(url, entry, error):
            failed_urls.append(url)
        engine.run_sync(on_sync=on_sync, on_fail=on_fail)
        assert "https://example.com/a" in failed_urls

    def test_apply_remote_manifest(self):
        engine = SyncEngine(device_id="dev-1")
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/b", content_hash="h2", status=SyncStatus.SYNCED, direction=SyncDirection.DOWNLOAD))
        engine.apply_remote_manifest(remote)
        entry = engine.manifest.get_entry_by_url("https://example.com/b")
        assert entry is not None
        assert entry.content_hash == "h2"

    def test_apply_remote_manifest_detects_conflict(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_synced()
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2", status=SyncStatus.SYNCED))
        engine.apply_remote_manifest(remote)
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.status == SyncStatus.CONFLICT

    def test_resolve_conflict_local_wins(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Local Version")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_synced()
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2", status=SyncStatus.SYNCED))
        engine.apply_remote_manifest(remote)
        engine.resolve_conflict("https://example.com/a", ConflictResolution.LOCAL_WINS)
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.content_hash == "h1"
        assert entry.status == SyncStatus.SYNCED

    def test_resolve_conflict_remote_wins(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Local Version")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_synced()
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2", status=SyncStatus.SYNCED))
        engine.apply_remote_manifest(remote)
        engine.resolve_conflict("https://example.com/a", ConflictResolution.REMOTE_WINS)
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.content_hash == "h2"
        assert entry.status == SyncStatus.SYNCED

    def test_resolve_conflict_newest_wins(self):
        engine = SyncEngine(device_id="dev-1")
        local_entry = SyncEntry(url="https://example.com/a", content_hash="h1", created_at="2024-01-01T00:00:00+00:00")
        engine.manifest.add_entry(local_entry)
        engine.manifest.get_entry_by_url("https://example.com/a").mark_synced()
        remote = SyncManifest(device_id="dev-2")
        remote.add_entry(SyncEntry(url="https://example.com/a", content_hash="h2", status=SyncStatus.SYNCED, created_at="2024-06-01T00:00:00+00:00"))
        engine.apply_remote_manifest(remote)
        engine.resolve_conflict("https://example.com/a", ConflictResolution.NEWEST_WINS)
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.content_hash == "h2"

    def test_get_sync_status(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        status = engine.get_sync_status()
        assert status["pending"] == 1
        assert status["total"] == 1

    def test_get_sync_status_empty(self):
        engine = SyncEngine(device_id="dev-1")
        status = engine.get_sync_status()
        assert status["pending"] == 0
        assert status["total"] == 0

    def test_remove_item_from_sync(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.remove_item_from_sync("https://example.com/a")
        assert engine.manifest.get_entry_by_url("https://example.com/a") is None

    def test_get_conflicts(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_conflict("test conflict")
        conflicts = engine.get_conflicts()
        assert len(conflicts) == 1

    def test_batch_add_for_sync(self):
        engine = SyncEngine(device_id="dev-1")
        items = [
            ("https://example.com/a", "h1", "A"),
            ("https://example.com/b", "h2", "B"),
            ("https://example.com/c", "h3", "C"),
        ]
        engine.batch_add_for_sync(items)
        assert len(engine.manifest.entries) == 3

    def test_retry_all_failed(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        engine.manifest.get_entry_by_url("https://example.com/a").mark_failed("error")
        engine.retry_all_failed()
        entry = engine.manifest.get_entry_by_url("https://example.com/a")
        assert entry.status == SyncStatus.PENDING

    def test_to_dict(self):
        engine = SyncEngine(device_id="dev-1")
        engine.add_item_for_sync("https://example.com/a", "h1", "Test")
        d = engine.to_dict()
        assert d["device_id"] == "dev-1"
        assert len(d["manifest"]["entries"]) == 1

    def test_from_dict(self):
        data = {
            "device_id": "dev-1",
            "manifest": {
                "manifest_id": "m1",
                "device_id": "dev-1",
                "entries": [
                    {
                        "entry_id": "e1",
                        "url": "https://example.com/a",
                        "content_hash": "h1",
                        "title": "Test",
                        "status": "synced",
                        "direction": "upload",
                        "tags": [],
                        "created_at": "2024-01-01T00:00:00+00:00",
                        "synced_at": "2024-01-01T01:00:00+00:00",
                        "error": None,
                    }
                ],
            },
        }
        engine = SyncEngine.from_dict(data)
        assert engine.device_id == "dev-1"
        assert len(engine.manifest.entries) == 1


class TestSyncConflict:
    """Tests for SyncConflict dataclass."""

    def test_create_conflict(self):
        local = SyncEntry(url="https://example.com/a", content_hash="h1")
        remote = SyncEntry(url="https://example.com/a", content_hash="h2")
        conflict = SyncConflict(url="https://example.com/a", local=local, remote=remote)
        assert conflict.url == "https://example.com/a"
        assert conflict.local == local
        assert conflict.remote == remote

    def test_conflict_to_dict(self):
        local = SyncEntry(url="https://example.com/a", content_hash="h1")
        remote = SyncEntry(url="https://example.com/a", content_hash="h2")
        conflict = SyncConflict(url="https://example.com/a", local=local, remote=remote)
        d = conflict.to_dict()
        assert d["url"] == "https://example.com/a"
        assert d["local_hash"] == "h1"
        assert d["remote_hash"] == "h2"


class TestSyncStatus:
    """Tests for SyncStatus enum."""

    def test_status_values(self):
        assert SyncStatus.PENDING.value == "pending"
        assert SyncStatus.SYNCED.value == "synced"
        assert SyncStatus.FAILED.value == "failed"
        assert SyncStatus.CONFLICT.value == "conflict"

    def test_status_from_string(self):
        assert SyncStatus("pending") == SyncStatus.PENDING
        assert SyncStatus("synced") == SyncStatus.SYNCED

    def test_status_invalid(self):
        with pytest.raises(ValueError):
            SyncStatus("invalid")


class TestSyncDirection:
    """Tests for SyncDirection enum."""

    def test_direction_values(self):
        assert SyncDirection.UPLOAD.value == "upload"
        assert SyncDirection.DOWNLOAD.value == "download"

    def test_direction_from_string(self):
        assert SyncDirection("upload") == SyncDirection.UPLOAD
        assert SyncDirection("download") == SyncDirection.DOWNLOAD


class TestConflictResolution:
    """Tests for ConflictResolution enum."""

    def test_resolution_values(self):
        assert ConflictResolution.LOCAL_WINS.value == "local_wins"
        assert ConflictResolution.REMOTE_WINS.value == "remote_wins"
        assert ConflictResolution.NEWEST_WINS.value == "newest_wins"
