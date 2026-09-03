# TICKET-308: content_api._update_content accepts a non-object JSON body (contract asymmetry with _create_content)

- Status: OPEN
- Module: personal_index/content_api.py
- Issue: #450

## Symptom
`ContentAPI._update_content` (line 122) parses the request body with
`json.loads` (line 128) and then iterates `for key in (...): if key in data`
(lines 132-133) on whatever `json.loads` returned. If the body is a JSON
*list* (not an object), `key in data` is a list membership test, not a dict
key test:
- body `["title"]` -> `key in data` is False for every key -> the loop
  silently no-ops -> returns **200** with the item unchanged (a contract
  violation: the caller sent a non-object body and got success).
- body `["title", "x"]` -> `key in data` is True for `"title"` ->
  `item["title"] = data["title"]` indexes a *list* with a string -> raw
  `TypeError` traceback escapes.

`_create_content` (line 99) already rejects a non-object body with
`if not isinstance(data, dict): return 400, {"error": "Request body must be a
JSON object"}` (lines 106-107). `_update_content` has no equivalent guard, so
the two endpoints disagree on the request-body contract for the same
non-object input.

## Evidence
- `personal_index/content_api.py:106-107` - `_create_content` rejects a
  non-dict body with 400 "Request body must be a JSON object".
- `personal_index/content_api.py:128-133` - `_update_content` does
  `data = json.loads(body)` then `for key in (...): if key in data:` with NO
  `isinstance(data, dict)` guard.
- `tests/test_content_api.py:88-90` - `test_create_not_dict` asserts the
  create-side 400 for a list body; there is NO `test_update_not_dict`, so the
  update-side asymmetry is untested.

## Fix (minimal, additive, one function)
Add the same guard to `_update_content` immediately after the
`json.loads`/`except json.JSONDecodeError` block (after line 130):
`if not isinstance(data, dict): return 400, {"error": "Request body must be a
JSON object"}`. This makes `_update_content` reject a non-object body exactly
the way `_create_content` already does. No signature/return-type change, no
new module, no CLI/exit-code change. Add `test_update_not_dict` (list body ->
400) mirroring `test_create_not_dict`.
