# TICKET-286: backup.py list_backups aborts whole listing on a dict manifest with unexpected keys

- Status: OPEN
- Issue: #395
- Module: personal_index/backup.py
- Class: TypeError-coverage (from_dict raises TypeError on unexpected keys; not in except tuple)

## Symptom
`BackupManager.list_backups` (line 125) iterates manifest files and calls
`BackupManifest.from_dict(data)` (line 138) inside `except (json.JSONDecodeError, KeyError)`
(line 139). `from_dict` is `cls(**data)` (line 47), so a dict manifest containing an
unexpected key raises `TypeError` ("got an unexpected keyword argument"), which is NOT in
the except tuple. One malformed manifest aborts the ENTIRE listing instead of being skipped.

## Evidence
- personal_index/backup.py:138  `manifests.append(BackupManifest.from_dict(data))`
- personal_index/backup.py:139  `except (json.JSONDecodeError, KeyError):`   <- TypeError not covered
- personal_index/backup.py:47   `return cls(**data)`   <- TypeError on unexpected key
- Runtime: manifest {'backup_id':'abc','unexpected_key':1} -> list_backups() raises
           TypeError: BackupManifest.__init__() got an unexpected keyword argument 'unexpected_key'

## Minimal additive fix
- Add `TypeError` to the except tuple in `list_backups`: `except (json.JSONDecodeError, KeyError, TypeError):`.

## Regression tests (tests/test_backup.py)
- a dict manifest with an unexpected key is skipped; other valid manifests still listed.
