# TICKET-97: Undefined name `suppress` in `crawler/robots.py` (F821)

## Title
`suppress` is used but never imported in `personal_index/crawler/robots.py`, causing a `NameError` at runtime

## Evidence
`personal_index/crawler/robots.py:106` uses `suppress(ValueError)` but `suppress` is never imported:
