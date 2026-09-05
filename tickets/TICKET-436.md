# TICKET-436: content_collections.CollectionManager.get_stats docstring over-promise

- File: personal_index/content_collections.py
- Function: CollectionManager.get_stats
- Symptom (class-(b) doc-drift): docstring is the blanket "Get collection
  statistics." (content_collections.py:285) which does not enumerate the four
  returned dict keys or their semantics. In particular "total_items" is the SUM
  of per-collection item counts (an item present in N collections is counted N
  times), not the number of DISTINCT items; and "public_collections" /
  "private_collections" partition "total_collections".
- Evidence:
  - docstring (content_collections.py:285): "Get collection statistics."
  - body (content_collections.py:286-292):
      total_items = sum(len(c.item_ids) for c in self._collections.values())
      return {
          "total_collections": len(self._collections),
          "total_items": total_items,
          "public_collections": len(self.list_public()),
          "private_collections": len(self.list_private()),
      }
    -> total_items is a per-collection sum (double-counts items in multiple
      collections); public+private == total_collections; empty manager -> all
      four keys 0.
- Minimal additive fix: reword the docstring to enumerate the four returned
  keys and their exact semantics (total_collections = len of collections;
  total_items = sum of per-collection item_ids lengths, i.e. an item in N
  collections is counted N times, NOT distinct items; public_collections =
  count of is_public collections; private_collections = count of non-public
  collections; empty manager -> all four 0). Add ONE pinning test asserting the
  returned dict fields for the normal case (mixed public/private, an item in
  two collections -> total_items double-counts) AND the empty-manager guard
  path (all four keys 0).
- Status: OPEN
- Issue: #710
