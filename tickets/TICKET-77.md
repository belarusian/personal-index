# TICKET-77: Use `any()` instead of manual for-loop with early return (SIM110)

## Title
Multiple functions use a `for` loop with early `return True` that can be replaced with `any()`

## Evidence
ruff SIM110 flags 11 locations:

1. `personal_index/content_enricher.py:124` — for-loop checking regex patterns
2. `personal_index/content_filter.py:109` — for-loop checking blocked patterns
3. `personal_index/content_filter.py:117` — for-loop checking required patterns
4. `personal_index/filter/engine.py:112` — for-loop checking URL patterns
5. `personal_index/rss.py:258` — for-loop checking XML patterns
6. `personal_index/url_filter.py:69` — for-loop checking blacklist rules
7. `personal_index/url_utils.py:386` — for-loop checking excluded extensions
8. `personal_index/validator.py:109` — for-loop checking blocked paths

## Impact
- `any()` is more Pythonic and concise
- Reduces boilerplate and improves readability
- Single expression is easier to reason about than a loop with early return

## Suggestion
Replace:
