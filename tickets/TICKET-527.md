# TICKET-527: Add ContentAPI._delete_content docstring + pinning test

Status: OPEN

## File
personal_index/content_api.py (def _delete_content, line 231)
tests/test_content_api.py (pinning test, mirrors TestUpdateContentDocstring526)

## Symptom
ContentAPI._delete_content has no docstring, so its exact dispatch contract is
undocumented. The content_api docstring sweep (523 _list, 524 _get, 525 _create,
526 _update) is complete except for _delete_content.

## Evidence
def _delete_content(self, item_id: str) -> tuple[int, dict[str, Any]]:
    if item_id not in self._store:
        return 404, {"error": f"Content item '{item_id}' not found"}
    self._store.pop(item_id)
    return 200, {"deleted": True, "id": item_id}

No docstring on the def. TestDeleteContent (tests/test_content_api.py line 156)
pins behavior: delete existing -> 200, resp["deleted"] is True, id removed from
store; delete not found -> 404.

## Exact contract to state
- Returns (404, {"error": "Content item '<item_id>' not found"}) when item_id is
  not in self._store.
- Otherwise removes the item from self._store (pop) and returns
  (200, {"deleted": True, "id": item_id}).

## Minimal additive fix
Add a docstring to _delete_content stating the exact contract above; add a
pinning test (TestDeleteContentDocstring527) asserting the key contract phrases
(item_id, store, 404, not found, 200, deleted, id) are present.

Issue: #925
