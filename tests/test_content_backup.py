"""Tests for content_backup module - backup and restore functionality."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_backup import (
    BackupEntry,
    BackupArchive,
    BackupManager,
    BackupStatus,
    BackupType,
)


class TestBackupEntry:
    """Tests for BackupEntry dataclass."""

    def test_create_backup_entry_basic(self):
        entry = BackupEntry(
            url="https://example.com/article",
            content_hash="abc123",
        )
        assert entry.url == "https://example.com/article"
        assert entry.content_hash == "abc123"
        assert entry.entry_id is not None
        assert entry.status == BackupStatus.PENDING
        assert entry.created_at is not None

    def test_create_backup_entry_with_content(self):
        entry = BackupEntry(
            url="https://example.com/article",
            content_hash="abc123",
            content="<html>test</html>",
            title="Test Article",
        )
        assert entry.content == "<html>test</html>"
        assert entry.title == "Test Article"
        assert entry.content_length == 17

    def test_create_backup_entry_with_metadata(self):
        entry = BackupEntry(
            url="https://example.com/article",
            content_hash="abc123",
            author="John Doe",
            tags=["tech", "news"],
            published_at="2024-01-01T00:00:00+00:00",
        )
        assert entry.author == "John Doe"
        assert entry.tags == ["tech", "news"]
        assert entry.published_at == "2024-01-01T00:00:00+00:00"

    def test_backup_entry_to_dict(self):
        entry = BackupEntry(
            url="https://example.com/article",
            content_hash="abc123",
            title="Test",
            content="<html>test</html>",
        )
        d = entry.to_dict()
        assert d["url"] == "https://example.com/article"
        assert d["content_hash"] == "abc123"
        assert d["title"] == "Test"
        assert d["content"] == "<html>test</html>"
        assert d["content_length"] == 17

    def test_backup_entry_from_dict(self):
        data = {
            "entry_id": "b1",
            "url": "https://example.com/article",
            "content_hash": "abc123",
            "title": "Test",
            "content": "<html>test</html>",
            "author": "Jane",
            "tags": ["tech"],
            "status": "completed",
            "backup_type": "full",
            "content_length": 14,
            "created_at": "2024-01-01T00:00:00+00:00",
            "published_at": None,
            "error": None,
        }
        entry = BackupEntry.from_dict(data)
        assert entry.entry_id == "b1"
        assert entry.url == "https://example.com/article"
        assert entry.status == BackupStatus.COMPLETED
        assert entry.backup_type == BackupType.FULL

    def test_backup_entry_from_dict_minimal(self):
        data = {"url": "https://example.com/minimal", "content_hash": "h1"}
        entry = BackupEntry.from_dict(data)
        assert entry.status == BackupStatus.PENDING
        assert entry.backup_type == BackupType.FULL

    def test_backup_entry_mark_completed(self):
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_completed()
        assert entry.status == BackupStatus.COMPLETED

    def test_backup_entry_mark_failed(self):
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_failed("Disk full")
        assert entry.status == BackupStatus.FAILED
        assert entry.error == "Disk full"

    def test_backup_entry_mark_pending(self):
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        entry.mark_completed()
        entry.mark_pending()
        assert entry.status == BackupStatus.PENDING

    def test_backup_entry_add_tag(self):
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        entry.add_tag("tech")
        assert "tech" in entry.tags

    def test_backup_entry_remove_tag(self):
        entry = BackupEntry(
            url="https://example.com/a", content_hash="h1", tags=["tech", "news"]
        )
        entry.remove_tag("tech")
        assert "tech" not in entry.tags

    def test_backup_entry_set_content(self):
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        entry.set_content("<html>content</html>")
        assert entry.content == "<html>content</html>"
        assert entry.content_length == 20


class TestBackupArchive:
    """Tests for BackupArchive class."""

    def test_create_archive(self):
        archive = BackupArchive()
        assert archive.archive_id is not None
        assert len(archive.entries) == 0

    def test_create_archive_with_name(self):
        archive = BackupArchive(name="my-backup")
        assert archive.name == "my-backup"

    def test_add_entry(self):
        archive = BackupArchive()
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        archive.add_entry(entry)
        assert len(archive.entries) == 1

    def test_add_duplicate_url(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1"))
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h2"))
        assert len(archive.entries) == 1
        assert archive.get_entry_by_url("https://example.com/a").content_hash == "h2"

    def test_remove_entry(self):
        archive = BackupArchive()
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        archive.add_entry(entry)
        archive.remove_entry(entry.entry_id)
        assert len(archive.entries) == 0

    def test_get_entry_by_url(self):
        archive = BackupArchive()
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        archive.add_entry(entry)
        found = archive.get_entry_by_url("https://example.com/a")
        assert found == entry

    def test_get_entry_by_url_not_found(self):
        archive = BackupArchive()
        found = archive.get_entry_by_url("https://example.com/notfound")
        assert found is None

    def test_get_completed_entries(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1", status=BackupStatus.COMPLETED))
        archive.add_entry(BackupEntry(url="https://example.com/b", content_hash="h2", status=BackupStatus.PENDING))
        completed = archive.get_completed_entries()
        assert len(completed) == 1

    def test_get_failed_entries(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1", status=BackupStatus.FAILED))
        archive.add_entry(BackupEntry(url="https://example.com/b", content_hash="h2", status=BackupStatus.COMPLETED))
        failed = archive.get_failed_entries()
        assert len(failed) == 1

    def test_get_archive_stats(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1", status=BackupStatus.COMPLETED))
        archive.add_entry(BackupEntry(url="https://example.com/b", content_hash="h2", status=BackupStatus.FAILED))
        stats = archive.get_stats()
        assert stats["total"] == 2
        assert stats["completed"] == 1
        assert stats["failed"] == 1

    def test_get_archive_stats_empty(self):
        archive = BackupArchive()
        stats = archive.get_stats()
        assert stats["total"] == 0

    def test_get_total_content_size(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1", content="12345"))
        archive.add_entry(BackupEntry(url="https://example.com/b", content_hash="h2", content="1234567890"))
        size = archive.get_total_content_size()
        assert size == 15

    def test_to_dict(self):
        archive = BackupArchive(name="test-backup")
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1"))
        d = archive.to_dict()
        assert d["name"] == "test-backup"
        assert len(d["entries"]) == 1

    def test_from_dict(self):
        data = {
            "archive_id": "a1",
            "name": "restored-backup",
            "backup_type": "full",
            "entries": [
                {
                    "entry_id": "e1",
                    "url": "https://example.com/a",
                    "content_hash": "h1",
                    "title": "Test",
                    "content": "<html>a</html>",
                    "author": "",
                    "tags": [],
                    "status": "completed",
                    "backup_type": "full",
                    "content_length": 11,
                    "created_at": "2024-01-01T00:00:00+00:00",
                    "published_at": None,
                    "error": None,
                }
            ],
        }
        archive = BackupArchive.from_dict(data)
        assert archive.archive_id == "a1"
        assert archive.name == "restored-backup"
        assert len(archive.entries) == 1

    def test_clear_all(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1"))
        archive.clear_all()
        assert len(archive.entries) == 0

    def test_contains_url(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1"))
        assert archive.contains_url("https://example.com/a") is True
        assert archive.contains_url("https://example.com/b") is False

    def test_batch_add(self):
        archive = BackupArchive()
        entries = [
            BackupEntry(url="https://example.com/a", content_hash="h1"),
            BackupEntry(url="https://example.com/b", content_hash="h2"),
        ]
        archive.batch_add(entries)
        assert len(archive.entries) == 2

    def test_get_entries_sorted_by_date(self):
        archive = BackupArchive()
        archive.add_entry(BackupEntry(url="https://example.com/a", content_hash="h1", created_at="2024-01-01T00:00:00+00:00"))
        archive.add_entry(BackupEntry(url="https://example.com/b", content_hash="h2", created_at="2024-06-01T00:00:00+00:00"))
        sorted_entries = archive.get_entries_sorted_by_date()
        assert sorted_entries[0].url == "https://example.com/b"


class TestBackupManager:
    """Tests for BackupManager class."""

    def test_create_manager(self):
        mgr = BackupManager()
        assert len(mgr.archives) == 0

    def test_create_backup(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("my-backup")
        assert archive_id is not None
        assert len(mgr.archives) == 1

    def test_create_backup_with_name(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("custom-name")
        archive = mgr.get_archive(archive_id)
        assert archive.name == "custom-name"

    def test_get_archive(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        archive = mgr.get_archive(archive_id)
        assert archive is not None

    def test_get_archive_not_found(self):
        mgr = BackupManager()
        archive = mgr.get_archive("nonexistent")
        assert archive is None

    def test_add_entry_to_backup(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        entry = BackupEntry(url="https://example.com/a", content_hash="h1")
        mgr.add_entry_to_backup(archive_id, entry)
        archive = mgr.get_archive(archive_id)
        assert len(archive.entries) == 1

    def test_delete_backup(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        mgr.delete_backup(archive_id)
        assert len(mgr.archives) == 0

    def test_delete_backup_not_found(self):
        mgr = BackupManager()
        mgr.delete_backup("nonexistent")
        assert len(mgr.archives) == 0

    def test_list_backups(self):
        mgr = BackupManager()
        mgr.create_backup("backup-1")
        mgr.create_backup("backup-2")
        backups = mgr.list_backups()
        assert len(backups) == 2

    def test_restore_from_backup(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        entry = BackupEntry(
            url="https://example.com/a",
            content_hash="h1",
            content="<html>test</html>",
            title="Test Article",
            status=BackupStatus.COMPLETED,
        )
        mgr.add_entry_to_backup(archive_id, entry)
        restored = mgr.restore_from_backup(archive_id)
        assert len(restored) == 1
        assert restored[0].url == "https://example.com/a"

    def test_restore_from_backup_by_url(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        mgr.add_entry_to_backup(archive_id, BackupEntry(
            url="https://example.com/a", content_hash="h1", content="<html>a</html>", status=BackupStatus.COMPLETED
        ))
        mgr.add_entry_to_backup(archive_id, BackupEntry(
            url="https://example.com/b", content_hash="h2", content="<html>b</html>", status=BackupStatus.COMPLETED
        ))
        restored = mgr.restore_from_backup(archive_id, url="https://example.com/a")
        assert len(restored) == 1
        assert restored[0].url == "https://example.com/a"

    def test_restore_from_backup_not_found(self):
        mgr = BackupManager()
        restored = mgr.restore_from_backup("nonexistent")
        assert len(restored) == 0

    def test_get_backup_stats(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        mgr.add_entry_to_backup(archive_id, BackupEntry(
            url="https://example.com/a", content_hash="h1", status=BackupStatus.COMPLETED
        ))
        stats = mgr.get_backup_stats(archive_id)
        assert stats["total"] == 1

    def test_get_backup_stats_not_found(self):
        mgr = BackupManager()
        stats = mgr.get_backup_stats("nonexistent")
        assert stats is None

    def test_get_latest_backup(self):
        mgr = BackupManager()
        mgr.create_backup("backup-1")
        latest_id = mgr.create_backup("backup-2")
        latest = mgr.get_latest_backup()
        assert latest.archive_id == latest_id

    def test_get_latest_backup_empty(self):
        mgr = BackupManager()
        latest = mgr.get_latest_backup()
        assert latest is None

    def test_compare_backups(self):
        mgr = BackupManager()
        id1 = mgr.create_backup("backup-1")
        id2 = mgr.create_backup("backup-2")
        mgr.add_entry_to_backup(id1, BackupEntry(url="https://example.com/a", content_hash="h1"))
        mgr.add_entry_to_backup(id2, BackupEntry(url="https://example.com/a", content_hash="h2"))
        mgr.add_entry_to_backup(id2, BackupEntry(url="https://example.com/b", content_hash="h3"))
        diff = mgr.compare_backups(id1, id2)
        assert "changed" in diff
        assert "added" in diff

    def test_compare_backups_same(self):
        mgr = BackupManager()
        id1 = mgr.create_backup("backup-1")
        id2 = mgr.create_backup("backup-2")
        mgr.add_entry_to_backup(id1, BackupEntry(url="https://example.com/a", content_hash="h1"))
        mgr.add_entry_to_backup(id2, BackupEntry(url="https://example.com/a", content_hash="h1"))
        diff = mgr.compare_backups(id1, id2)
        assert len(diff.get("changed", [])) == 0
        assert len(diff.get("added", [])) == 0

    def test_merge_backups(self):
        mgr = BackupManager()
        id1 = mgr.create_backup("backup-1")
        id2 = mgr.create_backup("backup-2")
        mgr.add_entry_to_backup(id1, BackupEntry(url="https://example.com/a", content_hash="h1"))
        mgr.add_entry_to_backup(id2, BackupEntry(url="https://example.com/b", content_hash="h2"))
        merged_id = mgr.merge_backups(id1, id2)
        merged = mgr.get_archive(merged_id)
        assert len(merged.entries) == 2

    def test_to_dict(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        mgr.add_entry_to_backup(archive_id, BackupEntry(url="https://example.com/a", content_hash="h1"))
        d = mgr.to_dict()
        assert len(d["archives"]) == 1

    def test_from_dict(self):
        data = {
            "archives": [
                {
                    "archive_id": "a1",
                    "name": "restored",
                    "backup_type": "full",
                    "entries": [
                        {
                            "entry_id": "e1",
                            "url": "https://example.com/a",
                            "content_hash": "h1",
                            "title": "Test",
                            "content": "<html>a</html>",
                            "author": "",
                            "tags": [],
                            "status": "completed",
                            "backup_type": "full",
                            "content_length": 11,
                            "created_at": "2024-01-01T00:00:00+00:00",
                            "published_at": None,
                            "error": None,
                        }
                    ],
                }
            ],
        }
        mgr = BackupManager.from_dict(data)
        assert len(mgr.archives) == 1
        assert len(mgr.archives[0].entries) == 1

    def test_get_total_backup_size(self):
        mgr = BackupManager()
        archive_id = mgr.create_backup("test")
        mgr.add_entry_to_backup(archive_id, BackupEntry(
            url="https://example.com/a", content_hash="h1", content="12345"
        ))
        size = mgr.get_total_backup_size()
        assert size == 5

    def test_get_total_backup_size_empty(self):
        mgr = BackupManager()
        size = mgr.get_total_backup_size()
        assert size == 0

    def test_cleanup_old_backups(self):
        mgr = BackupManager()
        mgr.create_backup("old-1")
        mgr.create_backup("old-2")
        latest = mgr.create_backup("latest")
        mgr.cleanup_old_backups(keep=1)
        assert len(mgr.archives) == 1
        assert mgr.archives[0].archive_id == latest

    def test_cleanup_old_backups_keep_all(self):
        mgr = BackupManager()
        mgr.create_backup("keep-1")
        mgr.create_backup("keep-2")
        mgr.cleanup_old_backups(keep=10)
        assert len(mgr.archives) == 2


class TestBackupStatus:
    """Tests for BackupStatus enum."""

    def test_status_values(self):
        assert BackupStatus.PENDING.value == "pending"
        assert BackupStatus.COMPLETED.value == "completed"
        assert BackupStatus.FAILED.value == "failed"

    def test_status_from_string(self):
        assert BackupStatus("pending") == BackupStatus.PENDING
        assert BackupStatus("completed") == BackupStatus.COMPLETED

    def test_status_invalid(self):
        with pytest.raises(ValueError):
            BackupStatus("invalid")


class TestBackupType:
    """Tests for BackupType enum."""

    def test_type_values(self):
        assert BackupType.FULL.value == "full"
        assert BackupType.INCREMENTAL.value == "incremental"

    def test_type_from_string(self):
        assert BackupType("full") == BackupType.FULL
        assert BackupType("incremental") == BackupType.INCREMENTAL
