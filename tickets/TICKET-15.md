# TICKET-15: Broken import in export.py — `from bookmarks import Bookmark`

## Title
`personal_index/export.py` imports `Bookmark` from `.bookmarks` but never uses it; `os` and `Dict` are also unused

## Evidence
`personal_index/export.py` (lines 7, 12, 14):
