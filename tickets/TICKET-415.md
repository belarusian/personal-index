# TICKET-415

- Status: RESOLVED (cycle 54, PR #670, gh #668 closed, main 9a39f41)
- Class: (b) doc-drift / docstring over-promise (CLAIM TRUTH)
- File: personal_index/content_pin.py
- Function: ContentPinner.pin (line 82)
- Issue: #668 (created)
- Note: renumbered from 414 to 415 (same-number collision with the parallel
  pipeline's TICKET-414 for content_search.py SearchIndex.search, main 0f73427).

## Symptom
The class method `pin` docstring was DOWNGRADED by the parallel pipeline
(commit 4535ea8, TICKET-322) from the ORIGINAL claim
    "True if successfully pinned."
to
    "True. The item is pinned (or re-pinned/overwritten) unconditionally;
     there is no failure path, so this always returns True."

The downgrade is a FALSE assertion: `pin` calls `self._save()`, which performs
disk I/O (`Path.mkdir` + `open(..., "w")` + `json.dump`). That I/O can raise
`OSError` (e.g. read-only filesystem, permission denied, disk full). So there
IS a failure path, and the "no failure path / always True" claim is not true.

The ORIGINAL claim ("True if successfully pinned") is the honest contract:
pin should return True on success and False when the pin could not be
persisted. Corroboration: the module-level wrapper `pin_content` (line 154)
was NOT downgraded and still carries the original claim
"True if successfully pinned." — only the class method was downgraded.

## Evidence
- personal_index/content_pin.py:82-100 (pin body: `self._save(); return True`)
- personal_index/content_pin.py:68-80 (_save: mkdir + open + json.dump, no guard)
- personal_index/content_pin.py:154-165 (pin_content still says "True if
  successfully pinned")
- git: commit 4535ea8 (TICKET-322) reword; original docstring recovered via
  `git log -p -1 4535ea8 -- personal_index/content_pin.py`

## Minimal additive fix (CLAIM TRUTH: implement the missing behavior)
1. In `pin`, capture the pre-pin snapshot of `self._pinned`, attempt
   `self._save()` inside a `try/except OSError`, and on failure roll back
   `self._pinned` to the snapshot and `return False`. On success `return True`.
2. Restore the ORIGINAL claim in the `pin` docstring:
   "True if successfully pinned." (plus a short note that a persistence
   failure returns False and leaves the in-memory state unchanged).
3. Re-pin the pinning test `test_pin_always_returns_true_no_failure_path`
   (tests/test_content_pin.py:57) to the ORIGINAL claim: rename/repurpose it to
   assert the success path returns True AND add failure-path tests that force
   `_save` to raise OSError and assert `pin` returns False and the in-memory
   state is unchanged (rollback). Do not leave a test pinning the false
   "no failure path" claim.

## Issue: #668
