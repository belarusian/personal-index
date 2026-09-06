# TICKET-525: ContentAPI._create_content docstring + pinning test

Status: RESOLVED

## File
personal_index/content_api.py (def _create_content, line ~165)

## Symptom
ContentAPI._create_content has NO docstring, so its exact dispatch contract is
undocumented. The parallel pipeline has already documented the sibling methods
(_list_content TICKET-523, _get_content TICKET-524) with docstrings + pinning
tests; _create_content is the remaining gap in the content_api doc-drift sweep.

## Evidence
- def _create_content(self, body: str | None) -> tuple[int, dict[str, Any]] has
  no docstring (line ~165).
- Live behavior (verified in code + TestCreateContent):
  - body missing/empty -> (400, {"error": "Request body is required"})
  - body not valid JSON -> (400, {"error": "Invalid JSON in request body"})
  - parsed body not a dict -> (400, {"error": "Request body must be a JSON object"})
  - otherwise builds an item (id from self._next_id, title/description/link/tags
    with defaults, created_at/updated_at), stores it in self._store, and returns
    (201, {"item": <item>}).

## Minimal additive fix
Add a docstring to _create_content stating the exact dispatch contract above,
and add a pinning test (TestCreateContentDocstring525) mirroring the
TestGetContentDocstring524 pattern asserting the key contract phrases
(body, 400, JSON, object, 201, item, store).

## Resolution
- Merged via PR #922 (merge commit a32ce63); issue #921 closed.

## Issue
Issue: #921
