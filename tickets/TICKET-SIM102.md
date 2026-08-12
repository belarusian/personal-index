# TICKET-SIM102: Nested if statements that can be combined

## Category
SIM102 — Nested if statements that can be combined

## Evidence
5 occurrences across 5 test files:

| File | Line |
|------|------|
| tests/test_exception_handling.py | 24 |
| tests/test_fstring_placeholders.py | 16 |
| tests/test_rss.py | 237 |
| tests/test_ticket57_duplicate_set_element.py | 14 |
| tests/test_ticket99_unused_encoding.py | 19 |

## Impact
Nested `if` statements reduce readability and increase cyclomatic complexity. While not a functional bug, it makes test code harder to scan and maintain.

## Suggestion
Combine nested `if` conditions using `and`. For example:
