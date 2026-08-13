"""Tests for restore manager."""

from personal_index.content_backup.backup_store import BackupStore
from personal_index.content_backup.restore import (
    RestoreManager,
    RestoreResult,
)


class TestRestoreResult:
    def test_success(self):
        r = RestoreResult(success=True, items_restored=5, backup_id="b1")
        assert r.success is True
        assert r.items_restored == 5
        assert r.errors == []

    def test_failure(self):
        r = RestoreResult(success=False, items_restored=0, backup_id="b1", errors=["not found"])
        assert r.success is False
        assert r.errors == ["not found"]


class TestRestoreManager:
    def test_restore_from_backup_success(self):
        store = BackupStore()
        store.add_backup([{"id": "1"}, {"id": "2"}], backup_id="b1")
        mgr = RestoreManager(store=store)
        result = mgr.restore_from_backup("b1")
        assert result.success is True
        assert result.items_restored == 2

    def test_restore_from_backup_not_found(self):
        mgr = RestoreManager()
        result = mgr.restore_from_backup("nonexistent")
        assert result.success is False
        assert result.items_restored == 0
        assert "not found" in result.errors[0]

    def test_restore_latest_success(self):
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        mgr = RestoreManager(store=store)
        result = mgr.restore_latest()
        assert result.success is True

    def test_restore_latest_no_backups(self):
        mgr = RestoreManager()
        result = mgr.restore_latest()
        assert result.success is False
        assert "No backups available" in result.errors

    def test_restore_items_success(self):
        store = BackupStore()
        items = [{"id": "1", "title": "A"}, {"id": "2", "title": "B"}]
        store.add_backup(items, backup_id="b1")
        mgr = RestoreManager(store=store)
        restored = mgr.restore_items("b1")
        assert len(restored) == 2
        assert restored[0]["title"] == "A"

    def test_restore_items_not_found(self):
        mgr = RestoreManager()
        restored = mgr.restore_items("nonexistent")
        assert restored == []

    def test_restore_items_copies_data(self):
        store = BackupStore()
        items = [{"id": "1", "title": "A"}]
        store.add_backup(items, backup_id="b1")
        mgr = RestoreManager(store=store)
        restored = mgr.restore_items("b1")
        restored[0]["title"] = "Modified"
        assert store.get_backup("b1").data[0]["title"] == "A"

    def test_merge_restore_no_overlap(self):
        store = BackupStore()
        store.add_backup([{"id": "3"}, {"id": "4"}], backup_id="b1")
        mgr = RestoreManager(store=store)
        existing = [{"id": "1"}, {"id": "2"}]
        merged = mgr.merge_restore("b1", existing)
        assert len(merged) == 4

    def test_merge_restore_with_overlap(self):
        store = BackupStore()
        store.add_backup([{"id": "2"}, {"id": "3"}], backup_id="b1")
        mgr = RestoreManager(store=store)
        existing = [{"id": "1"}, {"id": "2"}]
        merged = mgr.merge_restore("b1", existing)
        assert len(merged) == 3

    def test_merge_restore_not_found(self):
        mgr = RestoreManager()
        existing = [{"id": "1"}]
        merged = mgr.merge_restore("nonexistent", existing)
        assert merged == existing

    def test_merge_restore_empty_existing(self):
        store = BackupStore()
        store.add_backup([{"id": "1"}], backup_id="b1")
        mgr = RestoreManager(store=store)
        merged = mgr.merge_restore("b1", [])
        assert len(merged) == 1

    def test_merge_restore_empty_backup(self):
        store = BackupStore()
        store.add_backup([], backup_id="b1")
        mgr = RestoreManager(store=store)
        existing = [{"id": "1"}]
        merged = mgr.merge_restore("b1", existing)
        assert len(merged) == 1
