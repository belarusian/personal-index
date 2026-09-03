# TICKET-290: backup.py restore_backup dies with an unlocated JSONDecodeError on an unparseable manifest

- Status: OPEN
- Issue: #409
- Module: personal_index/backup.py
- Class: error-location (declared located-ValueError contract bypassed)

## Symptom
`BackupManager.restore_backup` documents a located failure for corrupt manifests:
the non-dict branch raises `ValueError("Invalid manifest in <file>: expected dict,
got <type>")`. But the `json.load` call runs before that check and is unguarded, so
a manifest file that is not valid JSON raises a bare `json.JSONDecodeError` that
names neither the backup nor the manager's manifest path contract. Same located-error
class as TICKET-288, different exception source.

## Evidence
- personal_index/backup.py:150  `data = json.load(f)`   <- unguarded
- personal_index/backup.py:152  `if not isinstance(data, dict):`
- personal_index/backup.py:153  `raise ValueError(f"Invalid manifest in {manifest_file}: ...")`
- Runtime probe: backup_raw.json containing `{` -> restore_backup('raw', ...) raises JSONDecodeError

## Minimal additive fix
- Wrap the `json.load` read in `try/except json.JSONDecodeError as exc` and raise
  `ValueError(f"Invalid manifest in {manifest_file}: not valid JSON for backup
  {backup_id!r}: {exc}") from exc`, reusing the located-error style of the non-dict branch.

## Regression tests (tests/test_backup.py)
- Every corrupt fixture (including `{`) raises ValueError matching "Invalid manifest"
  whose message contains the manifest filename.
