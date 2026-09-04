# TICKET-345: content_collections.CollectionManager.move_item docstring over-promises "move"

- File: personal_index/content_collections.py
- Function: CollectionManager.move_item (line 213)
- Symptom: docstring says "Move an item from one collection to another," which
  implies the item was present in the source collection and is relocated. But the
  body calls `from_c.remove_item(item_id)` (a no-op when the item is absent from
  the source) and `to_c.add_item(item_id)` unconditionally, then returns True
  whenever BOTH collections exist -- regardless of whether the item was ever in
  the source. So moving an item that is NOT in the source still adds it to the
  destination and returns True: it is an "add to dest, remove from source if
  present" operation, not a guaranteed move.
- Evidence line: `from_c.remove_item(item_id)` / `to_c.add_item(item_id)` then
  `return True` with no membership check on the source collection.
- Minimal additive fix: reword the docstring to state the exact behavior (adds the
  item to the destination, removes it from the source only if present, returns
  True iff both collections exist, False if either is missing), and add ONE
  behavior test pinning that move_item on an item absent from the source still
  adds it to the destination and returns True.
- Status: OPEN
- Issue: #528
