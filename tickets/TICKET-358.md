# TICKET-358: index.SearchIndex._create_snippet docstring over-promises "highlighting the query terms"

Status: OPEN
Issue: #554
Module: personal_index/index.py
Symptom: _create_snippet docstring says "Create a snippet highlighting the
  query terms." but the body never marks up / highlights any term. It finds
  the first query token in the content, takes a window around it (50 chars
  before, `length` chars after), and truncates with "..." ellipses. No
  markup (no <mark>, no *, no bold) is ever applied to the matched terms.
Evidence: index.py line 183-204: docstring "Create a snippet highlighting
  the query terms." Body: `best_idx = content.lower().find(token)` then
  `snippet = content[start:end]` with only "..." prefix/suffix appended.
  No term is wrapped in any highlight marker.
Fix: Reword the docstring to state the exact behavior: locate the first
  query token in the content and return a window around it (up to 50 chars
  before, `length` chars after), truncated with "..." ellipses when the
  window is clipped; the matched terms are NOT marked up. Add one behavior
  test pinning the corrected claim: the returned snippet contains the raw
  query term text but no highlight markup.
