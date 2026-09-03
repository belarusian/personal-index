# TICKET-320: content_rollback.rollback docstring promises a side-effect the code does not perform

- Status: OPEN
- Issue: #476
- Module: personal_index/content_rollback.py
- Defect class: (b) doc/behavior drift — the docstring promises a mutation ("Roll back a
  URL to a previous version") that the body does not perform.

## Symptom
`ContentRollback.rollback(url, index=0)` (content_rollback.py:36) has the docstring:
    """Roll back a URL to a previous version."""
The body, however, only *returns* the `RollbackPoint` at `index` (or `None` if the URL has
no points). It performs no mutation: there is no "current content" store in this class to
restore, the stored point list is untouched, and nothing is written. The docstring reads
as if the call applies the rollback (a side-effect), which the code does not honor.

## Evidence (verified at runtime, cycle 70)
    r = ContentRollback()
    r.create_rollback_point(RollbackPoint(url="http://x.com", content="v1"))
    r.create_rollback_point(RollbackPoint(url="http://x.com", content="v2"))
    res = r.rollback("http://x.com", index=0)
    # res.content == "v1"
    # r.get_rollback_points("http://x.com") == [v1, v2]   (unchanged — no mutation)
The method is a pure accessor; the "Roll back ... to a previous version" wording
over-promises a state change that never happens.

## Impact
A caller reading the docstring would expect `rollback()` to restore/apply the selected
version (e.g. update a "current" pointer or persist state). In reality it only fetches
the point, so a caller relying on the documented side-effect would silently believe a
rollback was applied when none was. The existing tests (tests/test_content_rollback.py)
only assert the *return value*, not any mutation, so the drift is uncaught.

## Fix (minimal, additive)
Correct the docstring to state the actual contract: it returns the `RollbackPoint` at
`index` (0 = oldest) or `None` if the URL has no rollback points, and performs no
mutation. No behavior change — the body is the intended design (this class stores
snapshots only; applying a rollback is the caller's responsibility). Add a regression
test pinning the corrected contract (returns the indexed point; does not mutate the
stored list).
