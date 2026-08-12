# TICKET-PLW1510: `subprocess.run` without explicit `check` argument

## Category
PLW1510 — subprocess.run without explicit check argument

## Evidence
7 occurrences across 5 test files:

| File | Line |
|------|------|
| tests/test_ticket103_import_sorting.py | 35 |
| tests/test_ticket103_sorted_imports.py | 55 |
| tests/test_ticket105_invalid_type.py | 16 |
| tests/test_ticket106_attribute_value_list.py | 11 |
| tests/test_ticket107_missing_stubs.py | 16, 30, 45 |

## Impact
Without `check=True` (or `check=False`), subprocess failures are silently ignored. If a subprocess call fails unexpectedly, the test will not raise an error, potentially masking real issues.

## Suggestion
Add `check=True` to `subprocess.run()` calls where a non-zero exit code should cause the test to fail. Add `check=False` explicitly where the return code is intentionally ignored (e.g., testing failure scenarios).
