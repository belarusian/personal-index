"""Adversarial deep tests for personal_index.backup module.

Targets: BackupManifest edge cases, BackupManager operations with corrupt/missing
data, restore overwrite semantics, cleanup retention, file collection filtering.
"""

import json
import os
import tarfile
import tempfile
import time
from pathlib import Path

import pytest

from personal_index.backup import BackupManifest, BackupManager


@pytest.fixture
def tmp_backup_env():
    """Create isolated source and backup directories."""
    with tempfile.TemporaryDirectory() as src, tempfile.TemporaryDirectory() as bak:
        yield src, bak


@pytest.fixture
def populated_source(tmp_backup_env):
    """Source dir with files to back up."""
    src, bak = tmp_backup_env
    (Path(src) / "file1.txt").write_text("hello world")
    (Path(src) / "file2.txt").write_text("second file")
    subdir = Path(src) / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("in subdir")
    # Hidden file - code filters hidden dirs but not hidden files
    (Path(src) / ".hidden").write_text("hidden")
    return src, bak


class TestBackupManifestEdgeCases:
    """BackupManifest dataclass edge cases."""

    def test_empty_fields_get_defaults(self):
        m = BackupManifest()
        assert m.backup_id != ""
        assert m.created_at != ""
        assert m.files == []
        assert m.file_count == 0
        assert m.total_size == 0

    def test_backup_id_format(self):
        m = BackupManifest()
        # Format: YYYYMMDD_HHMMSS_XXXXXX (6 hex chars)
        parts = m.backup_id.split("_")
        assert len(parts) == 3
        assert len(parts[0]) == 8  # YYYYMMDD
        assert len(parts[1]) == 6  # HHMMSS
        assert len(parts[2]) == 6  # short uuid

    def test_to_dict_from_dict_roundtrip(self):
        original = BackupManifest(
            backup_id="test_id",
            source_dir="/tmp/src",
            files=["a.txt", "b.txt"],
            file_count=2,
            total_size=100,
            metadata={"key": "value"},
        )
        data = original.to_dict()
        restored = BackupManifest.from_dict(data)
        assert restored.backup_id == "test_id"
        assert restored.source_dir == "/tmp/src"
        assert restored.files == ["a.txt", "b.txt"]
        assert restored.file_count == 2
        assert restored.total_size == 100
        assert restored.metadata == {"key": "value"}

    def test_from_dict_empty_dict_uses_defaults(self):
        """from_dict with empty dict should use field defaults."""
        m = BackupManifest.from_dict({})
        assert m.backup_id != ""
        assert m.source_dir == ""
        assert m.files == []

    def test_from_dict_non_dict_raises(self):
        with pytest.raises(TypeError):
            BackupManifest.from_dict("not a dict")


class TestCreateBackupEdgeCases:
    """create_backup with edge cases."""

    def test_nonexistent_source(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        with pytest.raises(FileNotFoundError):
            mgr.create_backup("/nonexistent/path")

    def test_empty_source_dir(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        assert manifest.file_count == 0
        assert manifest.total_size == 0

    def test_compressed_vs_uncompressed(self, populated_source):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)

        # Compressed
        manifest_gz = mgr.create_backup(src, compress=True)
        assert manifest_gz.metadata.get("compressed") is True
        archive_gz = Path(manifest_gz.metadata["archive_path"])
        assert archive_gz.suffix == ".gz"

        # Uncompressed
        manifest_tar = mgr.create_backup(src, compress=False)
        assert manifest_tar.metadata.get("compressed") is False
        archive_tar = Path(manifest_tar.metadata["archive_path"])
        assert archive_tar.suffix == ".tar"

    def test_include_patterns(self, populated_source):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src, include_patterns=["*.txt"])
        # Should include all .txt files
        assert manifest.file_count >= 3

    def test_exclude_patterns(self, populated_source):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src, exclude_patterns=["file1.txt"])
        assert "file1.txt" not in manifest.files

    def test_hidden_files_included_by_default(self, populated_source):
        """Code filters hidden dirs but not hidden files."""
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        assert ".hidden" in manifest.files

    def test_hidden_dirs_excluded_by_default(self, populated_source):
        src, bak = populated_source
        hidden_dir = Path(src) / ".hidden_dir"
        hidden_dir.mkdir()
        (hidden_dir / "file.txt").write_text("in hidden dir")
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        assert not any(".hidden_dir" in f for f in manifest.files)

    def test_pycache_excluded_by_default(self, populated_source):
        src, bak = populated_source
        pycache = Path(src) / "__pycache__"
        pycache.mkdir()
        (pycache / "module.pyc").write_bytes(b"fake bytecode")
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        assert not any("__pycache__" in f for f in manifest.files)


