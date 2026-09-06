# TICKET-520: content_api._route_content_item docstring is a one-liner placeholder (class-(b) doc-drift)

- **File:** `personal_index/content_api.py`
- **Symptom:** `_route_content_item` (line 96) carries only the one-liner
  placeholder `"""Route /api/v1/content/{id} requests."""` (line 98), while its
  sibling `_route_content` was reworded to the exact dispatch contract in
  cycle 151 (TICKET-519). The placeholder over-promises nothing but states no
  dispatch contract, so the reader cannot tell which HTTP methods are handled
  or what the None fallback means.
- **Evidence line:** `personal_index/content_api.py:98`
  (`"""Route /api/v1/content/{id} requests."""`)
- **Minimal additive fix:** reword the docstring to the exact dispatch
  contract the body performs:
  - `"GET"`    -> zero-arg callable running `self._get_content(item_id)`
    -> `(200, {item})` on a match, `(404, {error})` when the id is absent.
  - `"PUT"`    -> zero-arg callable running `self._update_content(item_id, body)`
    -> `(200, {item})` on success, `(404, {error})` / `(400, {error})` on a
    missing id or missing/invalid body.
  - `"DELETE"` -> zero-arg callable running `self._delete_content(item_id)`
    -> `(200, {deleted, id})` on a match, `(404, {error})` when absent.
  - any other method -> `None` (the caller maps this to 404/405).
  Add ONE pinning test class that calls the handler and asserts the result
  (main matched branch AND the None fallback); do NOT assert bound-method
  identity.
- **Status:** OPEN
- **Issue:** #902
