# TICKET-526: ContentAPI._update_content missing docstring

- Issue: #923
- File: personal_index/content_api.py (def _update_content, line ~199)
- Symptom: `_update_content` has no docstring; its exact dispatch contract is
  not documented, unlike its siblings _create_content (525), _get_content (524),
  _list_content (523).
- Evidence: `sed -n '199,216p' personal_index/content_api.py` shows the def
  body with no docstring; tests/test_content_api.py TestUpdateContent pins the
  behavior (200/404/400) but no docstring pinning test exists.
- Minimal additive fix: add a docstring stating the exact dispatch contract:
  404 not-found when item_id not in self._store; 400 "Request body is
  required" when body missing/empty; 400 "Invalid JSON in request body" when
  body is not valid JSON; 400 "Request body must be a JSON object" when parsed
  body is not a dict; otherwise partial-update title/description/link/tags
  present in data, refresh updated_at to now(UTC).isoformat(), return
  (200, {"item": item}). Add a pinning test (TestUpdateContentDocstring526)
  asserting the key contract phrases are present.
- Status: OPEN
