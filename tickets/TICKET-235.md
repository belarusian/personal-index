# TICKET-235: Fix bare exception in api/handlers.py:40 (BLE001)

**File:** `personal_index/api/handlers.py`, line 40
**Error:** `except Exception as exc` without noqa suppression

## Suggestion

Read context. If this is an HTTP error handler that must return 500 on any failure, add `# noqa: BLE001`. Otherwise narrow to specific exceptions.
