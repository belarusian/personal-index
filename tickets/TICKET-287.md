# TICKET-287: restore_backup dies with an opaque TypeError on a non-dict manifest

Status: RESOLVED
Module: personal_index/backup.py (BackupManager.restore_backup, lines 142-160)
- Issue: #397

## Symptom
This site deliberately fails loudly (a bad restore must not be silently
ignored) and that is the correct semantics - but the failure it produces for a
non-dict manifest is an interpreter-level `TypeError: ... argument after **
must be a mapping, not list` raised from inside the dataclass constructor. The
operator gets no mention of which backup id / manifest path is corrupt, and
`TypeError` is the wrong class to catch for callers that already handle the
documented `FileNotFoundError` / data-shape failures of a restore.

## Evidence (runtime repro)
    BackupManifest.from_dict([])   -> TypeError: personal_index.backup.BackupManifest()
                                       argument after ** must be a mapping, not list
    # reached from restore_backup line 149: json.load(f) yields [] for a
    # truncated/hand-edited manifest; nothing between it and the caller.

## Minimal additive fix
Keep it loud, make it explicit and typed. Validate BEFORE constructing, then
raise a ValueError naming the backup id:
    data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Corrupt backup manifest (expected a JSON object): {manifest_file}")
    manifest = BackupManifest.from_dict(data)
Do NOT wrap this in try/except that returns or continues - unlike
list_backups (skip) and get_backup_info (None), a restore must abort.

## Regression tests to add
1. Manifest file containing `[]` -> restore_backup raises ValueError whose
   message names the backup id / manifest path (not a bare TypeError).
2. A valid manifest still restores and returns the result dict unchanged.

## Resolution (cycle 30)
Fixed on branch build30/backup-manifest-type-guards (Issue: LOCAL-NONE - no remote). restore_backup keeps loud semantics but now raises ValueError naming the manifest path / backup id (and wraps the bad-fields TypeError) instead of an opaque `argument after ** must be a mapping` TypeError. Regression tests in tests/test_backup.py::TestBackupManifestCorruption.

## Reconciliation addendum (cycle 31)
Renumbered from local TICKET-264 (collided with a DIFFERENT upstream ticket of the same
number). The earlier "no git remote / Issue: LOCAL-NONE" note is stale: origin exists
and this work is tracked upstream as the Issue above, landed via the reconcile/main-31 PR.

Note (cycle 31): the loud message was finally aligned to upstream TICKET-274
wording - "Invalid manifest in <file>: expected dict, got <type>" - while keeping
the local extra (bad-fields TypeError wrapped into the same located ValueError).
