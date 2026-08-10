# TICKET-71: `try`-`except`-`pass` that should use `contextlib.suppress` (SIM105)

## Title
Multiple modules use `try`-`except`-`pass` blocks that should use `contextlib.suppress`

## Evidence
ruff SIM105 flags 7 locations:

1. `personal_index/content_filter.py:45` — `try`-`except`-`pass` for `re.error`
2. `personal_index/content_priority.py:281` — `try`-`except`-`pass` for `IndexError`
3. `personal_index/crawler/robots.py:107` — `try`-`except`-`pass` for `ValueError`
4. `personal_index/filter/engine.py:41` — `try`-`except`-`pass` for `re.error`
5. `personal_index/interests.py:105` — `try`-`except`-`pass` for `re.error`
6. `personal_index/robots_parser.py:115` — `try`-`except`-`pass` for `ValueError`
7. `personal_index/sitemap.py:133` — `try`-`except`-`pass` for `ValueError`

Example from `personal_index/content_filter.py:45`:
