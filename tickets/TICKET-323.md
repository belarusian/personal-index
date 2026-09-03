# TICKET-323: bookmark_export.BookmarkExporter.export_to_file return annotation over-promises a None path

- Status: OPEN
- Issue: #483
- Module: personal_index/bookmark_export.py
- Class: (b) doc/behavior drift — return annotation over-promises a None path the code never honors

## Symptom
`BookmarkExporter.export_to_file` is annotated `-> BookmarkExportResult | None`,
implying a possible `None` return. But the docstring states the actual contract:
"A BookmarkExportResult on success, or a result with errors on failure" — it never
returns None. The body confirms it: all four return paths return a
`BookmarkExportResult` (unsupported-format, export-failed, and success). There is
no `return None` anywhere in the function. The `| None` in the annotation is the
drift; it promises a None path the code does not honor.

## Evidence
- personal_index/bookmark_export.py `export_to_file`:
    - annotation: `-> BookmarkExportResult | None`
    - docstring: "A BookmarkExportResult on success, or a result with errors on failure."
    - body return paths (all return a BookmarkExportResult):
        1. `return BookmarkExportResult(errors=[f"Unsupported format: {fmt}"])`
        2. `return BookmarkExportResult(errors=[f"Export failed for format: {fmt}"])`
        3. `return BookmarkExportResult(format=fmt, bookmark_count=..., output_path=filepath)`
    - `grep 'return None'` in the function body: no match.
- Verified at runtime: unsupported-format path and success path both return a
  `BookmarkExportResult` (never None).

## Fix
Correct the return annotation from `BookmarkExportResult | None` to
`BookmarkExportResult` to match the actual contract (always returns a result;
errors are reported via the result's `errors` field, never via None). Add a
regression test pinning the corrected contract (unsupported-format and success
paths both return a `BookmarkExportResult`, never None). No behavior change.
