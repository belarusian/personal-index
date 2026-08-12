# TICKET-DTZ005: `datetime.datetime.now()` called without `tz` argument

## Category
DTZ005 — datetime.now() called without tz argument

## Evidence
9 occurrences across 2 test files:

| File | Line |
|------|------|
| tests/test_content_notifications.py | 60, 210, 223, 225 |
| tests/test_content_scoring.py | 116, 121, 149, 155, 160 |

## Impact
`datetime.now()` without a `tz` argument returns a naive datetime tied to the local system timezone. Tests using this may produce non-deterministic results across machines or CI environments with different timezone settings.

## Suggestion
Replace `datetime.now()` with `datetime.now(datetime.timezone.utc)` in all affected lines. This ensures timezone-aware, deterministic test behavior.
