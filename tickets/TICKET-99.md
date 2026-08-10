# TICKET-99: Broad exception handling — `except Exception` in crawler modules without logging

## Title
`crawler/__init__.py` and `crawler/main.py` catch `Exception` broadly and silently return `None`, not covered by TICKET-48

## Evidence
TICKET-48 lists 12 locations with broad `except Exception` handling, but misses these two in the crawler module:

1. `personal_index/crawler/__init__.py:114` — bare `except Exception: return None`
