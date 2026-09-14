# ARCH-72 — backup: `restore_backup` silently overwrites pre-existing files in `target_dir` with no guard, so restoring into a populated directory destroys caller-owned data

Status: IMPLEMENTED #1425@3639453
Component: `personal_index/backup.py` — `BackupManager.restore_backup` (lines 160-196); the clobber half `BackupManager._extract_archive` (lines 212-231, `tar.extractall` at line 226); the docstrings at lines 161 and 213
Umbrella: ARCH-2 (#983)
Issue: #1407
Docs: `docs/backup.md` (Contract Hole 1)

## Problem
`restore_backup(backup_id, target_dir)` (line 160) ends with:

    target = Path(target_dir)
    target.mkdir(parents=True, exist_ok=True)          # line 189
    restored = self._extract_archive(archive_path, mode, target)   # line 190

and `_extract_archive` (line 212) does:

    with tarfile.open(str(archive_path), mode) as tar:
        count = len(tar.getnames())
        tar.extractall(path=str(target), filter="data")   # line 226

`tarfile.extractall` **overwrites any file in `target` whose path collides
with an archive member, with no guard, no conflict detection, and no signal.**
If the caller points `target_dir` at a directory that already holds data — a
live data dir, a previously-restored backup, or any existing tree — the
colliding files are **silently clobbered**: the pre-existing content is
destroyed and the returned dict reports only `files_restored` (the count of
archive members), never that existing files were overwritten.

This is the **destructive user-facing** half of the module. It is distinct
from the corrupt-archive path, which is already guarded: `len(tar.getnames())`
runs **before** `extractall`, so a corrupt/truncated archive raises `ValueError`
**before** any byte is written to `target` (pinned by
`tests/test_backup.py::test_restore_corrupt_archive_raises_value_error` and
`test_restore_truncated_archive_raises_value_error`). The clobber happens on
the **happy path** with a valid archive and a valid manifest.

The `restore_backup` docstring (`"Restore a backup to the target directory."`)
and the `_extract_archive` docstring both omit the overwrite behavior entirely,
so a caller reading the contract has no reason to expect data loss. This is the
same "advertised safety not actually provided" class as ARCH-39/40/41/42/44/46
(silent overwrite / silent data loss on a write path), and it is the single
most important hole in this module because it destroys **caller-owned** data
rather than the module's own persisted state.

## Public contract (target)
`restore_backup` must never silently destroy pre-existing files in
`target_dir`. The exact target behavior (pick ONE and pin it):

1. **Default-safe (recommended):** add an `overwrite: bool = False` parameter
   to `restore_backup`. When `overwrite` is `False` (the default) and any
   archive member's destination path already exists in `target_dir`, raise a
   clean `FileError`-style `ValueError` (e.g.
   `"Restore would overwrite existing file(s) in {target_dir}: {paths}; pass
   overwrite=True to replace") **before** writing anything (check the
   `tar.getnames()` member paths against `target` first, mirroring the
   corrupt-archive pre-write guard). When `overwrite` is `True`, proceed with
   `extractall` as today.
2. Reword the `restore_backup` docstring (line 161) to state the exact
   overwrite contract: by default it refuses to overwrite existing files in
   `target_dir` (raising `ValueError` naming the colliding paths) and only
   overwrites when `overwrite=True`; and reword the `_extract_archive`
   docstring (line 213) to note that `extractall` overwrites colliding files
   and that the overwrite decision is made by the caller of `restore_backup`.
3. Keep the corrupt-archive `ValueError` guard unchanged (it already fires
   before any write).

## Acceptance criteria
- `restore_backup(id, target)` where `target` already contains a file whose
  path collides with an archive member **raises `ValueError`** (naming the
  colliding path) and leaves the pre-existing file **byte-identical** (not
  truncated, not replaced).
- `restore_backup(id, target, overwrite=True)` into the same populated
  `target` **succeeds** and the colliding file is replaced by the archive
  member's content (the current behavior, now opt-in).
- `restore_backup(id, target)` into an **empty/nonexistent** `target`
  succeeds exactly as today (no new failure mode on the clean path).
- The corrupt-archive and truncated-archive paths still raise `ValueError`
  before writing anything (existing tests unchanged and green).
- The `restore_backup` and `_extract_archive` docstrings state the overwrite
  contract (no blanket "restore to the target directory" that hides the
  clobber).

## Pinning tests to add (in `tests/test_backup.py`)
- `test_restore_backup_refuses_to_overwrite_existing_file(tmp_path)`: create a
  backup of a source dir containing `file1.txt`; pre-create
  `target/file1.txt` with distinct content; call
  `restore_backup(id, target)` (default `overwrite=False`); assert it raises
  `ValueError` AND that `target/file1.txt` still holds the **original**
  content (pins both the guard path and the no-clobber guarantee).
- `test_restore_backup_overwrites_when_flag_set(tmp_path)`: same setup, call
  `restore_backup(id, target, overwrite=True)`; assert it returns
  `files_restored == <count>` and `target/file1.txt` now holds the **archive**
  content (pins the opt-in path).
- `test_restore_backup_into_empty_target_unchanged(tmp_path)`: restore into a
  fresh `target`; assert success and correct content (pins that the guard does
  not break the clean path).

## Docs
`docs/backup.md` (new, this PR) — Public API + Contract Hole 1 + Secondary
notes. The docstring reword in the fix PR must keep `docs/backup.md`
Contract Hole 1 accurate (the "silently overwrites" claim becomes
"refuses to overwrite by default; overwrites only when `overwrite=True`").
