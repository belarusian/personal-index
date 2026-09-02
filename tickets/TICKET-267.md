# TICKET-267: Unguarded non-dict JSON load in TagStore._load

## Status: RESOLVED

## File
personal_index/tags.py

## Symptom
`TagStore._load()` crashes with `AttributeError` when the storage file contains
valid JSON that is not a dict (e.g. `null`, `[1,2,3]`, `42`).

## Evidence
- Line 54: `data = json.load(f)`
- Line 55: `data.get("tags", {})` — raises AttributeError if data is None/list/int
- Line 68: `except (json.JSONDecodeError, KeyError, TypeError)` — does NOT catch AttributeError

## Fix
Add `if not isinstance(data, dict): self._tags = {}; self._page_tags = {}; return`
immediately after `data = json.load(f)`.

Add 3 regression tests: test_null_storage_resets_to_empty, test_list_storage_resets_to_empty,
test_number_storage_resets_to_empty.

## Issue: #363
