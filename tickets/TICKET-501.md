# TICKET-501: Paginator.iterate_pages docstring omits its real contract

Status: RESOLVED
Issue: #858

## File
personal_index/pagination.py — `Paginator.iterate_pages` (line ~138)

## Symptom
The docstring is the generic `"""Get all pages as a list."""`, which omits the
actual contract of the method.

## Evidence (verified live)
- Returns a `list[PageResult]`, one entry per page, in page order.
- ALWAYS returns at least one page, even for an EMPTY collection:
  `Paginator([]).iterate_pages()` -> `[PageResult(items=[], total=0, total_pages=1)]`
  (because `PageResult.total_pages = max(1, ceil(total/per_page))`).
- The optional `per_page` argument, when given, overrides the constructor
  default for BOTH the slicing AND the `total_pages` computation:
  `Paginator(range(10)).iterate_pages(per_page=3)` -> 4 pages of sizes [3,3,3,1].
- The last page may be partial (fewer than per_page items).

## Minimal additive fix
Reword the `iterate_pages` docstring to state the exact contract above, and
append pinning tests to tests/test_pagination.py (TestIteratePagesContract):
empty-collection -> 1 page, per_page override affects page count, return type,
partial last page.
