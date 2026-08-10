# TICKET-86: Type error — `tarfile.open()` mode `'w'` and `'r'` not accepted by mypy overloads

## Title
`tarfile.open()` calls use mode strings `'w'` and `'r'` that don't match mypy's expected literal types

## Evidence
File: `personal_index/backup.py`
Line 90: `with tarfile.open(str(archive_path), mode) as tar:` where `mode` is `"w:gz"` or `"w"`
Line 158: `with tarfile.open(str(archive_path), mode) as tar:` where `mode` is `"r:gz"` or `"r"`

mypy flags both lines with `[call-overload]` errors because the `mode` variable is typed as `str` rather than a `Literal['w', 'w:gz', 'r', 'r:gz', ...]`.

## Impact
Static type checking fails. Runtime behavior is correct since the mode values are valid, but mypy can't verify this because the variable is dynamically assigned.

## Suggestion
Either:
1. Add a type annotation: `mode: Literal["w", "w:gz", "r", "r:gz"]`
2. Or use `typing.cast()` to narrow the type at the call site
3. Or inline the mode string directly in the `tarfile.open()` call
