# TICKET-341: normalize_url docstring over-promises "normalizes case"

**File:** personal_index/content_dedup.py
**Symptom:** Docstring says "normalizes case" (implying all case is normalized),
but the body only lowercases the scheme and host. Path and query segments retain
their original case.
**Evidence:** Line 40: "Removes trailing slashes, fragments, and normalizes case."
vs lines 52-59: only `scheme.lower()` and `host_path[0].lower()` are applied.
**Fix:** Reword docstring to "Removes trailing slashes and fragments, and
lowercases the scheme and host." (doc-only, no behavior change).
Add one behavior test pinning that an uppercase path segment is preserved.
**Status:** OPEN
**Issue:** #520
