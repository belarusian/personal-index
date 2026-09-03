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


class TestBackupStoreNonDictGuard:
    def _write(self, tmp_path, value, name="b.json"):
        p = tmp_path / name
        p.write_text(value)
        return str(p)

    def test_import_null_raises(self, tmp_path):
        s = BackupStore()
        try:
            s.import_from_file(self._write(tmp_path, "null"))
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_import_number_raises(self, tmp_path):
        s = BackupStore()
        try:
            s.import_from_file(self._write(tmp_path, "42"))
            assert False, "Should have raised"
        except ValueError:
            pass

    def test_import_list_raises(self, tmp_path):
        s = BackupStore()
        try:
            s.import_from_file(self._write(tmp_path, '[{"backup_id": "x"}]'))
            assert False, "Should have raised"
        except ValueError:
            pass


    def test_import_corrupt_json_raises_valueerror(self, tmp_path):
        """Corrupt (truncated) JSON file raises ValueError, not JSONDecodeError."""
        import json as _json
        s = BackupStore()
        p = self._write(tmp_path, "{", "corrupt.json")
        try:
            s.import_from_file(p)
            assert False, "Should have raised"
        except _json.JSONDecodeError:
            assert False, "Should raise ValueError, not JSONDecodeError"
        except ValueError as e:
            assert "not valid JSON" in str(e)

    def test_import_missing_key_raises_valueerror(self, tmp_path):
        """Valid JSON dict missing required key raises ValueError, not KeyError."""
        s = BackupStore()
        p = self._write(tmp_path, '{"backup_id": "x"}', "missing.json")
        try:
            s.import_from_file(p)
            assert False, "Should have raised"
        except KeyError:
            assert False, "Should raise ValueError, not KeyError"
        except ValueError as e:
            assert "missing required key" in str(e)

    def test_import_valid_dict_still_works(self, tmp_path):
        s = BackupStore()
        s.add_backup([{"id": "1", "title": "A"}], backup_id="b1")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            s.export_to_file("b1", f.name)
        s2 = BackupStore()
        entry = s2.import_from_file(f.name)
        assert entry.backup_id == "b1"
        assert entry.data[0]["title"] == "A"

    def test_valid_after_invalid_not_suppressed(self, tmp_path):
        s = BackupStore()
        try:
            s.import_from_file(self._write(tmp_path, "null", "bad.json"))
            assert False, "Should have raised"
        except ValueError:
            pass
        s.add_backup([{"id": "1", "title": "A"}], backup_id="b1")
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            s.export_to_file("b1", f.name)
        entry = s.import_from_file(f.name)
        assert entry.backup_id == "b1"
        assert entry.data[0]["title"] == "A"
