# TICKET-540: ContentCategorizer._score_topic docstring over-promise (class b)

**File:** personal_index/content_categorizer.py
**Symptom:** Docstring at line 509 is a single-line placeholder: `"""Score a single topic against content signals."""` — does not enumerate the actual return contract or scoring logic.
**Evidence:** Line 509: `"""Score a single topic against content signals."""`; body returns `(score, matched, sources)` 3-tuple with weighted capped contributions from text/title/meta_description keyword matches plus flat URL-hint bonus.
**Fix:** Reword docstring to enumerate the exact 3-tuple return, the four signal sources with their capping/weighting, and the empty `(0.0, [], [])` guard. Add ONE pinning test in tests/test_content_categorizer.py.
**Status:** RESOLVED
**Issue:** #955
