# TICKET-270: content_search.py non-dict JSON guard

- Status: RESOLVED
- Module: personal_index/content_search.py
- Class: json.load non-dict guard sweep (8th instance)

## Symptom
`SearchIndex.load_index()` (line ~467) calls `data = _json.load(f)` (line ~471)
then `self._items = data["items"]`. A non-dict JSON value (null / list / number)
crashes with `TypeError` before any field is populated.

## Evidence (reproduced live)
- null    -> TypeError: 'NoneType' object is not subscriptable
- [1,2,3] -> TypeError: list indices must be integers or slices, not str
- 42      -> TypeError: 'int' object is not subscriptable

## Writer type
`SearchIndex.save_index()` (line ~455) writes
`json.dump(data, f, default=str)` where data is a **dict** with keys
`items`, `index`, `term_freq`, `doc_lengths`. Guard expected type = dict.

## Loader return shape
`load_index` mutates the existing `SearchIndex` in place (no return value);
`__init__` already sets `_items`, `_index`, `_term_freq`, `_doc_lengths` to
empty dicts. On a bad file the safe state is the empty index the object already
has. Guard is a plain `return` that leaves the default empty fields (do NOT
reset fields to non-empty values).

## Minimal additive fix
Immediately after `data = _json.load(f)`, add:
    if not isinstance(data, dict):
        return

## Tests
3 regression tests (null / list / number) in tests/test_content_search.py,
mirroring the established pattern.

## Issue: #369 (closed)

## Resolution
- Branch build25/content-search-json-guard, PR #370, squash-merged eae1497 to main, CI green (3 jobs), gh #369 closed.
- 3 regression tests added (null/list/number).
