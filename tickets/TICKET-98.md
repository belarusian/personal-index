# TICKET-98: E741 — Ambiguous variable name `l` in `rss.py`

## Title
Variable name `l` (lowercase L) used in for-loops in `rss.py`, easily confused with `1` (one) or `I` (uppercase i)

## Evidence
File: `personal_index/rss.py`

Line 162: `for l in links:` — inside `_parse_atom_feed()`
