"""Tests for backup store."""

import tempfile
import time

from personal_index.content_backup.backup_store import BackupStore


class TestBackupStore:
    def test_add_backup(self):
        s = BackupStore()
        entry = s.add_backup([{"id": "1"}], backup_id="b1")
        assert entry.backup_id == "b1"
        assert entry.item_count == 1

    def test_add_backup_auto_id(self):
        s = BackupStore()
        entry = s.add_backup([{"id": "1"}])
        assert entry.backup_id.startswith("backup_")

    def test_get_backup(self):
        s = BackupStore()
        s.add_backup([], backup_id="b1")
        assert s.get_backup("b1") is not None

    def test_get_backup_missing(self):
        s = BackupStore()
        assert s.get_backup("missing") is None

    def test_list_backups(self):
        s = BackupStore()
        s.add_backup([], backup_id="b1")
        s.add_backup([], backup_id="b2")
        assert len(s.list_backups()) == 2

    def test_delete_backup(self):
        s = BackupStore()
        s.add_backup([], backup_id="b1")
        assert s.delete_backup("b1") is True
        assert s.get_backup("b1") is None

    def test_delete_missing(self):
        s = BackupStore()
        assert s.delete_backup("missing") is False

    def test_get_latest(self):
        s = BackupStore()
        s.add_backup([], backup_id="b1")
        latest = s.get_latest()
        assert latest.backup_id == "b1"

    def test_get_latest_empty(self):
        s = BackupStore()
        assert s.get_latest() is None

    def test_max_backups_eviction(self):
        s = BackupStore(max_backups=2)
        s.add_backup([], backup_id="b1")
        time.sleep(0.01)
        s.add_backup([], backup_id="b2")
        time.sleep(0.01)
        s.add_backup([], backup_id="b3")
        assert len(s.list_backups()) == 2

    def test_export_import_roundtrip(self):
        s = BackupStore()
        s.add_backup([{"id": "1", "title": "A"}], backup_id="b1")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            s.export_to_file("b1", f.name)
        s2 = BackupStore()
        entry = s2.import_from_file(f.name)
        assert entry.backup_id == "b1"
        assert entry.data[0]["title"] == "A"

    def test_export_missing_raises(self):
        s = BackupStore()
        try:
            s.export_to_file("missing", "/tmp/nonexistent.json")
            assert False, "Should have raised"
        except ValueError:
            pass
