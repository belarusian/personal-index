# TICKET-299: backup.py BackupManager._extract_archive unguarded tarfile.open (corrupt tar)

- Status: RESOLVED (merged to main cfd844e, gh #430 closed)
- Issue: #430
- Module: personal_index/backup.py
- Function: BackupManager._extract_archive (line 196)

## Symptom
`restore_backup` establishes a clean, documented error contract for every failure it can hit: `FileNotFoundError` for a missing backup/archive, and `ValueError` for an invalid manifest (bad JSON, non-dict, unexpected keys). But the archive-extraction step is unguarded: `_extract_archive` calls `tarfile.open(str(archive_path), mode)` (line 198) with no try/except. A corrupt `.tar.gz` (or `.tar`) raises `tarfile.TarError` (e.g. `ReadError` "not a gzip file", `CompressionError`) and a truncated `.tar.gz` raises `EOFError` from the gzip layer; that raw exception propagates straight out of `restore_backup`, violating the module's clean-error style. This is the untested-error-path class (c), not the closed corrupt-JSON-guard class.

## Evidence
- Line 198: `with tarfile.open(str(archive_path), mode) as tar:` in `_extract_archive` — no try/except.
- Lines 153-168: `restore_backup` already raises `ValueError` for invalid manifest data — the module's documented style for "invalid data" conditions.
- Verified by running the code: writing `b'GARBAGE_NOT_A_TAR'` over a real `backup_<id>.tar.gz` makes `tarfile.open(path, "r:gz")` raise `tarfile.TarError` (ReadError), and `restore_backup(backup_id, target)` leaks that raw `tarfile.TarError` to the caller.

## Minimal additive fix
Wrap the `tarfile.open`/`extractall` body in `_extract_archive` in `try/except (tarfile.TarError, EOFError) as exc: raise ValueError(f"Corrupt or unreadable archive {archive_path}: {exc}") from exc`. A corrupt archive raises `tarfile.TarError` (ReadError/CompressionError); a truncated `.tar.gz` raises `EOFError` from the gzip layer before tarfile sees a valid stream — both are translated to a clean `ValueError`, mirroring the module's existing invalid-data style (do NOT invent a new contract; do NOT degrade to a count — `restore_backup` returns the count as `files_restored`, so a corrupt/truncated archive must fail loudly, not silently return 0). Add 2 regression tests in tests/test_backup.py: (a) a corrupt archive (garbage bytes over `backup_<id>.tar.gz`, then `restore_backup`) asserts a clean `ValueError` (NOT a raw `tarfile.TarError` leak), with a precondition that `tarfile.open` on the garbage raises `tarfile.TarError`; (b) a truncated archive (real archive cut to 1/3) asserts a clean `ValueError`, with a precondition that `tarfile.open` raises `(tarfile.TarError, EOFError)` — so both tests exercise the new guard branch rather than a pre-existing path.
