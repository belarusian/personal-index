# TICKET-321: content_reader.ContentReader.paginate raises ZeroDivisionError on page_size=0

- Status: RESOLVED
- Issue: #477 (closed)
- Merged: main f038b93 (PR #479)
- Module: personal_index/content_reader.py
- Defect class: (b) sibling-class asymmetry — a pagination guard present on the two
  near-identical sibling pagination implementations is missing on this one.

## Symptom
`ContentReader.paginate` (content_reader.py:83) computes:
    total_pages = max(1, (total_items + page_size - 1) // page_size)
with no guard on `page_size`. A caller passing `page_size=0` therefore makes
`paginate` raise `ZeroDivisionError: integer division or modulo by zero`. `ContentReader`
is a public module (importable as `personal_index.content_reader`, with a dedicated
test file `tests/test_content_reader.py`), so `paginate` is a public API surface
that accepts a caller-supplied `page_size`.

## Evidence (verified at runtime, cycle 49)
- `ContentReader().paginate(page_size=0)` -> `ZeroDivisionError: integer division or
  modulo by zero` (reproduced on main 78054ad).
- The two sibling pagination implementations guard the identical `page_size` input:
  - `api/pagination.py` `paginate` calls `_validate_page` which raises
    `ValueError("Page size must be >= 1")` when `page_size < 1` (api/pagination.py:84-89),
    pinned by `tests/test_api/test_pagination.py::test_invalid_page_size`.
  - `pagination.py` `PageParams.__post_init__` clamps `per_page` with
    `max(1, min(self.per_page, self.max_per_page))` (pagination.py:18-20).
  `content_reader.py` `paginate` is the only pagination entry point with no such guard.
- No test in tests/test_content_reader.py exercised a non-positive `page_size` before
  this fix.

## Impact
A single caller-supplied `page_size=0` (e.g. from a CLI flag, an API query param, or a
config value) makes `ContentReader.paginate` raise an unhandled `ZeroDivisionError`,
aborting the browse/pagination call. Same defect family as the sibling
`api/pagination.py` guard (ValueError on `page_size < 1`).

## Fix (minimal, additive)
Guard `page_size` at the top of `ContentReader.paginate`: raise
`ValueError("Page size must be >= 1")` when `page_size < 1`, matching the sibling
`api/pagination.py` `_validate_page` behavior and message exactly. No signature or
behavior change for valid `page_size`. Adds regression tests pinning the guard
(`page_size=0` and `page_size=-1` both raise `ValueError`).
