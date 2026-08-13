# TICKET-234: Fix bare exception in pipeline.py:101 (BLE001)

**File:** `personal_index/pipeline.py`, line 101
**Error:** `except Exception as e` without noqa suppression

## What's Wrong

Bare `Exception` catch violates BLE001. Either use specific exception types or add `# noqa: BLE001` with justification.

## Suggestion

Read the context at lines 95-110. If this is a generic step handler that must survive any error, add `# noqa: BLE001` with comment explaining why. Otherwise narrow to specific exceptions.
