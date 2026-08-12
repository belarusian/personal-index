# TICKET-SIM117: Nested `with` statements that can be combined

## Category
SIM117 — Nested with statements that can be combined

## Evidence
5 occurrences, all in one test file:

| File | Line |
|------|------|
| tests/test_webhook.py | 126, 176, 194, 212, 230 |

Each occurrence nests two `with` statements (typically `patch` + `patch` or `patch` + `pytest.raises`).

## Impact
Nested `with` statements increase indentation depth and reduce readability. While functionally correct, combining them with a tuple context manager produces cleaner, more maintainable code.

## Suggestion
Combine nested `with` statements using a tuple:
