# TICKET-352: content_annotations.get_recent docstring omits sort key/direction and default limit

**File:** `personal_index/content_annotations.py`
**Symptom:** `AnnotationManager.get_recent` docstring is a blanket "Get the most
  recent annotations." but the body sorts by `created_at` in descending order
  (`reverse=True`) and slices to `limit` (default 10). The docstring names none
  of the sort key, the sort direction, or the default limit.
**Evidence:** Line 163: `"""Get the most recent annotations."""` — no mention of
  the `created_at` sort key, the descending direction, or the default `limit=10`.
  Lines 164-166 show: `all_ann.sort(key=lambda a: a.created_at, reverse=True)`
  then `return all_ann[:limit]`.
**Fix:** Reword docstring to state the exact sort key (`created_at`), the
  descending direction, and the default limit (10). Add ONE behavior test pinning
  the corrected claim: annotations with distinct `created_at` values are returned
  in descending `created_at` order (newest first) against the returned list.
**Status:** RESOLVED (merged to main 60d3b3d, gh #542 closed)
**Issue:** #542
