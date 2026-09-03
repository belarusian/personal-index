# TICKET-323: bookmark_export.export_to_file return annotation over-promises None path

**Status:** OPEN
**Module:** personal_index/bookmark_export.py
**Issue:** #483

## Symptom
`BookmarkExporter.export_to_file` is annotated `-> BookmarkExportResult | None`,
implying a possible None return. But the docstring states the actual contract:
'A BookmarkExportResult on success, or a result with errors on failure' — it never
returns None. All body return paths return a BookmarkExportResult; there is no
`return None`.

## Evidence
- Line 166: `def export_to_file(self, path: Path, fmt: str | None = None) -> BookmarkExportResult | None:`
- Body: every return statement returns a `BookmarkExportResult(...)` instance.
- No `return None` in the function body.

## Minimal Fix
1. Change return annotation from `BookmarkExportResult | None` to `BookmarkExportResult`.
2. Add regression test asserting the return type is `BookmarkExportResult` (not None).

## Scope
- personal_index/bookmark_export.py (annotation only)
- tests/test_bookmark_export.py (1 regression test)
