# TICKET-74: Unnecessary generator — rewrite as set comprehension (C401)

## Title
`set()` wrapping a generator expression should be rewritten as a set comprehension

## Evidence
ruff C401 flags 4 locations:

1. `personal_index/analytics.py:173` — `set(x for x in ...)`
2. `personal_index/content_timeline/timeline.py:110` — `set(x for x in ...)`
3. `personal_index/dashboard/views.py:183` — `set(x for x in ...)`
4. `personal_index/url_history.py:110` — `set(x for x in ...)`

Example from `personal_index/analytics.py:173`:
