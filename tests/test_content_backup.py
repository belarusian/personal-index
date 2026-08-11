"""Tests for content backup module."""

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from personal_index.content_backup.backup_manager import BackupConfig, BackupManager
from personal_index.content_backup.backup_store import BackupEntry, BackupStore
from personal_index.content_backup.restore import RestoreManager, RestoreResult


class TestBackupStore:
    def test_add_backup(self) -> None:
        store = BackupStore()
        items = [{"id": "1", "title": "Test"}]
        entry = store.add_backup(items, backup_id="b1")
        assert entry.backup_id == "b1"
        assert entry.item_count == 1

    def test_get_backup(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        entry = store.get_backup("b1")
        assert entry is not None
        assert entry.item_count == 1

    def test_get_backup_not_found(self) -> None:
        store = BackupStore()
        assert store.get_backup("nonexistent") is None

    def test_list_backups_sorted(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        store.add_backup([{"id": "2"}], backup_id="b2")
        backups = store.list_backups()
        assert len(backups) == 2
        assert backups[0].timestamp >= backups[1].timestamp

    def test_delete_backup(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        assert store.delete_backup("b1") is True
        assert store.get_backup("b1") is None

    def test_delete_backup_not_found(self) -> None:
        store = BackupStore()
        assert store.delete_backup("nonexistent") is False

    def test_get_latest(self) -> None:
        store = BackupStore()
        assert store.get_latest() is None
        store.add_backup([{"id": "1"}], backup_id="b1")
        latest = store.get_latest()
        assert latest is not None
        assert latest.backup_id == "b1"

    def test_max_backups_eviction(self) -> None:
        store = BackupStore(max_backups=2)
        store.add_backup([{"id": "1"}], backup_id="b1")
        store.add_backup([{"id": "2"}], backup_id="b2")
        store.add_backup([{"id": "3"}], backup_id="b3")
        assert len(store.backups) == 2

    def test_export_import(self, tmp_path: Path) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1", "title": "Test"}], backup_id="b1")
        filepath = tmp_path / "backup.json"
        store.export_to_file("b1", filepath)
        assert filepath.exists()

        store2 = BackupStore()
        entry = store2.import_from_file(filepath)
        assert entry.backup_id == "b1"
        assert entry.item_count == 1


class TestBackupManager:
    def test_create_backup(self) -> None:
        manager = BackupManager()
        items = [{"id": "1", "title": "Test"}]
        entry = manager.create_backup(items, label="test")
        assert entry.item_count == 1
        assert entry.metadata["label"] == "test"

    def test_incremental_backup(self) -> None:
        manager = BackupManager()
        items1 = [{"id": "1", "title": "A"}]
        entry1 = manager.create_backup(items1)

        items2 = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
        entry2 = manager.create_incremental_backup(items2, entry1.backup_id)
        assert entry2.item_count == 1
        assert entry2.data[0]["id"] == "2"

    def test_backup_summary(self) -> None:
        manager = BackupManager()
        summary = manager.get_backup_summary()
        assert summary["total_backups"] == 0

        manager.create_backup([{"id": "1"}])
        summary = manager.get_backup_summary()
        assert summary["total_backups"] == 1

    def test_cleanup_old_backups(self) -> None:
        manager = BackupManager()
        manager.store.add_backup(
            [{"id": "1"}],
            backup_id="b1",
        )
        old_entry = manager.store.backups["b1"]
        old_entry.timestamp = datetime.now(timezone.utc) - timedelta(days=60)
        manager.store.backups["b1"] = old_entry

        removed = manager.cleanup_old_backups()
        assert removed == 1


class TestRestoreManager:
    def test_restore_from_backup(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}, {"id": "2"}], backup_id="b1")
        manager = RestoreManager(store=store)
        result = manager.restore_from_backup("b1")
        assert result.success is True
        assert result.items_restored == 2

    def test_restore_not_found(self) -> None:
        manager = RestoreManager()
        result = manager.restore_from_backup("nonexistent")
        assert result.success is False
        assert len(result.errors) == 1

    def test_restore_latest(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        manager = RestoreManager(store=store)
        result = manager.restore_latest()
        assert result.success is True

    def test_restore_latest_no_backups(self) -> None:
        manager = RestoreManager()
        result = manager.restore_latest()
        assert result.success is False

    def test_restore_items(self) -> None:
        store = BackupStore()
        items = [{"id": "1", "title": "Test"}]
        store.add_backup(items, backup_id="b1")
        manager = RestoreManager(store=store)
        restored = manager.restore_items("b1")
        assert len(restored) == 1
        assert restored[0]["title"] == "Test"

    def test_merge_restore(self) -> None:
        store = BackupStore()
        store.add_backup([{"id": "1"}, {"id": "2"}], backup_id="b1")
        manager = RestoreManager(store=store)
        existing = [{"id": "1", "title": "Updated"}]
        merged = manager.merge_restore("b1", existing)
        assert len(merged) == 2
