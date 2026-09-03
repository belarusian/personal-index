# TICKET-288: backup.py restore_backup dies with opaque TypeError on a dict manifest with unexpected keys

- Status: RESOLVED
- Issue: #397
- Module: personal_index/backup.py
- Class: TypeError-coverage (from_dict raises TypeError on unexpected keys; not caught)

## Symptom
`BackupManager.restore_backup` (line 144) raises a clean, located `ValueError` for a
non-dict manifest (lines 152-155: "Invalid manifest in <file>: expected dict, got <type>"),
but for a dict manifest with an unexpected key it calls `BackupManifest.from_dict(data)`
(line 157) which raises an opaque `TypeError` ("got an unexpected keyword argument") with no
reference to the manifest file. The method already has a located-error contract for the
non-dict case; the TypeError path bypasses it.

## Evidence
- personal_index/backup.py:152  `if not isinstance(data, dict):`
- personal_index/backup.py:153  `raise ValueError(`  (located "Invalid manifest in <file>...")
- personal_index/backup.py:157  `manifest = BackupManifest.from_dict(data)`   <- TypeError on unexpected key, uncaught
- personal_index/backup.py:47   `return cls(**data)`
- Runtime: manifest {'backup_id':'abc','unexpected_key':1} -> restore_backup('abc', ...) raises
           TypeError: BackupManifest.__init__() got an unexpected keyword argument 'unexpected_key'

## Minimal additive fix
- Wrap the `from_dict` call (line 157) in `try/except (KeyError, TypeError)` and raise the
  same located `ValueError` used for the non-dict case, so the error names the manifest file.

## Regression tests (tests/test_backup.py)
- a dict manifest with an unexpected key raises ValueError naming the manifest file (not TypeError).
