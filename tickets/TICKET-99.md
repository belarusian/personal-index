# TICKET-99: Unused unpacked variable `encoding` in `content_type.py` (RUF059)

## Title
Three unpacked `encoding` variables are never used in `personal_index/content_type.py`

## Evidence
ruff RUF059 flags 3 locations where `encoding` is unpacked from `mimetypes.guess_type()` but never used:

1. `personal_index/content_type.py:98` — `mime_type, encoding = mimetypes.guess_type(url)`
2. `personal_index/content_type.py:124` — `mime_type, encoding = mimetypes.guess_type(filename)`
3. `personal_index/content_type.py:190` — `mime_type, encoding = mimetypes.guess_type(f"file{ext}")`

In all three cases, only `mime_type` is used. The `encoding` return value is discarded.

## Impact
Low — no runtime error. But it signals intent mismatch (the code unpacks a value it doesn't need) and triggers linter warnings.

## Suggestion
Replace the two-tuple unpacking with a pattern that discards the unused value:
