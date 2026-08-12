# TICKET-215: Duplicate bookmark export functionality

## Evidence
- `personal_index/bookmark_export.py`: BookmarkExportResult dataclass, _EXPORT_MAP, exports to JSON/HTML/OPML
- `personal_index/export.py`: ExportResult dataclass, EXTENSION_MAP, exports to JSON/CSV/HTML/XML/MD/OPML
- Near-identical format mapping and export logic for bookmarks

## Impact
- Redundant code paths for the same operation
- Risk of divergent behavior between the two modules

## Suggestion
Merge bookmark_export.py into export.py or vice versa.
