# TICKET-487: pagination get_page/iterate_pages silently coerce per_page=0 to default

## File
personal_index/pagination.py

## Symptom
`Paginator.get_page()` and `Paginator.iterate_pages()` select the per-page size with
`per_page or self._per_page`. Because `0` is falsy, an explicit `per_page=0` is silently
coerced to the constructor default (e.g. 20) instead of being clamped to `1` by
`PageParams.__post_init__` (`self.per_page = max(1, min(self.per_page, self.max_per_page))`).
The documented clamp-to-1 contract is bypassed for the falsy input, so a caller asking for
"0 items per page" gets a full default-sized page with no error or warning.

## Evidence
Line ~121: `per_page=per_page or self._per_page,` in get_page
Line ~131: `result = self.get_page(page_num, per_page)` in iterate_pages (same falsy path)
`PageParams.__post_init__` (line ~20) clamps `per_page` to `max(1, ...)`, but the `or`
short-circuits before PageParams ever sees the 0.
Verified: `Paginator(range(50), per_page=20).get_page(1, per_page=0).per_page == 20`
(expected 1 after clamp).

## Minimal Additive Fix
In `get_page`, replace `per_page or self._per_page` with an explicit None check so that a
falsy-but-valid `0` reaches `PageParams` and is clamped to 1:
`per_page = self._per_page if per_page is None else per_page`.
Add a test that pins `get_page(1, per_page=0).per_page == 1` (guard path) alongside the
normal `per_page=5` case.

## Issue
Issue: #827
