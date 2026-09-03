# TICKET-287: backup.py get_backup_info raises on a dict manifest with unexpected keys instead of returning None

- Status: OPEN
- Issue: #396
- Module: personal_index/backup.py
- Class: TypeError-coverage (from_dict raises TypeError on unexpected keys; not caught)

## Symptom
`BackupManager.get_backup_info` (line 209) returns `None` for a missing file and for a
non-dict manifest (lines 215, 220), but for a dict manifest with an unexpected key it calls
`BackupManifest.from_dict(data)` (line 221) which raises `TypeError` (from `cls(**data)`).
The method's contract is "return None on any malformed manifest"; the TypeError path
violates it and crashes the caller.

## Evidence
- personal_index/backup.py:215  `return None`  (missing file)
- personal_index/backup.py:220  `return None`  (non-dict manifest)
- personal_index/backup.py:221  `return BackupManifest.from_dict(data)`   <- TypeError on unexpected key, uncaught
- personal_index/backup.py:47   `return cls(**data)`
- Runtime: manifest {'backup_id':'abc','unexpected_key':1} -> get_backup_info('abc') raises
           TypeError: BackupManifest.__init__() got an unexpected keyword argument 'unexpected_key'

## Minimal additive fix
- Wrap the `from_dict` call in `try/except (KeyError, TypeError)` and `return None` on
  failure, matching the existing non-dict degrade path.

## Regression tests (tests/test_backup.py)
- a dict manifest with an unexpected key returns None (does not raise).
