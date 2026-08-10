# TICKET-23: Duplicate `IndexedPage` dataclasses in `index.py` and `models.py`

## Title
Two `IndexedPage` dataclasses with different field schemas

## Evidence
Two distinct `IndexedPage` classes:

1. **`personal_index/models.py:198`** — Has `url`, `title`, `content`, `keywords`, `matched_interests`, `crawled_at: str`, `domain`, `status_code`, `content_length`, `language`
2. **`personal_index/index.py:30`** — Has `url`, `title`, `content`, `keywords`, `score`, `indexed_at`, `source_interest`, `word_count` — completely different fields

Import usage:
- `models.py` IndexedPage: imported by `storage.py:5`
- `index.py` IndexedPage: imported by `formatter.py:7`, used internally by `index.py`'s own `SearchIndex`

## Impact
- `storage.py` and `index.py` cannot share page data
- Different persistence schemas mean data written by one is unreadable by the other
- `index.py`'s `IndexedPage` has `score` and `word_count` fields that `models.py`'s version lacks

## Suggestion
1. Merge fields from both into a single `IndexedPage` in `models.py`
2. Remove `IndexedPage` from `index.py`
3. Update `formatter.py` to import from `models.py`
