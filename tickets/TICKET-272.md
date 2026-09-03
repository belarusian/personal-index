# TICKET-272

- Status: RESOLVED
- Module: personal_index/search_index.py
- Class: json.load non-dict/non-list guard sweep

## Symptom
`SearchIndex._load()` crashes on a non-dict JSON index file (null / list / number).
The writer `_save()` writes a **dict** `{"pages": {...}, "word_index": {...}}`, but
`_load()` calls `data.get("pages", {})` on whatever `json.load` returns. A null,
list, or number file raises `AttributeError: '<type>' object has no attribute 'get'`
during `SearchIndex.__init__` (via `__post_init__` -> `_load`).

## Evidence
- personal_index/search_index.py:40  `data = json.load(f)`
- personal_index/search_index.py:42  `for url, page_data in data.get("pages", {}).items():`
- personal_index/search_index.py:71  `json.dump(data, f, indent=2)` (writer writes a dict)
- Reproduced live: null -> AttributeError 'NoneType' object has no attribute 'get';
  [1,2,3] -> AttributeError 'list' object has no attribute 'get';
  42 -> AttributeError 'int' object has no attribute 'get'.

## Loader return shape
`_load(self) -> None` mutates `self._pages` / `self._word_index` in place (store-mutating).
Both fields already default to empty dicts via `field(default_factory=dict)`.
Safe default on a bad file = the empty index the object already has -> plain `return`.

## Minimal additive fix
Add `if not isinstance(data, dict): return` immediately after `data = json.load(f)`.

## Tests
3 regression tests (null / list / number) in tests/test_search_index.py:
store pointed at a tmp_path file, construct SearchIndex, assert count() == 0.

## Issue
Issue: #373
