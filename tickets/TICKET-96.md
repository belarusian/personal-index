# TICKET-96: Dead code — duplicate `tokenize()` functions in `content.py` and `utils/__init__.py`

## Title
Two unused `tokenize()` functions exist as duplicates of `personal_index.text_utils.tokenize`

## Evidence
Three `tokenize` functions exist in the codebase:

1. `personal_index/text_utils.py:305` — `tokenize(text, lowercase=True, remove_stopwords=False)` — **ACTIVE** (imported by keyword_extractor, content_categorizer, content_enricher, tfidf)
2. `personal_index/content.py:129` — `tokenize(text)` — **DEAD** (never imported anywhere)
3. `personal_index/utils/__init__.py:65` — `tokenize(text)` — **DEAD** (exported in `__all__` but never imported)

The dead versions use slightly different regex patterns:
- `content.py`: `r'[a-z0-9]+'` (simpler, no hyphen support)
- `utils/__init__.py`: `r'[a-z0-9]+(?:-[a-z0-9]+)*'` (supports hyphenated words)
- `text_utils.py`: `r"\b[a-zA-Z0-9_]{2,}\b"` (requires 2+ chars, includes underscores)

## Impact
Dead code increases maintenance burden and confusion. Developers may accidentally import the wrong `tokenize` function, getting different tokenization behavior.

## Suggestion
1. Remove `tokenize()` from `personal_index/content.py` (lines 129-133)
2. Remove `tokenize()` from `personal_index/utils/__init__.py` (lines 65-69) and remove it from `__all__` (line 107)
3. Ensure all consumers use `personal_index.text_utils.tokenize` as the canonical implementation
