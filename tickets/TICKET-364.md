# TICKET-364

- File: personal_index/search_suggestions.py
- Symptom: class docstring over-promises a data source the code never touches.
- Evidence: line 100 `"""Generates search suggestions from indexed content metadata."""`
  but `__init__` (lines 102-116) takes no index/store handle; it only initializes
  empty lists/dicts. Data is supplied via add_search_history / add_tags /
  add_keywords / record_search, and generate_suggestions (lines 171-197) dispatches
  to exactly four sources: "history", "tags", "keywords", "trending".
- Minimal additive fix: reword the class docstring to state the exact four sources
  the body actually reads (search history, tags, keywords, trending queries), and
  add ONE behavior test pinning the corrected claim against the returned
  suggestions (suggestions drawn from the added sources; empty when nothing added).
- Status: RESOLVED (merged to main ed5bbc1, gh #566 closed)
- Issue: #566
