# TICKET-RUF012: Mutable default value for class attribute

## Category
RUF012 — Mutable default value for class attribute

## Evidence
1 occurrence:

| File | Line |
|------|------|
| tests/test_cli_core.py | 85 |

The class attribute `EXPECTED_COMMANDS` is a mutable list defined at class level (line 85–91).

## Impact
Mutable class attributes are shared across all instances of the class. If any test modifies `EXPECTED_COMMANDS` (e.g., via `.append()` or `.remove()`), the change persists across test methods, causing flaky or incorrect test results.

## Suggestion
Annotate with `typing.ClassVar[list[str]]` to signal intent, or convert to a tuple (`EXPECTED_COMMANDS: tuple[str, ...] = (...)`) if the list is never mutated. If mutation is needed, initialize in `__init__` instead.
