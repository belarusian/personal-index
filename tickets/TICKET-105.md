# TICKET-105: Missing `suppress` import in `personal_index/crawler/robots.py`

## Title
`contextlib.suppress` is used but never imported, causing `NameError` at runtime

## Evidence
**File:** `personal_index/crawler/robots.py:106`
