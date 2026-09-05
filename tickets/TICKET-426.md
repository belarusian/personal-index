# TICKET-426: content_pin.unpin — implement missing failure path (CLAIM TRUTH)

**Status:** RESOLVED
**Issue:** #690
**File:** personal_index/content_pin.py
**Function:** ContentPinner.unpin (line 108) + unpin_content (line 174)

## Symptom
The original docstring claim "True if successfully unpinned (or was not pinned)"
was downgraded by commit bbd78fe (TICKET-324) to "there is no failure path, so
this always returns True." However, `unpin` calls `self._save()` which performs
disk I/O (mkdir/open/json.dump) that can raise OSError — a failure path EXISTS.
This is the same class of genuine over-promise as `pin` (TICKET-415, cycle 54).

## Evidence
- `unpin` body: `del self._pinned[item_id]; self._save()` — `_save` does
  `os.makedirs` + `open(..., "w")` + `json.dump` (lines 68-77).
- `pin` (already fixed in cycle 54) has the identical structure and was
  corrected to snapshot + try/except OSError + rollback + return False.
- The pinning test `test_unpin_always_returns_true_no_failure_path` (line 136)
  pins the DOWNGRADED claim.

## Fix
1. In `ContentPinner.unpin`: snapshot `self._pinned`, wrap `self._save()` in
   try/except OSError, on failure restore snapshot and return False.
2. Update docstring to original claim: "True if successfully unpinned (or was
   not pinned). Returns False if the unpin could not be persisted."
3. Update `unpin_content` module-level docstring similarly.
4. Re-pin the pinning test to the ORIGINAL claim: rename
   `test_unpin_always_returns_true_no_failure_path` to
   `test_unpin_returns_false_and_rolls_back_on_save_failure` (mirroring the
   pin test pattern), and add a no-op case that still returns True.
