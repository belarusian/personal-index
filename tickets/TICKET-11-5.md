# TICKET-11-5: Extract helpers from `content_type.ContentTypeDetector.detect_from_extension` (59L → ~25L)

## File
`personal_index/content_type.py`, lines 137–195

## Evidence

The `detect_from_extension` method performs three distinct logical phases:

1. **Cache lookup** (lines 144–148): Checks `_mime_cache` for a cached result by normalized extension key.
2. **MIME type resolution** (lines 150–156): Uses `mimetypes.guess_type()` to resolve the extension to a MIME type, falling back to `"application/octet-stream"`.
3. **Category classification + flag computation** (lines 158–193): Determines the category by checking against `TEXT_EXTENSIONS`, `DOCUMENT_EXTENSIONS`, `MEDIA_EXTENSIONS`, `ARCHIVE_EXTENSIONS` sets, then falls back to `CATEGORY_MAP` prefix matching, then constructs the `ContentTypeInfo` with boolean flags (`is_text`, `is_media`, `is_document`), and caches the result.

The category classification block (lines 158–180) is the largest sub-task: it checks 4 extension sets sequentially, then falls back to MIME-based classification via `self.classify()`. The flag computation (lines 182–190) is a separate concern from the category determination.

## Impact

- The method mixes caching, MIME resolution, category classification, and flag computation — four concerns in one method.
- The category-from-extension logic (checking 4 sets) is duplicated in spirit by `self.classify()` which does MIME-based classification.
- Adding a new category requires modifying the method body (open/closed violation).

## Suggestion

Extract two private helpers:

### Helper 1: `_resolve_mime_type`
