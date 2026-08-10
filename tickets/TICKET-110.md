# TICKET-110: Code quality — `CacheDecorator` cannot cache `None` return values

## Title
`personal_index/cache.py`'s `CacheDecorator` fails to cache functions returning `None`

## Evidence
File: `personal_index/cache.py`, lines 237-245
