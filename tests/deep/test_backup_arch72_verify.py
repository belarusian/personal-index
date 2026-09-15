"""ARCH-72 verification: backup.restore_backup overwrite guard.

The implementer chose Option 1 (default-safe): ``restore_backup`` gained an
``overwrite: bool = False`` parameter. By default it refuses to overwrite any
file in ``target_dir`` whose path collides with an archive member, raising a
clean ``ValueError`` naming the colliding path(s) BEFORE writing anything
(``_check_no_collision`` mirrors the corrupt-archive pre-write guard). With
``overwrite=True`` it proceeds with ``extractall`` as before.

These tests pin the acceptance criteria (AC1-AC5) plus adversarial guard
inputs implied by the contract. They run against the real ``restore_backup``
entry point.
"""

from __future__ import annotations

import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from personal_index.backup import BackupManager


def _make_source(root: Path, files: dict[str, str]) -> str:
    """Create a source dir with the given {relpath: content} mapping."""
    src = root / "src"
    for rel, content in files.items():
        p = src / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return str(src)


def _backup(root: Path, files: dict[str, str]) -> tuple[BackupManager, str]:
    src = _make_source(root, files)
    mgr = BackupManager(backup_dir=str(root / "backups"))
    manifest = mgr.create_backup(src)
    return mgr, manifest.backup_id


# ---------------------------------------------------------------------------
# AC1: default restore refuses to clobber a colliding file, byte-identical
# ---------------------------------------------------------------------------


class TestRefusesToOverwrite:
    def test_default_refuses_and_preserves_byte_identical(self, tmp_path) -> None:
        """AC1: colliding pre-existing file -> ValueError, file unchanged."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "content 1"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "file1.txt").write_text("PRE-EXISTING")

        with pytest.raises(ValueError, match="Restore would overwrite"):
            mgr.restore_backup(bid, str(target))

        assert (target / "file1.txt").read_text() == "PRE-EXISTING"

    def test_error_names_the_colliding_path(self, tmp_path) -> None:
        """AC1: the ValueError message names the colliding member path."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "content 1"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "file1.txt").write_text("PRE")

        with pytest.raises(ValueError, match="file1\\.txt"):
            mgr.restore_backup(bid, str(target))

    def test_multiple_collisions_all_named(self, tmp_path) -> None:
        """Adversarial: two colliding members -> both named in one error."""
        mgr, bid = _backup(
            tmp_path, {"a.txt": "A", "b.txt": "B", "c.txt": "C"}
        )
        target = tmp_path / "restored"
        target.mkdir()
        (target / "a.txt").write_text("PRE-A")
        (target / "c.txt").write_text("PRE-C")

        with pytest.raises(ValueError, match="Restore would overwrite") as exc:
            mgr.restore_backup(bid, str(target))

        msg = str(exc.value)
        assert "a.txt" in msg
        assert "c.txt" in msg
        # Non-colliding member must NOT be named.
        assert "b.txt" not in msg
        # Both pre-existing files preserved byte-identical.
        assert (target / "a.txt").read_text() == "PRE-A"
        assert (target / "c.txt").read_text() == "PRE-C"
        # No partial write: the non-colliding member was never extracted.
        assert not (target / "b.txt").exists()

    def test_nested_subdir_collision(self, tmp_path) -> None:
        """Adversarial: collision on a nested member path (subdir/file3.txt)."""
        mgr, bid = _backup(
            tmp_path, {"file1.txt": "1", "subdir/file3.txt": "3"}
        )
        target = tmp_path / "restored"
        (target / "subdir").mkdir(parents=True)
        (target / "subdir" / "file3.txt").write_text("PRE-3")

        with pytest.raises(ValueError, match="subdir/file3\\.txt"):
            mgr.restore_backup(bid, str(target))

        assert (target / "subdir" / "file3.txt").read_text() == "PRE-3"

    def test_unicode_filename_collision(self, tmp_path) -> None:
        """Adversarial: unicode member path collides and is named."""
        mgr, bid = _backup(tmp_path, {"файл_日本語.txt": "unicode content"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "файл_日本語.txt").write_text("PRE-UNICODE")

        with pytest.raises(ValueError, match="Restore would overwrite"):
            mgr.restore_backup(bid, str(target))

        assert (target / "файл_日本語.txt").read_text() == "PRE-UNICODE"

    def test_guard_fires_before_any_write(self, tmp_path) -> None:
        """Adversarial: on refusal, NO member is extracted (pre-write guard)."""
        mgr, bid = _backup(
            tmp_path, {"keep.txt": "K", "collide.txt": "C"}
        )
        target = tmp_path / "restored"
        target.mkdir()
        (target / "collide.txt").write_text("PRE")

        with pytest.raises(ValueError):
            mgr.restore_backup(bid, str(target))

        # The non-colliding member must NOT have been written either.
        assert not (target / "keep.txt").exists()
        assert (target / "collide.txt").read_text() == "PRE"


# ---------------------------------------------------------------------------
# AC2: overwrite=True replaces the colliding file
# ---------------------------------------------------------------------------


class TestOverwriteOptIn:
    def test_overwrite_replaces_colliding_file(self, tmp_path) -> None:
        """AC2: overwrite=True replaces the colliding file with archive content."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "content 1"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "file1.txt").write_text("PRE-EXISTING")

        result = mgr.restore_backup(bid, str(target), overwrite=True)
        assert result["files_restored"] == 1
        assert (target / "file1.txt").read_text() == "content 1"

    def test_overwrite_multiple_all_replaced(self, tmp_path) -> None:
        """Adversarial: overwrite=True replaces every colliding member."""
        mgr, bid = _backup(
            tmp_path, {"a.txt": "A-new", "b.txt": "B-new"}
        )
        target = tmp_path / "restored"
        target.mkdir()
        (target / "a.txt").write_text("A-old")
        (target / "b.txt").write_text("B-old")

        result = mgr.restore_backup(bid, str(target), overwrite=True)
        assert result["files_restored"] == 2
        assert (target / "a.txt").read_text() == "A-new"
        assert (target / "b.txt").read_text() == "B-new"

    def test_overwrite_idempotent_double_restore(self, tmp_path) -> None:
        """Adversarial: two overwrite=True restores converge to archive content."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "content 1"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "file1.txt").write_text("PRE")

        first = mgr.restore_backup(bid, str(target), overwrite=True)
        second = mgr.restore_backup(bid, str(target), overwrite=True)
        assert first["files_restored"] == second["files_restored"] == 1
        assert (target / "file1.txt").read_text() == "content 1"


# ---------------------------------------------------------------------------
# AC3: empty / nonexistent target succeeds exactly as today
# ---------------------------------------------------------------------------


class TestCleanPath:
    def test_into_nonexistent_target_succeeds(self, tmp_path) -> None:
        """AC3: restore into a fresh (nonexistent) target succeeds."""
        mgr, bid = _backup(
            tmp_path, {"file1.txt": "1", "subdir/file3.txt": "3"}
        )
        target = str(tmp_path / "brand_new")
        result = mgr.restore_backup(bid, target)
        assert result["files_restored"] == 2
        assert (Path(target) / "file1.txt").read_text() == "1"
        assert (Path(target) / "subdir" / "file3.txt").read_text() == "3"

    def test_into_empty_existing_target_succeeds(self, tmp_path) -> None:
        """AC3: restore into an existing-but-empty target succeeds."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "1"})
        target = tmp_path / "empty"
        target.mkdir()
        result = mgr.restore_backup(bid, str(target))
        assert result["files_restored"] == 1
        assert (target / "file1.txt").read_text() == "1"

    def test_non_colliding_extra_file_survives(self, tmp_path) -> None:
        """Adversarial: a pre-existing file NOT in the archive is untouched."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "1"})
        target = tmp_path / "restored"
        target.mkdir()
        (target / "unrelated.txt").write_text("KEEP-ME")

        result = mgr.restore_backup(bid, str(target))
        assert result["files_restored"] == 1
        assert (target / "file1.txt").read_text() == "1"
        assert (target / "unrelated.txt").read_text() == "KEEP-ME"


# ---------------------------------------------------------------------------
# AC4: corrupt / truncated archive still raises ValueError before any write
# ---------------------------------------------------------------------------


class TestCorruptArchiveGuard:
    def test_corrupt_archive_raises_before_write(self, tmp_path) -> None:
        """AC4: corrupt archive -> clean ValueError, no partial write."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "1"})
        archive = Path(mgr._backup_dir) / f"backup_{bid}.tar.gz"
        archive.write_bytes(b"NOT A VALID TAR ARCHIVE AT ALL")

        target = tmp_path / "out"
        with pytest.raises(ValueError, match="Corrupt or unreadable archive"):
            mgr.restore_backup(bid, str(target))

        # No member was extracted.
        assert not (target / "file1.txt").exists()

    def test_corrupt_archive_with_collision_still_corrupt_error(self, tmp_path) -> None:
        """Adversarial: corrupt archive + collision -> corrupt error (not clobber)."""
        mgr, bid = _backup(tmp_path, {"file1.txt": "1"})
        archive = Path(mgr._backup_dir) / f"backup_{bid}.tar.gz"
        archive.write_bytes(b"GARBAGE")

        target = tmp_path / "out"
        target.mkdir()
        (target / "file1.txt").write_text("PRE")

        with pytest.raises(ValueError, match="Corrupt or unreadable archive"):
            mgr.restore_backup(bid, str(target))

        # Pre-existing file must survive (guard raised before any write).
        assert (target / "file1.txt").read_text() == "PRE"


# ---------------------------------------------------------------------------
# Soundness: the guard is only sound if the archive holds file members only
# ---------------------------------------------------------------------------


class TestArchiveMemberSoundness:
    def test_archive_contains_only_file_members(self, tmp_path) -> None:
        """The collision guard compares member paths to target; it is sound
        only if the archive holds file members (no bare directory entries that
        would collide with an existing target subdir)."""
        mgr, bid = _backup(
            tmp_path, {"file1.txt": "1", "subdir/file3.txt": "3"}
        )
        archive = Path(mgr._backup_dir) / f"backup_{bid}.tar.gz"
        with tarfile.open(str(archive), "r:gz") as tar:
            names = tar.getnames()
        # Every member must be a file path, never a bare directory entry.
        assert "subdir" not in names
        assert set(names) == {"file1.txt", "subdir/file3.txt"}


# ---------------------------------------------------------------------------
# End-to-end CLI smoke (installed console script)
# ---------------------------------------------------------------------------


class TestEndToEndCli:
    def test_cli_version_runs(self) -> None:
        """End-to-end: the installed CLI responds to --version."""
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "--version"],
            capture_output=True,
            text=True,
        )
        assert proc.returncode == 0
        assert proc.stdout.strip() != ""
