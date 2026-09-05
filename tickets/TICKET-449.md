# TICKET-449: content_pin.pin_content docstring under-describes its False return path

Status: OPEN

## File
personal_index/content_pin.py

## Symptom
The module-level convenience function `pin_content` documents its
return as only "True if successfully pinned." but it delegates to
`ContentPinner.pin`, which returns **False** when persistence fails (OSError in
`_save`) and rolls back the in-memory state. The sibling `unpin_content`
already documents both the True and False paths; `pin_content`
omits the False path entirely, so the docstring under-describes the actual
behavior.

## Evidence
- `pin_content` docstring: Returns section says only
  "True if successfully pinned."
- `pin_content` body: `return _get_default_pinner().pin(item_id, reason, metadata)`
- `ContentPinner.pin`: returns False on OSError in `_save`
  after rolling back `self._pinned` to the snapshot.
- `unpin_content` docstring documents the False path:
  "Returns False if the unpin could not be persisted (e.g. a disk I/O error
  in _save); on failure the in-memory state is rolled back so the item is
  not left unpinned."

## Minimal additive fix
Reword the `pin_content` Returns docstring to state the exact two-path
behavior (True on success; False on persistence failure with rollback),
matching the `unpin_content` wording. Add ONE pinning test that pins the
corrected claim against the returned object: monkeypatch the default
pinner's `_save` to raise OSError and assert `pin_content` returns False
and the item is not left pinned (guard path), alongside the existing
success-path test (normal case). Doc-only; no behavior change.

## Issue
Issue: #737
