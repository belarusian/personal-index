# TICKET-268: Unguarded non-list JSON load in BookmarkManager.load

## Status: RESOLVED

## File
personal_index/bookmarks.py

## Symptom
`BookmarkManager.load()` crashes when the storage file contains valid JSON that
is not a list (e.g. `null`, `{"key": "val"}`, `42`). `save()` writes a JSON list,
so `load()` expects one; a corrupted or hand-edited file breaks the
`for item in data:` loop (TypeError for None/int, AttributeError for dict).

## Evidence
- Line 157: `data = json.load(f)`
- Line 159: `for item in data:` — assumes list
- Same class as TICKET-265 (scheduler.py), TICKET-266 (content_pin.py), TICKET-267 (tags.py)

## Fix
Add `if not isinstance(data, list): return 0` immediately after
`data = json.load(f)`.

Add 3 regression tests: test_load_null_json, test_load_dict_json,
test_load_number_json.

## Issue: #365
