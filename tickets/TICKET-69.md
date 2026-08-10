# TICKET-69: Duplicate if-branches that can be combined with `or` (SIM114)

## Title
Multiple modules have consecutive `if` branches with identical bodies that can be combined using logical `or`

## Evidence
ruff SIM114 flags 2 locations:

1. `personal_index/annotation.py:180` — two `if` branches with identical body
2. `personal_index/search_facets/faceted_search.py:78` — two `if` branches with identical body

Example from `personal_index/annotation.py:180`:
