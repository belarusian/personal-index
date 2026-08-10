# TICKET-82: NameError — `suppress` is not defined in `personal_index/crawler/robots.py`

## Title
`suppress` used but never imported in `personal_index/crawler/robots.py` — will raise `NameError` at runtime

## Evidence
File: `personal_index/crawler/robots.py`
Line 106: `with suppress(ValueError):`

The `suppress` context manager from `contextlib` is used on line 106 to handle `ValueError` when parsing `crawl-delay`, but it is never imported. The imports at the top of the file (lines 5-8) only include:
- `fnmatch`
- `dataclasses`
- `typing`
- `urllib.parse`

mypy confirms: `personal_index/crawler/robots.py:106: error: Name "suppress" is not defined  [name-defined]`

## Impact
Any code path that encounters a non-numeric `crawl-delay` value in a robots.txt file will crash with `NameError: name 'suppress' is not defined`. This affects the `parse_robots_txt()` function which is called by the crawler's robots.txt handling.

## Suggestion
Add `from contextlib import suppress` to the imports at the top of `personal_index/crawler/robots.py` (line 5 area).
