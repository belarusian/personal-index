# TICKET-454

- Module: personal_index/content_collections.py
- Class: CollectionManager
- Function: remove_item
- Status: RESOLVED (merged to main, gh #749 closed, squash 1c28fce)
- Issue: #749
- Type: doc-drift (class-(b): generic docstring omits guard path + reverse-index cleanup)

## Symptom
`CollectionManager.remove_item(collection_id, item_id)` has a one-line generic
docstring ("Remove an item from a collection.") that does not enumerate the
exact behavior the body performs:
  - the guard path (collection missing -> returns False, no changes),
  - that it returns True whenever the collection EXISTS, even when the item
    was not actually in the collection (the underlying `Collection.remove_item`
    is a no-op in that case and does not refresh `updated_at`),
  - the `_item_to_collections` reverse-index cleanup (remove the collection id
    from the item's list; delete the list entry when it becomes empty).

## Evidence
personal_index/content_collections.py:149-161
  def remove_item(self, collection_id: str, item_id: str) -> bool:
      """Remove an item from a collection."""
      c = self._collections.get(collection_id)
      if c:
          c.remove_item(item_id)
          if item_id in self._item_to_collections:
              if collection_id in self._item_to_collections[item_id]:
                  self._item_to_collections[item_id].remove(collection_id)
              if not self._item_to_collections[item_id]:
                  del self._item_to_collections[item_id]
          return True
      return False

## Minimal additive fix
Reword the docstring to state the EXACT behavior (guard path, the True-when-
collection-exists return contract, and the reverse-index cleanup). NO behavior
change. Add ONE pinning test asserting the guard path (missing collection ->
False, reverse index untouched) and the success path (item removed from both
the collection and the reverse index; reverse-index list entry deleted when it
becomes empty).

Note: renumbered from TICKET-453 (assigned to content.ExtractedContent.get_keywords
by the parallel pipeline, merged as b671c69) to avoid a ticket-number collision.
