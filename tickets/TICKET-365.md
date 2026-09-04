# TICKET-365: content_reader.ContentReader class docstring "indexed content" over-promise

Status: OPEN
Issue: #568
Module: personal_index/content_reader.py
Class: (b) doc-drift (docstring over-promise)

## Symptom
The `ContentReader` class docstring (line 55) reads:
    "Reader for navigating and browsing indexed content."
The phrase "indexed content" names a data SOURCE the code never touches.

## Evidence
- `__init__` (lines 61-63) takes NO index/store handle; it only initializes
  `self._items: list[ReadResult] = []` and `self._url_index: dict[str, ReadResult] = {}`.
- Data is supplied manually via `add(item)` / `add_many(items)` (lines 65-73).
- There is no index object, no store, no crawler handle anywhere in the class.
- All other class docstrings (paginate, filter_by_tags, filter_by_score,
  search_titles, search_content, format_item, format_page) accurately describe
  the methods; only the class-level "indexed content" phrase over-promises.

## Minimal additive fix
Reword the class docstring to state the exact mechanism the body performs:
    "Reader for navigating and browsing content items added via add/add_many.

    Provides pagination, filtering by tags/score, and formatting
    options for displaying content."
Add ONE behavior test pinning the corrected claim against the returned object:
a fresh ContentReader is empty (count == 0, list_all() == []) and only surfaces
items that were added via add/add_many (list_all() returns exactly the added
URLs). This witnesses the "added via add/add_many" claim, not just the reword.
