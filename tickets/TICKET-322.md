# TICKET-322

- Status: OPEN
- Module: personal_index/content_pin.py
- Class: (b) doc/behavior drift — docstring over-promises a return path

## Symptom
`ContentPinner.pin` docstring says:
    Returns:
        True if successfully pinned.
The phrasing "if successfully pinned" implies a conditional boolean with a
possible `False` failure path. The body, however, unconditionally inserts the
item into `self._pinned`, calls `self._save()`, and returns `True` — it never
returns `False` under any input. The docstring promises a return value the code
does not honor.

## Evidence
- personal_index/content_pin.py (`pin`): body is
    self._pinned[item_id] = PinnedItem(...)
    self._save()
    return True
  — no branch ever returns False.
- Runtime: `pin('a')`, `pin('a')` again, `pin('b')` all return True.

## Minimal additive fix
Correct the `pin` docstring to state the actual contract: always returns True
(the item is pinned/overwritten unconditionally; no failure path). Add a
regression test pinning the corrected contract (pin always returns True, even
for a re-pin of an already-pinned id). No behavior change.

## Issue: #480
