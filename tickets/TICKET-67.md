# TICKET-67: Redundant exception object in logging.exception call (TRY401)

## Title
Redundant exception object passed to `logging.exception` in `personal_index/api/handlers.py`

## Evidence
ruff TRY401 flags 1 location:

1. `personal_index/api/handlers.py:41` — `logger.exception("Unhandled exception: %s", exc)`
