# TICKET-519: content_api._route_content one-liner placeholder docstring

- **File:** personal_index/content_api.py
- **Function:** `_route_content` (line 74)
- **Symptom (class b - doc drift / over-promise placeholder):**
  The docstring is a one-liner placeholder that does not state the dispatch
  contract: 'Route /api/v1/content requests.'
  It does not say what it inspects (the HTTP `method`), what it returns on each
  branch, or the fallback.
- **Evidence (line 77):** the one-line placeholder docstring on `_route_content`.
- **Actual behavior (lines 74-82):**
  - `method == "GET"`  -> returns a zero-arg lambda that calls
    `self._list_content(params)` -> `(200, {items, total, page, per_page})`
    (or `(400, {error})` on non-integer page/per_page).
  - `method == "POST"` -> returns a zero-arg lambda that calls
    `self._create_content(body)` -> `(201, {item})` on success,
    `(400, {error})` on missing/invalid body.
  - any other method   -> returns `None` (caller maps to 404/405).
- **Minimal additive fix:**
  Reword the docstring to the exact dispatch contract (enumerate the two
  matched branches and the `None` fallback). Add ONE pinning test that CALLS
  the returned handler and asserts on the result for the main branch (GET ->
  200 list) AND the guard/fallback path (unmatched method -> None).
- **Issue:** #898
- **Status:** RESOLVED (merged PR #900, issue #898 closed)
