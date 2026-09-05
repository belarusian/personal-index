# TICKET-427: content_collections.CollectionManager.add_item doc-drift (class b)

- File: personal_index/content_collections.py
- Function: CollectionManager.add_item
- Symptom: blanket one-liner docstring "Add an item to a collection." that does not
  enumerate the sub-components: the guard path (collection not found -> returns False
  without touching any index) and the two index updates performed on success
  (Collection.item_ids append via Collection.add_item; _item_to_collections reverse
  index append), nor the True return.
- Evidence: body `c = self._collections.get(collection_id); if c: ... return True; return False`.
- Minimal additive fix: reword the docstring to state the exact guard path and the
  two index updates + True return; add ONE pinning test asserting the returned bool
  and the observable index state (get_items / get_collections_for_item) for the
  normal case AND the guard path (nonexistent collection -> False, reverse index
  untouched).
- Status: OPEN
- Issue: #691
