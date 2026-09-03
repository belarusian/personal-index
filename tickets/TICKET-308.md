# TICKET-308: content_api._update_content accepts a non-object JSON body (contract asymmetry with _create_content)

- Status: OPEN
- Module: personal_index/content_api.py
- Defect class: (b) doc/behavior drift — contract asymmetry between sibling handlers
- Issue: #450

## Symptom
`ContentAPI._create_content` (content_api.py:99) rejects a non-object JSON body with
`400 {"error": "Request body must be a JSON object"}` (lines 106-107). The sibling
`_update_content` (content_api.py:122) parses the body with `json.loads` (line 128)
then iterates `for key in (...): if key in data` (lines 132-133) on whatever
`json.loads` returned, with NO equivalent `isinstance(data, dict)` guard.

## Evidence (verified at runtime, cycle 64)
- `PUT /api/v1/content/1` body `["x"]`  -> 200, item unchanged (silent no-op; contract violation).
- `PUT /api/v1/content/1` body `["title"]` -> raw `TypeError: list indices must be integers or slices, not str` (content_api.py:134).
- `PUT /api/v1/content/1` body `123` -> raw `TypeError: argument of type 'int' is not iterable` (content_api.py:133).

## Fix (minimal, additive)
In `_update_content`, after the `json.loads` try/except block and before the
`item = self._store[item_id]` line, add:
    if not isinstance(data, dict):
        return 400, {"error": "Request body must be a JSON object"}
mirroring `_create_content`. Add regression test `test_update_not_dict`.
