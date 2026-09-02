# TICKET-257: content_versioning version-id collision after delete_version

## File
personal_index/content_versioning.py

## Symptom
`create_version` derives the next version id from the current list length:
`version_id = f"{item_id}_v{len(self._versions.get(item_id, [])) + 1}"` (line 102).
After `delete_version` removes an entry, the list shrinks, so a subsequent
`create_version` reuses an id that still exists -> duplicate `version_id` for the
same `item_id`.

## Evidence
Runtime repro (storage_path=/tmp/cv_repro.json):
    create_version('item-1','a')   # item-1_v1
    create_version('item-1','b')   # item-1_v2
    delete_version('item-1','item-1_v1')   # list=[v2], len=1
    create_version('item-1','c')   # len=1 -> item-1_v2  (COLLISION)
    ids: ['item-1_v2', 'item-1_v2']  -> collision: True
`get_version` (line 129) then returns the FIRST match, so the second version is
unreachable by id.

## Minimal additive fix
In `create_version`, compute the next numeric suffix from the max existing
`_v<N>` suffix for the item (not from list length), so ids stay unique after
deletions. Add a regression test asserting unique ids after delete+create.

## Issue: #343

## Status
OPEN
