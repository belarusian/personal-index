# TICKET-214: Duplicate export functionality

## Evidence
- `personal_index/export.py`: Exports bookmarks via BookmarkManager to JSON/CSV/HTML/XML/MD/OPML
- `personal_index/content_exporter.py`: Exports content items to HTML/JSON/Markdown/RSS
- Both have format mapping dictionaries (EXTENSION_MAP vs SUPPORTED_FORMATS)
- Both implement JSON and HTML export handlers

## Impact
- Maintenance burden: changes to export logic must be applied in two places
- Confusion for developers choosing which module to use
- Potential inconsistency in exported formats

## Suggestion
Consolidate into a single export module with pluggable format handlers.
