# TICKET-274: backup.py json.load non-dict guard sweep

**Status:** RESOLVED
**Module:** personal_index/backup.py
**Issue:** #377

## Symptom
Three `json.load` sites in `backup.py` feed `BackupManifest.from_dict(...)` without
verifying the loaded JSON is a dict. A corrupted or malformed manifest file
containing `null`, a list, or a number will cause `AttributeError`/`TypeError`
inside `from_dict` instead of a clean, site-appropriate failure.

## Evidence
- `list_backups()` (~line 135): `data = json.load(f)` then `BackupManifest.from_dict(data)` — inside try/except but the except only catches `(json.JSONDecodeError, KeyError)`, not `AttributeError`/`TypeError`.
- `restore_backup()` (~line 149): `BackupManifest.from_dict(json.load(f))` — no try/except at all; bad file propagates raw exception.
- `get_backup_info()` (~line 210): `return BackupManifest.from_dict(json.load(f))` — no try/except; bad file propagates raw exception.

## Fix (per-site, matching documented contract)
1. `list_backups()`: add `if not isinstance(data, dict): continue` after `json.load` — matches existing skip-on-error intent.
2. `restore_backup()`: add `if not isinstance(data, dict): raise ValueError(...)` — explicit restore should fail loudly.
3. `get_backup_info()`: add `if not isinstance(data, dict): return None` — matches the "not found" return path.

## Tests
Add regression tests: write a bad manifest file (null, list, number) to tmp_path backup dir; assert:
- `list_backups()` skips it (not in results)
- `get_backup_info()` returns `None`
- `restore_backup()` raises `ValueError` with clear message
