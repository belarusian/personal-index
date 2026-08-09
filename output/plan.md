# bookmark_export Implementation Plan

## Batch 1: Tests + Module Skeleton
- Create `tests/test_bookmark_export.py` with all tests
- Create `personal_index/bookmark_export.py` with minimal implementation
- Tests should fail initially (TDD)

## Batch 2: JSON Exporter
- Implement `export_json()` method
- Run tests, verify JSON tests pass

## Batch 3: HTML Exporter  
- Implement `export_html()` method with Netscape format
- Run tests, verify HTML tests pass

## Batch 4: OPML Exporter
- Implement `export_opml()` method with OPML 2.0 format
- Run tests, verify OPML tests pass

## Batch 5: Export dispatch + file writing
- Implement `export()` method with format dispatch and file writing
- Implement `BookmarkExportResult` dataclass
- Run all tests, verify everything passes
- Commit and signal PR_GATE
