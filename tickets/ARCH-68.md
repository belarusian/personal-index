# ARCH-68 — content_api: `_validate_content` is dead in the production request path — POST/PUT with a >200-char title or non-list tags returns 201/200 instead of 400

Status: CLAIMED (cycle 295)
Component: `personal_index/content_api.py` — `ContentAPI._create_content` (lines 168-201) and `ContentAPI._update_content` (lines 203-233); the dead validator `ContentAPI._validate_content` (lines 308-321)
Umbrella: ARCH-2 (#983)
Issue: #1390
Docs: `docs/content-api.md` (Contract Holes #1)

## Problem
`ContentAPI._validate_content(data)` (line 308) exists with a docstring
("Validate content data and return errors") and enforces: `data` must be a
`dict`; `title` (if present) must be a `str` of length ≤ 200; `tags` (if
present) must be a `list`. **It is never called by `_create_content` or
`_update_content`.** The only callers are `tests/test_content_api.py`
(lines 272-288). The real request path does only an inline
`isinstance(data, dict)` check and then stores/updates the item.

Consequence: the advertised validation is not enforced on the real path
(verified against the code):
- `POST /api/v1/content` with `{"title": "x"*201}` → **`201`** (not `400`);
  the over-length title is stored.
- `POST /api/v1/content` with `{"tags": "not-a-list"}` → **`201`** (not
  `400`); the non-list tags are stored.
- `PUT /api/v1/content/{id}` with the same bodies → **`200`** (not `400`).

The method's own contract (its docstring + the tests that pin it) says these
inputs are invalid, but the public `handle_request` contract (what a caller
actually observes) accepts them. This is a divergence between the documented
validation and the observed behavior — the same "advertised guard not wired
into the request path" class as ARCH-66/ARCH-67.

## Public contract (target)
The request path must enforce the same field validation that
`_validate_content` already defines: after parsing the JSON body in
`_create_content` and `_update_content`, if `_validate_content(data)` returns
a non-empty error list, the handler returns `(400, {"error": <first error>})`
**before** the item is stored/updated. The existing body guards (missing/empty
body, invalid JSON, non-dict body) are unchanged and still take precedence.

Preferred option (wire the existing validator):
1. In `_create_content`, after the `isinstance(data, dict)` check, call
   `errors = self._validate_content(data)`; if `errors`, return
   `(400, {"error": errors[0]})`.
2. In `_update_content`, after the `isinstance(data, dict)` check, call
   `errors = self._validate_content(data)`; if `errors`, return
   `(400, {"error": errors[0]})`.
3. Result: a >200-char title or non-list tags on POST/PUT → `400`; a valid
   body → unchanged `201`/`200`. The normal single-field path for every other
   input must be unchanged.

Alternative option (delete the dead validator):
4. If field validation is intentionally out of scope for the request path,
   delete `_validate_content` and its five tests in
   `tests/test_content_api.py` (lines 272-288), and state in
   `docs/content-api.md` that the request path performs no field validation.
   The two must agree.

Option 1 is preferred: it makes the observed behavior match the documented
contract without removing a tested, documented method.

## Behavior
- `POST /api/v1/content` with `{"title": "x"*201}` → `(400, {"error":
  "Title must be under 200 characters"})`; the store is unchanged (no item
  added, `_next_id` not incremented).
- `POST /api/v1/content` with `{"tags": "not-a-list"}` → `(400, {"error":
  "Tags must be a list"})`; the store is unchanged.
- `PUT /api/v1/content/{id}` with `{"title": "x"*201}` → `(400, {"error":
  "Title must be under 200 characters"})`; the stored item is unchanged
  (`updated_at` not refreshed).
- `POST /api/v1/content` with `{"title": "ok", "tags": ["a"]}` → `(201,
  {"item": ...})` (unchanged normal path).
- `POST /api/v1/content` with `{"title": 123}` → `(400, {"error": "Title must
  be a string"})`.

## Guard inputs
- A >200-char title on POST (the divergence input — currently 201, must be
  400).
- A non-list `tags` on POST (the divergence input — currently 201, must be
  400).
- A >200-char title on PUT (the divergence input — currently 200, must be
  400).
- A valid body (regression guard: the normal create/update path is unchanged).
- A non-dict body (regression guard: the existing `isinstance` guard still
  fires first, before `_validate_content`).

## Acceptance criteria
1. `POST /api/v1/content` with `{"title": "x"*201}` → status `400` and the
   store is unchanged (`len(store) == 0`, `_next_id == 1`).
2. `POST /api/v1/content` with `{"tags": "not-a-list"}` → status `400` and
   the store is unchanged.
3. `PUT /api/v1/content/{id}` with `{"title": "x"*201}` → status `400` and
   the stored item's `title` and `updated_at` are unchanged.
4. `POST /api/v1/content` with `{"title": "ok", "tags": ["a"]}` → status
   `201` and the item is stored (regression guard: valid path unchanged).
5. `POST /api/v1/content` with `[1, 2]` (non-dict) → status `400` with the
   existing "Request body must be a JSON object" error (regression guard:
   the `isinstance` guard still fires before `_validate_content`).

## Pinning tests to add
- `test_create_overlong_title_rejected`: `POST /api/v1/content` with
  `{"title": "x"*201}`; assert status `400` and `len(api._store) == 0`.
- `test_create_nonlist_tags_rejected`: `POST /api/v1/content` with
  `{"tags": "not-a-list"}`; assert status `400` and `len(api._store) == 0`.
- `test_update_overlong_title_rejected`: seed one item; `PUT
  /api/v1/content/{id}` with `{"title": "x"*201}`; assert status `400` and
  the stored item's `title`/`updated_at` are unchanged.
- `test_create_valid_body_still_accepted`: `POST /api/v1/content` with
  `{"title": "ok", "tags": ["a"]}`; assert status `201` and the item is
  stored (regression guard).
- `test_create_non_dict_still_rejected_first`: `POST /api/v1/content` with
  `[1, 2]`; assert status `400` and the error is "Request body must be a
  JSON object" (regression guard: the `isinstance` guard precedes
  `_validate_content`).

## Docs update (same PR)
`docs/content-api.md` — Contract Holes #1 already documents the dead
validator. After the fix, update the `_create_content` / `_update_content`
sections to state the enforced field-validation contract ("a non-empty
`_validate_content` error list maps to `400` before the item is
stored/updated") and remove/adjust the Contract Holes #1 callout once merged.
