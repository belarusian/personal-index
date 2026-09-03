# TICKET-286: get_backup_info raises on a corrupt manifest instead of returning None

Status: RESOLVED
Module: personal_index/backup.py (BackupManager.get_backup_info, lines 201-210)
- Issue: #396

## Symptom
The signature is `-> BackupManifest | None` and the missing-file path returns
`None`, so the method's contract is "None when there is no usable info about
this backup". But the read path has NO error handling at all: a manifest file
that exists yet is unparseable (`json.JSONDecodeError`) or holds a non-dict
top-level value (`TypeError` from `cls(**data)`, or `TypeError` for an unknown
key) escapes as an exception. Callers that already branch on `None`
(`info = mgr.get_backup_info(bid); if info: ...`) crash on a half-written
manifest instead of treating the backup as unknown.

## Evidence (runtime repro)
    # backup.py:209-210
    with open(str(manifest_file)) as f:
        return BackupManifest.from_dict(json.load(f))   # no guard, no except
    # file containing "["  -> json.JSONDecodeError
    # file containing "[]" -> TypeError: argument after ** must be a mapping,
    #                          not list   (from_dict([]) verified at runtime)

## Minimal additive fix
Match the declared return shape: an unreadable/unusable manifest is the same
outcome as "no info" -> return None.
    try:
        with open(str(manifest_file)) as f:
            data = json.load(f)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    try:
        return BackupManifest.from_dict(data)
    except (TypeError, ValueError):
        return None
Do NOT copy the skip/None behaviour into restore_backup (that site must stay
loud) and do not change the missing-file branch.

## Regression tests to add
1. Manifest file containing `[]` -> get_backup_info returns None (no raise).
2. Manifest file containing invalid JSON -> returns None.
3. Manifest file with an unknown key -> returns None.
4. Valid manifest still returns the populated BackupManifest.

## Resolution (cycle 30)
Fixed on branch build30/backup-manifest-type-guards (Issue: LOCAL-NONE - no remote). get_backup_info now honours its declared `BackupManifest | None` contract: JSONDecodeError, non-dict top-level value and bad-field construction all return None instead of escaping. Regression tests in tests/test_backup.py::TestBackupManifestCorruption.

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-263 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.
