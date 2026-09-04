# TICKET-337: progress.ProgressStore.load_all docstring over-promises "count loaded"

Status: OPEN
Module: personal_index/progress.py
Class: (b) docstring over-promises behavior the code does not do

## Symptom
`ProgressStore.load_all` docstring reads:
    """Load trackers from disk. Returns count loaded."""
The body loads every tracker from the JSON file into `self._trackers` and then
returns `len(self._trackers)` (progress.py:283). That is the TOTAL number of
trackers currently in the store after loading, NOT the number loaded in this
call. If the store already held trackers (e.g. created in-memory via
`create()`), the return value is inflated beyond the actual loaded count.
Verified: a store with 1 in-memory tracker + a file with 1 tracker returns 2,
not 1. The docstring therefore over-promises "count loaded" when the value is
"total trackers in store after load".

## Evidence
personal_index/progress.py:266  (def load_all(self) -> int:)
personal_index/progress.py:267  ("""Load trackers from disk. Returns count loaded.""")
personal_index/progress.py:280-282 (for oid, d in data.items(): ... self._trackers[oid] = tracker)
personal_index/progress.py:283  (return len(self._trackers))

## Minimal additive fix
Reword the `load_all` docstring to what the code actually does:
    """Load trackers from disk. Returns total number of trackers in the store."""
Do NOT change what is returned (behavior change, out of scope).

## Regression test
Assert via inspect.getsource that the load_all docstring no longer claims
"count loaded", and that load_all returns the total store size (not just the
loaded count) when the store already holds trackers (behavior unchanged).

Issue: #512
