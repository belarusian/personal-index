# TICKET-285: list_backups aborts the whole listing on a non-dict manifest file

Status: RESOLVED
Module: personal_index/backup.py (BackupManager.list_backups, lines 125-140)
- Issue: #395

## Symptom
`_save_manifest` (line 80-81) always writes `manifest.to_dict()`, i.e. a JSON
OBJECT, so every well-formed manifest file is a dict. `list_backups` is
documented to be tolerant of bad files - it catches
`(json.JSONDecodeError, KeyError)` and `continue`s - but a manifest file whose
top-level JSON value is a non-dict (a hand-edited `[]`, `"x"`, `5`, `null`, or
a truncated/overwritten file) reaches `BackupManifest.from_dict(data)` as
`cls(**data)` and raises `TypeError: argument after ** must be a mapping`.
`TypeError` is not in the except tuple, so ONE corrupt file kills the entire
listing instead of being skipped.

## Evidence (runtime repro)
    BackupManifest.from_dict([])     -> TypeError: ... argument after ** must be
                                        a mapping, not list
    BackupManifest.from_dict(None)   -> TypeError: ... not NoneType
    # same shape at backup.py:135-137: except (json.JSONDecodeError, KeyError)
    # does not cover TypeError, so list_backups() propagates it.

## Minimal additive fix
Keep the skip-on-malformed semantics (return shape is a list of manifests);
guard the loaded value's type BEFORE constructing, and widen the except tuple
so a wrong-but-parseable file is skipped rather than fatal:
    data = json.load(f)
    if not isinstance(data, dict):
        continue
    manifests.append(BackupManifest.from_dict(data))
    ...
    except (json.JSONDecodeError, KeyError, TypeError):
        continue
Do NOT blanket-apply this to the other two sites: get_backup_info must return
None and restore_backup must fail loudly.

## Regression tests to add
1. A `backup_*.json` containing `[]` (or `"str"`) is skipped; the valid sibling
   is still listed.
2. A manifest file containing `null` does not raise from list_backups().

## Resolution (cycle 30)
Fixed on branch build30/backup-manifest-type-guards (no git remote in this sandbox -> no gh issue; Issue: LOCAL-NONE). list_backups now skips a non-dict manifest (isinstance guard) and its except tuple covers TypeError, so one corrupt file no longer aborts the listing. Regression tests in tests/test_backup.py::TestBackupManifestCorruption. Local gate green (pytest 5218 passed / 22 skipped; ruff clean; mypy 495 files).

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-262 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.
