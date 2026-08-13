"""Tests for backup manager."""

from datetime import datetime, timedelta, timezone

from personal_index.content_backup.backup_manager import (
    BackupConfig,
    BackupManager,
)
from personal_index.content_backup.backup_store import BackupStore


class TestBackupConfig:
    def test_defaults(self):
        c = BackupConfig()
        assert c.max_backups == 10
        assert c.include_metadata is True
        assert c.compression is False

    def test_custom(self):
        c = BackupConfig(max_backups=5, compression=True)
        assert c.max_backups == 5
        assert c.compression is True


class TestBackupManager:
    def test_create_backup(self):
        mgr = BackupManager()
        items = [{"id": "1", "title": "Page 1"}]
        entry = mgr.create_backup(items)
        assert entry.item_count == 1
        assert entry.data == items

    def test_create_backup_with_label(self):
        mgr = BackupManager()
        entry = mgr.create_backup([{"id": "1"}], label="nightly")
        assert entry.metadata["label"] == "nightly"

    def test_create_backup_empty_items(self):
        mgr = BackupManager()
        entry = mgr.create_backup([])
        assert entry.item_count == 0
        assert entry.data == []

    def test_create_incremental_new_items(self):
        mgr = BackupManager()
        first = mgr.create_backup([{"id": "1"}, {"id": "2"}])
        second = mgr.create_incremental_backup(
            [{"id": "2"}, {"id": "3"}], last_backup_id=first.backup_id
        )
        assert second.item_count == 1
        assert second.data[0]["id"] == "3"

    def test_create_incremental_no_new_items(self):
        mgr = BackupManager()
        first = mgr.create_backup([{"id": "1"}, {"id": "2"}])
        second = mgr.create_incremental_backup(
            [{"id": "1"}, {"id": "2"}], last_backup_id=first.backup_id
        )
        assert second.item_count == 0

    def test_create_incremental_no_last_backup(self):
        mgr = BackupManager()
        entry = mgr.create_incremental_backup([{"id": "1"}])
        assert entry.item_count == 1

    def test_get_backup_summary_empty(self):
        mgr = BackupManager()
        summary = mgr.get_backup_summary()
        assert summary["total_backups"] == 0
        assert summary["latest_backup"] is None
        assert summary["oldest_backup"] is None

    def test_get_backup_summary_with_backups(self):
        mgr = BackupManager()
        mgr.create_backup([{"id": "1"}], label="first")
        mgr.create_backup([{"id": "2"}, {"id": "3"}], label="second")
        summary = mgr.get_backup_summary()
        assert summary["total_items_backed_up"] >= 1

    def test_cleanup_old_backups(self):
        store = BackupStore()
        old_time = datetime.now(timezone.utc) - timedelta(days=60)
        store.add_backup([{"id": "1"}], backup_id="old1")
        store.backups["old1"].timestamp = old_time
        mgr = BackupManager(store=store)
        removed = mgr.cleanup_old_backups(older_than=timedelta(days=30))
        assert removed == 1

    def test_cleanup_keeps_recent(self):
        mgr = BackupManager()
        mgr.create_backup([{"id": "1"}])
        removed = mgr.cleanup_old_backups(older_than=timedelta(days=30))
        assert removed == 0

    def test_config_max_backups_enforced(self):
        mgr = BackupManager(config=BackupConfig(max_backups=2))
        mgr.create_backup([{"id": "1"}])
        mgr.create_backup([{"id": "2"}])
        mgr.create_backup([{"id": "3"}])
        assert len(mgr.store.list_backups()) <= 2

    def test_post_init_syncs_max_backups(self):
        mgr = BackupManager(config=BackupConfig(max_backups=5))
        assert mgr.store.max_backups == 5
