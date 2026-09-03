# TICKET-279: backup_store.py import_from_file() crashes on non-dict JSON

- Status: RESOLVED
- Module: personal_index/content_backup/backup_store.py
- File: personal_index/content_backup/backup_store.py

## Symptom
`BackupStore.import_from_file(filepath)` raises `TypeError` when the JSON file contains a
valid-JSON-but-wrong-type value (null / number / list / string) instead of the dict
that `export_to_file()` writes.

## Evidence
- Writer: `export_to_file()` (line ~153) persists `json.dumps(data, ...)` where `data` is a
  **dict** with keys `backup_id`, `timestamp`, `item_count`, `metadata`, `items`.
- Loader: line 168 `data = json.loads(filepath.read_text())`; line 170
  `entry = BackupEntry(backup_id=data["backup_id"], ...)`.
  A non-dict `data` (null/number/list/string) has no `__getitem__` for a str key -> `TypeError`.
  Verified: null->TypeError, 42->TypeError, [1,2]->TypeError, "str"->TypeError.
  No try/except wraps the load.
- Contract: `import_from_file(filepath) -> BackupEntry` (no Optional/None path). The module's
  existing degrade style for an invalid condition is `raise ValueError` (see
  `export_to_file`, line ~141: `raise ValueError(f"Backup {backup_id} not found")`).

## Minimal additive fix
After `data = json.loads(filepath.read_text())`, add:
    if not isinstance(data, dict):
        raise ValueError("Backup file must contain a JSON object")
This matches the module's existing ValueError degrade style (a raise, not a return-None).

## Regression tests (tests/test_backup_store.py, TestBackupStoreNonDictGuard)
- null, number, list, valid-dict-still-works, valid-after-invalid-not-suppressed.

## Issue
Issue: #386
