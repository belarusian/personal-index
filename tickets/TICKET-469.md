# TICKET-469: CSVExporter.get_stats returns inconsistent keys on empty input

## Symptom
`CSVExporter.get_stats([])` returns `{"total_items": 0, "columns": 0}` while `CSVExporter.get_stats(items)` returns `{"total_items": N, "columns": M, "column_names": [...]}`. The empty guard path omits `column_names`, causing KeyError for callers expecting uniform keys.

## Evidence
File: `personal_index/content_export_csv.py`
Method: `CSVExporter.get_stats` (line 196)

Empty path (line 198-200):