# TICKET-31: Type error — `storage.py` passes `list | dict` to `CrawlConfig.from_dict()` expecting `dict`

## Title
`storage.py._read_json()` returns `list | dict`, but callers pass it directly to `from_dict()` without type narrowing

## Evidence
In `personal_index/storage.py:28-34`:
