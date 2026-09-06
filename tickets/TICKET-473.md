# TICKET-473: CollectionManager.merge self-merge destroys the collection

Status: RESOLVED (PR #791, issue #789 closed, merge 7b7f596)
Issue: #789

## File
personal_index/content_collections.py - `CollectionManager.merge` (line ~285)

## Symptom
`merge(target_id, source_id)` with `target_id == source_id` returns `True` but
deletes the collection and loses all of its items. A self-merge is a no-op
conceptually (merging a collection into itself changes nothing), yet the code
path treats it as a real merge: it re-adds the source's items to the target
(the same collection) and then calls `self.delete(source_id)`, which removes
the collection from `_collections` and cleans up the reverse index.

## Evidence
    m = CollectionManager(); a = m.create('A')
    m.add_item(a, 'i1'); m.add_item(a, 'i2')
    m.merge(a, a)   # -> True
    m.count()       # -> 0
    m.get(a)        # -> None

The collection that was merged into itself is gone; get_items(a) returns [].

## Minimal additive fix
Guard the self-merge case in `merge`: if `target_id == source_id`, return
`False` without touching the collection or the reverse index (a no-op merge
is not a successful merge). This is additive - it only short-circuits the
degenerate case and leaves the normal two-collection merge path unchanged.

## Pinning test
`test_merge_self_is_noop` - create one collection with items, call
`merge(cid, cid)`, assert it returns `False`, the collection still exists, and
its items are intact.
