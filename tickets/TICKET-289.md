# TICKET-289: backup.py get_backup_info still raises JSONDecodeError on an unparseable manifest

- Status: RESOLVED
- Issue: #408
- Module: personal_index/backup.py
- Class: TypeError/JSONDecodeError-coverage (declared `BackupManifest | None` contract violated)

## Symptom
TICKET-287 (gh #396, closed by PR #406 / commit 084f3b6) wrapped only the
`BackupManifest.from_dict(data)` call in `try/except (KeyError, TypeError)`. The
`json.load` call above it is still unguarded, so a manifest file that is not valid
JSON at all (e.g. a truncated write containing `{`) makes `get_backup_info` raise
`json.JSONDecodeError` instead of returning `None`. The method's contract is "return
None on any malformed manifest"; the unparseable path still crashes the caller.

## Evidence
- personal_index/backup.py:217  `data = json.load(f)`   <- unguarded
- personal_index/backup.py:219  `if not isinstance(data, dict): return None` (only reachable for parseable JSON)
- personal_index/backup.py:221  `try: return BackupManifest.from_dict(data)` (the half #406 did fix)
- Runtime probe: backup_raw.json containing `{` -> get_backup_info('raw') raises JSONDecodeError

## Minimal additive fix
- Wrap the `json.load` read in `try/except json.JSONDecodeError: return None`,
  matching the existing non-dict degrade path (the from_dict half is already fixed).

## Regression tests (tests/test_backup.py)
- Parametrised corrupt fixtures ([], "str", 5, null, `{`, {"nope":1}, unexpected-key dict)
  all return None from get_backup_info; `{` is the case that fails before the fix.
