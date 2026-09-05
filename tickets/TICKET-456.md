# TICKET-456: content_collections.CollectionManager.delete generic docstring (class-(b) doc-drift)

- File: personal_index/content_collections.py
- Function: CollectionManager.delete (line 208)
- Symptom: one-line generic docstring `"""Delete a collection."""` that does not
  enumerate the guard path, the True-when-exists return contract, or the
  reverse-index cleanup the body performs.
- Evidence (line 209): `"""Delete a collection."""`
- Body performs: (1) guard path — `self._collections.pop(collection_id, None)`;
  if the collection is absent, returns False with no changes; (2) on success
  cleans up the `_item_to_collections` reverse index — for each item in the
  deleted collection, removes `collection_id` from the item's list and deletes
  the list entry when it becomes empty; (3) returns True iff the collection
  existed.
- Minimal additive fix: reword the docstring to enumerate the guard path, the
  True-when-exists contract, and the reverse-index cleanup (NO behavior
  change). Add ONE pinning test `test_delete_guard_and_reverse_index` (guard
  path: missing collection -> False, reverse index untouched; success path:
  collection removed and its items' reverse-index entries cleaned up, list
  entry deleted when empty).
- Status: OPEN
- Issue: #751
