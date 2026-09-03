# TICKET-291: backup_store.py import_from_file unguarded json.loads and KeyError

- Status: OPEN
- Module: personal_index/content_backup/backup_store.py
- Function: BackupStore.import_from_file (line 155)

## Symptom
The docstring promises `ValueError` for any malformed input ("Raises: ValueError: If the file does not contain a JSON object."), but two unguarded paths violate this contract:
1. `json.loads(filepath.read_text())` (line 171) — a corrupt/truncated file (e.g. `{`) raises `json.JSONDecodeError`, not `ValueError`.
2. `data["backup_id"]`, `data["timestamp"]`, `data["item_count"]`, `data["items"]` (lines 176-179) — a valid JSON dict missing any required key raises `KeyError`, not `ValueError`.

## Evidence
- Line 171: `data = json.loads(filepath.read_text())` — no try/except
- Lines 176-179: direct `data["key"]` access — no `.get()` or try/except
- Docstring (line 168): "Raises: ValueError: If the file does not contain a JSON object."
- Tests (test_backup_store.py lines 93-109) only cover non-dict JSON (null, 42, list); no test for corrupt JSON or missing keys.

## Minimal Additive Fix
Wrap `json.loads` in `try/except json.JSONDecodeError as exc` → raise `ValueError(f"Invalid backup file {filepath}: not valid JSON: {exc}") from exc`.
Wrap the four required-key accesses in `try/except KeyError as exc` → raise `ValueError(f"Invalid backup file {filepath}: missing required key {exc}") from exc`.
Add 2 regression tests: (1) corrupt file `{` raises ValueError not JSONDecodeError; (2) dict missing `timestamp` raises ValueError not KeyError.

## Issue: #413
