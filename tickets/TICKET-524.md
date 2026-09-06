# TICKET-524: Reword ContentAPI._get_content docstring to exact contract + pinning test

**Status:** OPEN

## File
- `personal_index/content_api.py` — `ContentAPI._get_content` (def at line ~153)
- `tests/test_content_api.py` — pinning test

## Symptom
`_get_content` has no docstring stating its dispatch contract. The function
looks up `item_id` in the store and returns either a 404 error or a 200 item
payload, but nothing in the source documents that contract.

## Evidence
- `personal_index/content_api.py:153-157`: def _get_content(self, item_id) -> tuple[int, dict[str, Any]]; item = self._store.get(item_id); if item is None: return 404, {"error": ...}; return 200, {"item": item}
- `tests/test_content_api.py:120-128` (TestGetContent) pins the live behavior: 200 with body["item"] when found, 404 when not found.

## Minimal additive fix
1. Add a docstring to `_get_content` stating the exact contract: looks up item_id in the store; returns (404, {"error": ...}) when the item is not found; returns (200, {"item": <item>}) when found.
2. Add a pinning test (mirror TestListContentDocstring523) asserting the docstring contains the key contract phrases.

## Issue
Issue: #918

## Status
- OPEN
