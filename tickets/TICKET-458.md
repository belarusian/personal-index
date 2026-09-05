# TICKET-458: content_collections.CollectionManager.clear_items generic docstring (class-(b) doc-drift)

- File: personal_index/content_collections.py
- Function: CollectionManager.clear_items (line 231)
- Symptom: one-line generic docstring `"""Remove all items from a collection."""`
  that does not enumerate the guard path, the True-when-exists return contract,
  the reverse-index cleanup, or the `updated_at` refresh the body performs.
- Evidence (line 232): `"""Remove all items from a collection."""`
- Body performs: (1) guard path — `self._collections.get(collection_id)`; if the
  collection is absent, returns False with no changes; (2) on success iterates
  the collection's `item_ids` and cleans up the `_item_to_collections` reverse
  index — removes `collection_id` from each item's list and deletes the list
  entry when it becomes empty; (3) clears `c.item_ids` and refreshes
  `c.updated_at`; (4) returns True iff the collection existed.
- Minimal additive fix: reword the docstring to enumerate the guard path, the
  True-when-exists contract, the reverse-index cleanup, and the `updated_at`
  refresh (NO behavior change). Add ONE pinning test
  `test_clear_items_guard_and_reverse_index` (guard path: missing collection ->
  False, reverse index untouched; success path: items cleared, reverse-index
  entries cleaned up, list entry deleted when empty, `updated_at` refreshed).
- Status: RESOLVED
- Issue: #757
- Renumbered from 457 (collision with parallel pipeline's distinct finding)
