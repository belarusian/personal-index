# TICKET-300: backup.py BackupManager._create_archive unguarded tarfile.open (write failure)

- Status: RESOLVED (merged to main f0a4189, gh #432 closed)
- Issue: #432
- Module: personal_index/backup.py
- Function: BackupManager._create_archive (line 58)

## Symptom
`create_backup` establishes a clean, documented error contract for the failures it can hit: `FileNotFoundError` for a missing source directory. But the archive-creation step is unguarded: `_create_archive` calls `tarfile.open(str(archive_path), mode)` (line 58) with no try/except, then runs `tar.add(...)` in a loop. A write failure (disk full, permission denied, non-writable path, or the archive path being a directory) raises a raw `OSError` subclass (`PermissionError`, `IsADirectoryError`, `OSError` ENOSPC) — or `tarfile.TarError` from the tar layer — straight out of `create_backup`, violating the module's clean-error style. This is the untested-error-path class (c), not the closed corrupt-JSON-guard class and not the already-done `_extract_archive` corrupt-tar guard (TICKET-299).

## Evidence
- Line 58: `with tarfile.open(str(archive_path), mode) as tar:` in `_create_archive` — no try/except; the `tar.add` loop (lines 59-60) is likewise unguarded.
- Line 84: `create_backup` already raises `FileNotFoundError` for a missing source — the module's documented style for "cannot proceed" conditions.
- Verified by running the code: pointing the archive path at a directory makes `tarfile.open(path, "w")` raise `IsADirectoryError` (an `OSError` subclass); a non-writable parent dir makes it raise `PermissionError` (an `OSError` subclass). Both leak raw out of `create_backup`.

## Minimal additive fix
Wrap the `tarfile.open`/`tar.add` body in `_create_archive` in `try/except (OSError, tarfile.TarError) as exc: raise RuntimeError(f"Failed to create archive {archive_path}: {exc}") from exc`. A write failure raises an `OSError` subclass (PermissionError / IsADirectoryError / ENOSPC) and the tar layer can raise `tarfile.TarError`; both are translated to a clean `RuntimeError` (the module has no existing I/O-failure error type — `FileNotFoundError` is for *missing* files, `ValueError` for *invalid data* — so `RuntimeError` is the standard clean choice for "the write could not be performed"; do NOT invent a new contract and do NOT degrade to a silent empty archive). Add 2 regression tests in tests/test_backup.py: (a) a non-writable archive path (archive path is a directory) asserts a clean `RuntimeError` (NOT a raw `OSError` leak), with a precondition that `tarfile.open` on that path raises `OSError`; (b) a permission-denied archive path (non-writable parent dir) asserts a clean `RuntimeError`, with a precondition that `tarfile.open` raises `OSError` — so both tests exercise the new guard branch rather than a pre-existing path.
