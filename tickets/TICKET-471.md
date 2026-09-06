# TICKET-471: CSVExporter.get_stats returns inconsistent keys on empty input

## Symptom
`CSVExporter.get_stats([])` returns `{"total_items": 0, "columns": 0}` while `CSVExporter.get_stats(items)` returns `{"total_items": N, "columns": M, "column_names": [...]}`. The empty guard path omits `column_names`, causing KeyError for callers expecting uniform keys.

## Evidence
File: `personal_index/content_export_csv.py`
Method: `CSVExporter.get_stats` (line 196)

Empty path (line 198-200):
## Status
RESOLVED (PR #788, issue #781 closed, merge 2e50480). Canonical ticket for the CSVExporter.get_stats empty-path column_names fix. Duplicate PRs #787 (TICKET-470) and #782 (TICKET-469) closed as redundant in Cycle 103.
