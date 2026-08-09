# bookmark_export Module Analysis

## Existing Code
- `personal_index/bookmarks.py`: Bookmark dataclass + BookmarkManager
- `personal_index/export.py`: General Exporter with JSON, CSV, HTML, XML, Markdown, OPML

## Gap
No dedicated `bookmark_export` module exists. The existing `export.py` is a general-purpose
exporter. We need a focused `bookmark_export` module with clean APIs for HTML, JSON, and OPML.

## Design
- `BookmarkExportResult` dataclass for tracking export results
- `BookmarkExporter` class with three dedicated exporters:
  - `export_json()` -> str (JSON array of bookmark dicts)
  - `export_html()` -> str (Netscape HTML bookmark format)
  - `export_opml()` -> str (OPML 2.0 format)
- `export()` method that dispatches by format and can write to file
- Works with `Bookmark` objects directly (list of bookmarks)
- Supports category-based grouping in HTML and OPML

## Test Strategy
1. Test BookmarkExportResult dataclass defaults and fields
2. Test JSON export: content, structure, empty, special chars
3. Test HTML export: DOCTYPE, structure, escaping, empty
4. Test OPML export: XML declaration, structure, escaping, empty
5. Test export() dispatch and file writing
6. Test unsupported format handling
