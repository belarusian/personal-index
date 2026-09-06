# TICKET-523: ContentAPI._list_content has no docstring (class-(b) doc-drift)

- **File:** `personal_index/content_api.py`
- **Symptom:** `ContentAPI._list_content` (line 124) has NO docstring at all —
  the def line is immediately followed by `items = list(self._store.values())`.
  The body performs a specific pagination contract the reader cannot see: it
  reads optional `page` (default 1) and `per_page` (default 20) from `params`,
  returns `(400, {"error": ...})` when either is not an integer, caps
  `per_page` at 100, and returns `(200, {"items": <page slice>, "total":
  <full count>, "page": <page>, "per_page": <per_page>})`.
- **Evidence line:** `personal_index/content_api.py:124`
  (`def _list_content(...)` with no docstring before line 125).
- **Context:** gh issue #908 / PR #909 (branch build140/...) previously claimed
  this as "TICKET-522" but that number was already taken by the merged sitemap
  cycle (TICKET-522 = sitemap.get_recent_entries, RESOLVED, issue #910). PR #909's
  branch is STALE (branched before the sitemap merge; it reverts merged
  sitemap.py/test_sitemap.py work) and must NOT be merged. This ticket re-does
  the underlying work fresh under the next free number.
- **Minimal additive fix:** add the exact-contract docstring to `_list_content`
  (defaults 1/20, non-integer -> 400, per_page capped at 100, 200 response shape
  with items/total/page/per_page). Add ONE pinning test that CALLS
  `_list_content` directly and asserts on the returned tuple: main path
  (page slice + total + echoed page/per_page) AND the guard path (non-integer
  page -> 400 with an "error" key); do NOT assert on the docstring wording.
- **Status:** OPEN
- **Issue:** #914
