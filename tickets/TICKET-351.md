# TICKET-351: content_reader.paginate docstring omits sort/clamp/raise behavior

**File:** `personal_index/content_reader.py`
**Symptom:** `paginate` docstring is a blanket "Get a paginated view of content items."
  but the body sorts by `sort_by` (default "score") with `reverse` (default True = descending),
  clamps `page` to [1, total_pages], and raises ValueError if page_size < 1.
**Evidence:** Line 89: `"""Get a paginated view of content items."""` — no mention of sort,
  clamp, or raise. Lines 91-108 show all three behaviors.
**Fix:** Reword docstring to state the exact sort key/direction, page clamping, and
  ValueError condition. Add ONE behavior test pinning the default sort order
  (score descending) against the returned PageView.items.
**Status:** OPEN
**Issue:** #540
