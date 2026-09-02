# TICKET-266

Status: RESOLVED
Module: personal_index/content_pin.py
Class: non-dict JSON guard (defect class of TICKET-262/263/264/265)

## Symptom
`ContentPinner._load` (line ~53) does `data = json.load(f)` then `data.items()`
(line ~56) without checking `data` is a dict. The `except` clause catches
`(json.JSONDecodeError, KeyError, TypeError)` but NOT `AttributeError`.

Writing `null`, `[1,2,3]`, or `42` to the storage file and instantiating
`ContentPinner(storage_path=...)` raises
`AttributeError: 'NoneType'/'list'/'int' object has no attribute 'items'`.

## Evidence (reproduced live, cycle 21)
- null RAISES AttributeError 'NoneType' object has no attribute 'items'
- list RAISES AttributeError 'list' object has no attribute 'items'
- number RAISES AttributeError 'int' object has no attribute 'items'

## Minimal additive fix
Immediately after `data = json.load(f)`, add:
    if not isinstance(data, dict):
        self._pinned = {}
        return
Add 3 regression tests mirroring tests/test_scheduler.py (cycle 20):
test_null_storage_resets_to_empty, test_list_storage_resets_to_empty,
test_number_storage_resets_to_empty.

Issue: #361
