"""Tests for backup and restore system."""

from __future__ import annotations

import os

import pytest

from personal_index.backup import (
    BackupManager,
    BackupManifest,
)


class TestBackupManifest:
    """Tests for BackupManifest dataclass."""

    def test_create_manifest(self):
        m = BackupManifest(source_dir="/tmp/test")
        assert m.source_dir == "/tmp/test"
        assert m.backup_id
        assert m.created_at

    def test_to_dict(self):
        m = BackupManifest(
            backup_id="test_001",
            source_dir="/tmp/test",
            files=["a.txt", "b.txt"],
            total_size=1000,
        )
        d = m.to_dict()
        assert d["backup_id"] == "test_001"
        assert d["files"] == ["a.txt", "b.txt"]
        assert d["total_size"] == 1000

    def test_from_dict(self):
        data = {
            "backup_id": "test_001",
            "created_at": "2024-01-01T00:00:00",
            "source_dir": "/tmp/test",
            "files": ["a.txt"],
            "total_size": 500,
            "file_count": 1,
            "metadata": {},
        }
        m = BackupManifest.from_dict(data)
        assert m.backup_id == "test_001"
        assert m.files == ["a.txt"]

    def test_defaults(self):
        m = BackupManifest()
        assert m.files == []
        assert m.total_size == 0
        assert m.file_count == 0


class TestBackupManager:
    """Tests for BackupManager class."""

    def setup_method(self):
        self.tmp_dir = None

    def _create_test_dir(self, tmp_path):
        """Create a test directory with files."""
        test_dir = tmp_path / "test_source"
        test_dir.mkdir()
        (test_dir / "file1.txt").write_text("content 1")
        (test_dir / "file2.txt").write_text("content 2")
        subdir = test_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content 3")
        return str(test_dir)

    def test_create_backup(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source)
        assert manifest.file_count == 3
        assert manifest.total_size > 0
        assert manifest.backup_id

    def test_create_backup_no_compress(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source, compress=False)
        assert manifest.metadata["compressed"] is False

    def test_create_backup_nonexistent_source(self):
        manager = BackupManager()
        with pytest.raises(FileNotFoundError):
            manager.create_backup("/tmp/nonexistent_dir_xyz")

    def test_list_backups_empty(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)
        assert manager.list_backups() == []

    def test_list_backups(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manager.create_backup(source)
        manager.create_backup(source)

        backups = manager.list_backups()
        assert len(backups) == 2

    def test_restore_backup(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source)
        target = str(tmp_path / "restored")

        result = manager.restore_backup(manifest.backup_id, target)
        assert result["files_restored"] == 3
        assert os.path.exists(os.path.join(target, "file1.txt"))
        assert open(os.path.join(target, "file1.txt")).read() == "content 1"

    def test_restore_nonexistent_backup(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)
        with pytest.raises(FileNotFoundError):
            manager.restore_backup("nonexistent_id", str(tmp_path / "target"))

    def test_delete_backup(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source)
        assert manager.delete_backup(manifest.backup_id) is True
        assert manager.list_backups() == []

    def test_delete_nonexistent_backup(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)
        assert manager.delete_backup("nonexistent") is False

    def test_get_backup_info(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source)
        info = manager.get_backup_info(manifest.backup_id)
        assert info is not None
        assert info.backup_id == manifest.backup_id

    def test_get_backup_info_nonexistent(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)
        assert manager.get_backup_info("nonexistent") is None

    def test_get_total_backup_size(self, tmp_path):
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)
        assert manager.get_total_backup_size() == 0

    def test_get_total_backup_size_after_backup(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manager.create_backup(source)
        assert manager.get_total_backup_size() > 0

    def test_cleanup_old_backups(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        for _ in range(5):
            manager.create_backup(source)

        deleted = manager.cleanup_old_backups(keep=2)
        assert len(deleted) == 3
        assert len(manager.list_backups()) == 2

    def test_cleanup_nothing_to_delete(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manager.create_backup(source)
        deleted = manager.cleanup_old_backups(keep=5)
        assert deleted == []

    def test_create_backup_with_exclude(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source, exclude_patterns=["*.txt"])
        assert manifest.file_count == 0

    def test_create_backup_with_include(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source, include_patterns=["file1.txt"])
        assert manifest.file_count == 1

    def test_backup_id_unique(self, tmp_path):
        """Backup IDs should be unique even when created in the same second."""
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        m1 = manager.create_backup(source)
        m2 = manager.create_backup(source)
        assert m1.backup_id != m2.backup_id

    def test_backup_id_format(self, tmp_path):
        source = self._create_test_dir(tmp_path)
        backup_dir = str(tmp_path / "backups")
        manager = BackupManager(backup_dir=backup_dir)

        manifest = manager.create_backup(source)
        # ID should contain timestamp and UUID parts
        assert "_" in manifest.backup_id
        assert len(manifest.backup_id) > 10


class TestBackupTarFilter:
    """Tests for tar.extractall() filter argument (TICKET-47)."""

    def test_restore_uses_filter_argument(self):
        """tar.extractall should use filter='data' to prevent path traversal."""
        import os
        import tempfile
        import warnings

        from personal_index.backup import BackupManager

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a source directory with a file
            source_dir = os.path.join(tmpdir, "source")
            os.makedirs(source_dir)
            test_file = os.path.join(source_dir, "test.txt")
            with open(test_file, "w") as f:
                f.write("hello world")

            # Create backup
            backup_dir = os.path.join(tmpdir, "backups")
            manager = BackupManager(backup_dir=backup_dir)
            manifest = manager.create_backup(source_dir)

            # Restore with no deprecation warnings
            restore_dir = os.path.join(tmpdir, "restored")
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                result = manager.restore_backup(manifest.backup_id, restore_dir)
                deprecation_warnings = [x for x in w if issubclass(x.category, DeprecationWarning)]
                assert len(deprecation_warnings) == 0, f"Expected no deprecation warnings, got: {[str(x.message) for x in deprecation_warnings]}"

            # Verify restoration worked
            assert result["files_restored"] == 1
            restored_file = os.path.join(restore_dir, "test.txt")
            assert os.path.exists(restored_file)
            with open(restored_file) as f:
                assert f.read() == "hello world"
