# TICKET-395

- Status: RESOLVED (merged to main 49f77ba via PR #629, gh #628 closed)
- Issue: #628
- Class: (b) doc-drift (placeholder docstring over-promise)
- File: personal_index/importer.py
- Function: `Importer._import_csv` (line 129)
- Symptom: docstring `"""Import from CSV format."""` is a single-line generic
  placeholder; it does not enumerate the actual sub-components / behavior.
- Evidence line: `personal_index/importer.py:130` -> `"""Import from CSV format."""`
- Minimal additive fix: reword the docstring to state the exact behavior
  (DictReader row iteration; per-row Bookmark built with case-insensitive
  header fallback url/URL, title/Title, description/Description,
  category/Category defaulting to "imported", tags comma-split+stripped,
  favorite/Favorite lowercased == "true"; manager.add when url non-empty else
  total_skipped; per-row (ValueError, TypeError) appended to result.errors and
  loop continues; returns ImportResult). Add ONE pinning test asserting the
  case-insensitive header fallback + multi-tag comma-splitting against the
  returned Bookmark objects (a sub-component existing tests do not cover).
- Note: `tests/test_exception_handling.py::test_csv_import_catches_specific_exceptions`
  locates the except block via `_method_line_span(source, "_import_csv")`, so a
  docstring that adds lines is safe (the except block stays inside the span).
