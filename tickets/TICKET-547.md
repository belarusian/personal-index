# TICKET-547: ContentScorer._build_score missing docstring

**File:** personal_index/content_scoring.py
**Line:** ~138
**Symptom:** `_build_score` has no docstring. It takes 7 float params (total +
six factor scores) and returns a ContentScore where each of the 7 fields is
`round(x, 4)`, plus a `factors` dict keyed by the six factor names (recency,
relevance, engagement, quality, authority, freshness — NOT total) holding the
UNROUNDED input values.
**Evidence:** Lines 138-155: method body is a single `return ContentScore(...)`
with no docstring.
**Minimal additive fix:** Add a docstring enumerating: (1) the 7 rounded fields,
(2) the factors dict keys (six names, not total) and that values are unrounded.
Add ONE pinning test calling _build_score with known floats and asserting the
returned ContentScore's field values (rounded) AND the factors dict (unrounded).
**Status:** OPEN
Issue: #972
