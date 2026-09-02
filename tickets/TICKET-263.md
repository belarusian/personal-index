# TICKET-263: InterestStore._load crashes on non-dict JSON (null/list/number)

**Status:** OPEN
**Module:** personal_index/interests.py
**Issue:** #355

## Symptom
`InterestStore._load` (line 33-39) calls `json.load(f)` and immediately uses
`data.items()` on line 35. The except clause catches
`(json.JSONDecodeError, KeyError, TypeError)` but NOT `AttributeError`.

## Evidence
- Writing `null` to the storage file → `AttributeError: 'NoneType' object has no attribute 'items'`
- Writing `[1, 2, 3]` → `AttributeError: 'list' object has no attribute 'items'`
- Writing `42` → `AttributeError: 'int' object has no attribute 'items'`

## Fix
Add `if not isinstance(data, dict): self._interests = {}; return` after
`json.load(f)` in `_load`.

## Regression tests
- test_load_null_json
- test_load_list_json
- test_load_number_json
