# TICKET-368 — remove_query_params prefix-match drops sibling params

- **File:** personal_index/url_utils.py
- **Function:** remove_query_params (lines 211-230)
- **Class:** (a) behavioral bug — substring/prefix collision
- **Symptom:** Removing a query param also removes any *sibling* param whose
  key merely starts with the target key, because the filter uses
  `p.startswith(f"{param}=")` (a prefix test) instead of an exact key match.
- **Evidence (line 220-222):**
- **Issue:** #574

## RESOLVED
- Merged to main e2b8cb2 (PR #575), gh #574 closed.
