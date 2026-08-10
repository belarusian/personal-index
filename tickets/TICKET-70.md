# TICKET-70: Nested `if` statements that can be flattened (SIM102)

## Title
Multiple modules have nested `if` statements that can be combined into a single `if` with `and`

## Evidence
ruff SIM102 flags 6 locations:

1. `personal_index/api/rate_limit_middleware.py:29` — nested `if`
2. `personal_index/auth/sessions.py:168` — nested `if`
3. `personal_index/content_tagger/detector.py:138` — nested `if`
4. `personal_index/crawler/robots.py:50` — nested `if`
5. `personal_index/crawler/robots.py:152` — nested `if`
6. `personal_index/robots_parser.py:52` — nested `if`

Example pattern:
