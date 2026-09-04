# TICKET-357: stats.pages_with_interests mislabeled — counts interest matches, not pages

Status: OPEN
Issue: #552
Module: personal_index/stats.py
Symptom: IndexStats.pages_with_interests is named/labeled as a page count
  (field name "pages_with_interests"; format label "Pages with interests:")
  but the body increments it once per interest match, not once per page.
  A page with 3 matched interests contributes 3, not 1.
Evidence: stats.py line 111-112: `for interest_name in page.matched_interests:`
  then `pages_with_interests += 1` — the increment is inside the per-interest
  loop, so the value is sum(len(page.matched_interests)) over all pages.
Fix: Reword to state the exact semantics (total interest matches across all
  pages, not distinct pages). Change the format label to "Interest matches:".
  Add one behavior test pinning the corrected claim: a single page with 3
  matched interests yields pages_with_interests == 3.
