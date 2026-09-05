# TICKET-433: api.pagination.paginate doc-drift (blanket docstring)

- File: personal_index/api/pagination.py
- Function: paginate(items, page=1, page_size=20) -> PaginatedResult[T]
- Symptom: docstring is a blanket one-liner ("Paginate a sequence of items.")
  that does not enumerate the guard paths, the clamping behavior, or the
  returned object's fields.
- Evidence: line 71 `"""Paginate a sequence of items."""`
- Minimal additive fix: reword the docstring to state the EXACT behavior:
  (1) guard paths - page < 1 raises ValueError("Page must be >= 1"),
      page_size < 1 raises ValueError("Page size must be >= 1");
  (2) total_items = len(items); total_pages = max(1, ceil(total_items / page_size));
  (3) empty-sequence clamp - if total_items == 0, page is forced to 1
      (via _clamp_page);
  (4) out-of-range clamp - page is clamped to [1, total_pages]
      (page > total_pages -> total_pages, page < 1 already raised);
  (5) page_items = items[(page-1)*page_size : (page-1)*page_size + page_size];
  (6) returned PaginatedResult(items=page_items, page_info=PageInfo(...)) where
      PageInfo fields are: page (clamped), page_size, total_items, total_pages,
      has_next = page < total_pages, has_prev = page > 1; PageInfo also exposes
      start_index = (page-1)*page_size and end_index = min(start_index + page_size,
      total_items) as properties.
  Add ONE pinning test class asserting the RETURNED OBJECT fields for the
  normal case (page 2 of 3: items slice, page_info.page/page_size/total_items/
  total_pages/has_next/has_prev, start_index/end_index) AND the guard path
  (empty sequence: items [], page_info.page 1, total_items 0, total_pages 1,
  has_next False, has_prev False, start_index 0, end_index 0).
- Issue: #704
- Status: OPEN
