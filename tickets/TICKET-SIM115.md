# TICKET-SIM115: `open()` without context manager

## Category
SIM115 — open() without context manager

## Evidence
4 occurrences across 3 test files:

| File | Line |
|------|------|
| tests/test_backup.py | 124 |
| tests/test_ticket55_importlib_util.py | 7 |
| tests/test_ticket57_duplicate_set_element.py | 7, 28 |

## Impact
Files opened without a context manager (`with` statement) are not guaranteed to be closed promptly. This can lead to file descriptor leaks, especially in test suites that run many tests. On some platforms (e.g., Windows), unclosed files can cause permission errors on subsequent operations.

## Suggestion
Wrap every `open()` call in a `with` statement:
