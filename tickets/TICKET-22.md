# TICKET-22: Duplicate `InterestStore` classes in `interests.py` and `interest_store.py`

## Title
Two `InterestStore` classes with different APIs and storage formats

## Evidence
Two distinct `InterestStore` classes:

1. **`personal_index/interests.py:48`** — `InterestStore` with `store_path: str | None`, stores `Dict[str, Interest]` (dict keyed by name), uses `interests.py:Interest`
2. **`personal_index/interest_store.py:26`** — `InterestStore` with `storage_path: str` (required), stores `List[Interest]`, uses `models.py:Interest`

Import usage:
- `interests.py` InterestStore: imported by `cli.py:8`, `formatter.py:8`
- `interest_store.py` InterestStore: imported by `crawler/__init__.py:18`, `crawler/main.py:12`, `stats.py:9`, `content_filter.py:9`, `scheduler.py:12`

## Impact
- CLI and core crawler use different InterestStore implementations
- Data stored by one cannot be read by the other (dict vs list format)
- Adding an interest via CLI won't be visible to the crawler

## Suggestion
1. Consolidate into a single `InterestStore` in `personal_index/interest_store.py`
2. Use `models.py:Interest` as the canonical model
3. Update `cli.py` and `formatter.py` to import from `interest_store.py`
4. Remove `InterestStore` from `interests.py`
