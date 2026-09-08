Status: CLAIMED 2026-09-08
Kind: IMPL
Author: implementer (cycle 172)
References: ARCH-1 (issue #982) — umbrella parent
Issue: #1008

# IMPL-2: PageResult.total_pages exact-contract docstring + pinning test

## Scope (single bounded unit, in-path)

The OPEN queue (ARCH-1 umbrella, ARCH-2 docs-only, ARCH-3 OPEN-PUSHBACK,
IMPL-1 docs-only) holds no fully-in-path single unit, so this cycle runs the
legacy claim-truth / exact-contract doc-drift fallback on exactly one function:

- Target: `PageResult.total_pages` in `personal_index/pagination.py`
  (property at ~line 43).
- Current docstring: "Total number of pages." (too thin for exact-contract form).

## Acceptance (exact-contract, per docs/CONTRACTS.md parts 1-3)

1. Reword the `PageResult.total_pages` docstring to exact-contract form:
   - Behavior: returns `max(1, ceil(total / per_page))` — the smallest page
     count that covers `total` items at `per_page` per page.
   - Guard path: when `total == 0` (or `total < per_page`), returns `1`
     (never 0).
   - Return: `int`.
   - Side effects: none (pure property).
2. Add ONE pinning test `test_page_result_total_pages_pinned` in
   `tests/test_pagination.py` asserting the RETURNED int for BOTH:
   - normal case with non-integer division (total=25, per_page=10 -> 3), AND
   - the guard case total=0 (-> 1).
3. No behavior change — docstring + test only. No docs/** edits.

## Line-shift guard

`grep -rn --include='*.py' 'lineno|getsource|_get_source_lines|_method_line_span'
tests/ | grep -i 'pagination|PageResult'` returns nothing: no .py test pins
pagination by literal line number, so adding docstring lines is safe.
