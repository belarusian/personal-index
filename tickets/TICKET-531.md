# TICKET-531: Pin DedupResult.summary() contract + empty-state guard test

**Status:** OPEN
**File:** personal_index/content_dedup.py
**Issue:** #917

**Symptom:** `DedupResult.summary()` carried a generic one-line docstring
("Generate a human-readable summary.") that over-promised the content without
detailing the exact format.

**Fix:** Reword the docstring to enumerate the exact 7-line contract the body
emits (Deduplication Results / Total items / Unique items / Duplicates found /
Duplicate groups / Dedup ratio / Method) and state the empty-state behavior
(total_items=0 -> "0.0%" ratio, numeric fields render as 0). Add a guard-path
pinning test `test_summary_empty_state` that constructs an empty DedupResult and
asserts the "0.0%" ratio + all-zero fields against the returned string.

**Note (ticket renumber):** this work was originally filed as TICKET-524 and
renumbered through 525/527/528/529/530 as parallel runs claimed those numbers.
TICKET-530 on main is the ContentAPI._health_check docstring (PR #932, issue
#931) — different work — so this DedupResult work lands as TICKET-531.
