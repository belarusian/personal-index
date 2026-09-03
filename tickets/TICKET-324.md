# TICKET-324

- Status: RESOLVED (merged to main bbd78fe, gh #487 merged, gh #486 closed)
- Issue: #486 (closed)
- Module: personal_index/content_pin.py
- Class: (b) doc/behavior drift — docstring over-promises a return path

## Symptom
`ContentPinner.unpin` docstring says:
    Returns:
        True if successfully unpinned (or was not pinned).
The "True if" phrasing implies a conditional boolean with a possible `False`
failure path. The body, however, unconditionally returns `True` in every branch:
if the item is pinned it is deleted and `self._save()` is called, and the
function falls through to `return True`; if the item was not pinned it skips the
`if` block and still reaches `return True`. There is no input for which `unpin`
returns `False`. The docstring promises a return value the code does not honor.

The same over-promise is repeated verbatim in the module-level wrapper
`unpin_content` (content_pin.py:167-176), which delegates to `unpin`.

This is the same drift class as TICKET-322, which corrected the sibling method
`pin` to state the unconditional contract ("always returns True ... no failure
path"). `unpin` was left with the stale conditional phrasing.

## Evidence
- personal_index/content_pin.py (`unpin`, lines 102-114): body is
    if item_id in self._pinned:
        del self._pinned[item_id]
        self._save()
    return True
  — the only return statement is `return True`; no branch returns False.
- personal_index/content_pin.py (`unpin_content`, lines 167-176): docstring
  repeats "True if successfully unpinned (or was not pinned)."
- Runtime: `unpin('a')` after `pin('a')` returns True; `unpin('b')` (never
  pinned) also returns True.

## Minimal additive fix
Correct the `unpin` docstring (and the `unpin_content` wrapper docstring) to
state the actual contract: always returns True (the item is unpinned if present,
or is a no-op if absent; there is no failure path). Add a regression test
pinning the corrected contract (unpin always returns True, for both a pinned id
and a never-pinned id). No behavior change.
