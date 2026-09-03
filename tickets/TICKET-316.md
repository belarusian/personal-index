# TICKET-316: content_linker.ContentLinker.clear_cache docstring understates its destructive scope

- Status: RESOLVED (merged to main edc27f1, gh #470 merged, gh #469 closed)
- Module: personal_index/content_linker/linker.py
- Defect class: (b) doc/behavior drift — docstring says "Clear all cached data" but the body also wipes the entire source item store
- Issue: #469

## Symptom
`ContentLinker.clear_cache()` (linker.py:143) is documented as
"Clear all cached data." — the wording of a method that only resets a
derived cache (the `_link_cache` of precomputed related-item results).
But the body is:

    self._items.clear()
    self._link_cache.clear()

It also clears `self._items`, the **primary store of all content items**
added via `add_item`. So a caller who invokes `clear_cache()` expecting to
only invalidate the derived link cache actually loses every item in the
linker (`get_item` / `get_all_items` then return nothing). The name and
docstring both understate the destructive scope.

## Evidence (verified at runtime, cycle 68)
- `add_item('a', ...)`, `add_item('b', ...)` -> `len(get_all_items())` == 2
- `clear_cache()` -> `len(get_all_items())` == 0 ; `get_item('a')` -> None
The item store is wiped, not just the link cache. The destructive behavior
is the intended, tested design (tests/test_content_linker.py:180-183
`test_clear_cache` asserts `len(linker.get_all_items()) == 0` after
`clear_cache()`), so the body is correct and the docstring is the defect.

## Fix (minimal, additive)
Make the docstring honestly document that `clear_cache()` removes ALL
stored items (the primary `_items` store) in addition to the derived
`_link_cache`, i.e. it resets the linker to an empty state. Add a
regression test pinning that `clear_cache()` empties the item store
(`get_all_items()` -> [] and `get_item()` -> None), not merely the link
cache.