class TestListBackupsEdgeCases:
    """list_backups with corrupt/missing data."""

    def test_empty_backup_dir(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        assert mgr.list_backups() == []

    def test_missing_backup_dir(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir="/nonexistent/backup/dir")
        assert mgr.list_backups() == []

    def test_corrupt_json_manifest(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        # Create a corrupt manifest
        corrupt = Path(bak) / "backup_corrupt.json"
        corrupt.write_text("not valid json")
        # Should not raise, should skip corrupt file
        backups = mgr.list_backups()
        assert backups == []

    def test_non_dict_json_manifest(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        non_dict = Path(bak) / "backup_nondict.json"
        non_dict.write_text('["not", "a", "dict"]')
        backups = mgr.list_backups()
        assert backups == []

    def test_sorted_oldest_first(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        # Create backups with known timestamps
        for i in range(3):
            manifest = mgr.create_backup(src)
            # Write a manifest with a specific timestamp for ordering
            manifest_path = Path(bak) / f"backup_{manifest.backup_id}.json"
            data = manifest.to_dict()
            data["created_at"] = f"2026-01-0{i+1}T00:00:00Z"
            manifest_path.write_text(json.dumps(data))
        backups = mgr.list_backups()
        # Should be sorted by filename (which includes timestamp)
        assert len(backups) == 3


class TestRestoreBackupEdgeCases:
    """restore_backup with various failure modes."""

    def test_nonexistent_backup_id(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        with pytest.raises(FileNotFoundError):
            mgr.restore_backup("nonexistent_id", "/tmp/restore_target")

    def test_corrupt_archive(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        # Create a backup, then corrupt the archive
        manifest = mgr.create_backup(src)
        archive_path = Path(manifest.metadata["archive_path"])
        archive_path.write_bytes(b"corrupt data")
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            mgr.restore_backup(manifest.backup_id, "/tmp/restore_target")

    def test_truncated_gz_archive(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src, compress=True)
        archive_path = Path(manifest.metadata["archive_path"])
        # Truncate the gz file
        with open(archive_path, "r+b") as f:
            f.truncate(10)
        with pytest.raises(ValueError, match="Corrupt or unreadable"):
            mgr.restore_backup(manifest.backup_id, "/tmp/restore_target")

    def test_overwrite_collision(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        # Restore to a dir with existing files
        target = Path(bak) / "restore_target"
        target.mkdir()
        (target / "file1.txt").write_text("existing content")
        with pytest.raises(ValueError, match="overwrite"):
            mgr.restore_backup(manifest.backup_id, str(target), overwrite=False)

    def test_overwrite_true_replaces(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        target = Path(bak) / "restore_target"
        target.mkdir()
        (target / "file1.txt").write_text("existing content")
        result = mgr.restore_backup(manifest.backup_id, str(target), overwrite=True)
        assert result["files_restored"] >= 3
        # file1.txt should now have backed-up content
        assert (target / "file1.txt").read_text() == "hello world"

    def test_corrupt_manifest_json(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        # Create a corrupt manifest
        corrupt = Path(bak) / "backup_corrupt_id.json"
        corrupt.write_text("not json")
        with pytest.raises(ValueError):
            mgr.restore_backup("corrupt_id", "/tmp/restore_target")

    def test_manifest_not_dict(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        non_dict = Path(bak) / "backup_nondict_id.json"
        non_dict.write_text('["array"]')
        with pytest.raises(ValueError):
            mgr.restore_backup("nondict_id", "/tmp/restore_target")


class TestCleanupOldBackups:
    """cleanup_old_backups retention logic."""

    def test_keep_zero_deletes_nothing(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        for i in range(3):
            mgr.create_backup(src)
        deleted = mgr.cleanup_old_backups(keep=0)
        assert deleted == []
        assert len(mgr.list_backups()) == 3

    def test_keep_negative_deletes_nothing(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        for i in range(3):
            mgr.create_backup(src)
        deleted = mgr.cleanup_old_backups(keep=-1)
        assert deleted == []
        assert len(mgr.list_backups()) == 3

    def test_keep_more_than_count_deletes_nothing(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        for i in range(3):
            mgr.create_backup(src)
        deleted = mgr.cleanup_old_backups(keep=10)
        assert deleted == []
        assert len(mgr.list_backups()) == 3

    def test_keep_fewer_than_count_deletes_oldest(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifests = []
        for i in range(5):
            manifests.append(mgr.create_backup(src))
            time.sleep(0.05)  # Ensure distinct timestamps
        deleted = mgr.cleanup_old_backups(keep=2)
        assert len(deleted) == 3
        assert len(mgr.list_backups()) == 2


class TestGetBackupInfo:
    """get_backup_info edge cases."""

    def test_nonexistent_id(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        assert mgr.get_backup_info("nonexistent") is None

    def test_corrupt_manifest(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        corrupt = Path(bak) / "backup_corrupt.json"
        corrupt.write_text("not json")
        assert mgr.get_backup_info("corrupt") is None

    def test_valid_manifest(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        info = mgr.get_backup_info(manifest.backup_id)
        assert info is not None
        assert info.backup_id == manifest.backup_id


class TestGetTotalBackupSize:
    """get_total_backup_size edge cases."""

    def test_no_archives(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        assert mgr.get_total_backup_size() == 0

    def test_missing_dir(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir="/nonexistent")
        assert mgr.get_total_backup_size() == 0

    def test_counts_only_archives(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        size = mgr.get_total_backup_size()
        # Should be > 0 and match the archive size
        archive_path = Path(manifest.metadata["archive_path"])
        assert size == archive_path.stat().st_size


class TestDeleteBackup:
    """delete_backup edge cases."""

    def test_nonexistent_id(self, tmp_backup_env):
        src, bak = tmp_backup_env
        mgr = BackupManager(backup_dir=bak)
        assert mgr.delete_backup("nonexistent") is False

    def test_existing_id(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        assert mgr.delete_backup(manifest.backup_id) is True
        assert mgr.get_backup_info(manifest.backup_id) is None


class TestRoundTrip:
    """End-to-end backup and restore round-trip."""

    def test_backup_restore_content_integrity(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest = mgr.create_backup(src)
        target = Path(bak) / "restored"
        result = mgr.restore_backup(manifest.backup_id, str(target))
        # Verify all files restored
        assert (target / "file1.txt").read_text() == "hello world"
        assert (target / "file2.txt").read_text() == "second file"
        assert (target / "subdir" / "file3.txt").read_text() == "in subdir"

    def test_multiple_backups_independent(self, populated_source, tmp_backup_env):
        src, bak = populated_source
        mgr = BackupManager(backup_dir=bak)
        manifest1 = mgr.create_backup(src)
        # Modify source
        (Path(src) / "file1.txt").write_text("modified")
        manifest2 = mgr.create_backup(src)
        # Restore first backup
        target1 = Path(bak) / "restore1"
        mgr.restore_backup(manifest1.backup_id, str(target1))
        assert (target1 / "file1.txt").read_text() == "hello world"
        # Restore second backup
        target2 = Path(bak) / "restore2"
        mgr.restore_backup(manifest2.backup_id, str(target2))
        assert (target2 / "file1.txt").read_text() == "modified"
