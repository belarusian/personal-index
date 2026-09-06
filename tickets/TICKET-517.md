# TICKET-517: content_api._match_route docstring is a placeholder

**File:** `personal_index/content_api.py`
**Method:** `_match_route` (line ~46)
**Symptom:** Docstring `"""Match path parts to a route handler."""` does not state the exact dispatch contract (which path tuples map to which handler, the method-gated branches, and the None fallback).
**Evidence:** Line 47: `"""Match path parts to a route handler."""` — no enumeration of branches.
**Fix:** Reword docstring to enumerate all dispatch branches + None fallback. Add one pinning test.
**Issue:** #895
**Status:** RESOLVED
