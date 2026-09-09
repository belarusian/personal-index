# ARCH-58 — pagination: `Paginator.total_pages` divides by the raw, unclamped constructor `per_page` (ZeroDivisionError on `per_page=0`), while `get_page`/`iterate_pages` silently clamp to 1

Status: OPEN
Component: `personal_index/pagination.py` — `Paginator.__init__`, `Paginator.total_pages`, `Paginator.get_page`, `Paginator.iterate_pages`, `PageParams.__post_init__`, `PageResult.total_pages`
Umbrella: ARCH-2 (#983)
Issue: #1184
Docs: `docs/pagination.md` (Contract Holes)

## Problem
`PageParams.__post_init__` clamps `per_page = max(1, min(per_page, max_per_page))`, and both `Paginator.get_page` and `Paginator.iterate_pages` route through `PageParams`, so a `per_page=0` (or negative) request is **silently clamped to 1** and returns 1-item pages with no warning. But `Paginator.__init__` stores `self._per_page` **raw** (no clamping), and the `total_pages` property divides by that raw value:

    @property
    def total_pages(self) -> int:
        return max(1, math.ceil(len(self._items) / self._per_page))

So the same `per_page=0` input behaves three different ways across the class:

    Paginator([1, 2, 3], per_page=0).total_pages     # ZeroDivisionError: division by zero
    Paginator([], per_page=0).total_pages            # ZeroDivisionError: division by zero
    Paginator([1, 2, 3], per_page=0).get_page(1)     # PageResult(items=[1], per_page=1)  -- silently clamped
    Paginator([1, 2, 3], per_page=0).iterate_pages() # 3 single-item pages -- silently clamped

The guard is inconsistent: `total_pages` **raises**, while `get_page`/`iterate_pages` **silently clamp**. A caller who checks `total_pages` before iterating crashes; a caller who only iterates gets a surprising 1-item-per-page result with no signal. This is a guard-path inconsistency hole (the ARCH-2 umbrella class): no exception on the clamp path, no warning, just a silently-wrong page size.

The same raw division exists in `PageResult.total_pages` (`math.ceil(self.total / self.per_page)`), so a **hand-built** `PageResult(items, total, page, per_page=0)` also raises `ZeroDivisionError` on `total_pages`. The `Paginator` never produces such a result (it clamps via `PageParams`), so this only bites direct construction — but the precondition is unstated.

## Public contract (target)
Make the `per_page` guard consistent across the whole module: **clamp, never raise, never silently diverge.** The `Paginator` should clamp its constructor `per_page` exactly the way `PageParams` does, so every entry point agrees on the effective page size.

Preferred option (document it in the docstrings):
1. **Clamp in `Paginator.__init__`** — set `self._per_page = max(1, min(per_page, max_per_page))` (mirroring `PageParams.__post_init__`). Then `total_pages`, `get_page`, and `iterate_pages` all operate on the same clamped value, so `per_page=0`/negative yields 1-item pages everywhere and **no path raises**. This is the least invasive and makes the class internally consistent.
2. **Raise consistently** — validate `per_page >= 1` in `__init__` (and in `PageParams.__post_init__`) and raise `ValueError` for `per_page < 1`. This is a breaking change for the currently-silent clamp path, so it is the less-preferred option.

The ARCHITECT prefers option 1 (clamp in `__init__`) because it preserves the existing silent-clamp behavior of `get_page`/`iterate_pages` while removing the `ZeroDivisionError` from `total_pages`, making all three entry points agree.

Regardless of option, `PageResult.total_pages` should state its `per_page != 0` precondition in its docstring (it is a pure property over a hand-buildable dataclass, so it cannot clamp without changing the dataclass contract).

## Behavior
- `Paginator([1, 2, 3, 4, 5], per_page=0).total_pages` → `5` (clamped to 1 item/page), not `ZeroDivisionError`.
- `Paginator([], per_page=0).total_pages` → `1` (empty-collection guard preserved), not `ZeroDivisionError`.
- `Paginator([1, 2, 3], per_page=-5).total_pages` → `3` (clamped to 1), consistent with `get_page`.
- `Paginator([1, 2, 3, 4, 5], per_page=2).total_pages` → `3` (unchanged normal path).
- `Paginator([1, 2, 3], per_page=0).get_page(1)` → `PageResult(items=[1], per_page=1)` (unchanged clamp).
- `Paginator([1, 2, 3], per_page=0).iterate_pages()` → 3 single-item pages (unchanged clamp).
- `PageResult(items=[1], total=1, page=1, per_page=0).total_pages` → still raises `ZeroDivisionError` **unless** the implementer chooses to guard it; the docstring must state the `per_page != 0` precondition either way.

## Guard inputs
- `Paginator([], per_page=0).total_pages` → `1` (empty + zero per_page).
- `Paginator([1, 2, 3], per_page=0).total_pages` → `3` (non-empty + zero per_page).
- `Paginator([1, 2, 3], per_page=-5).total_pages` → `3` (negative per_page).
- `Paginator([1, 2, 3], per_page=0).get_page(1).per_page` → `1` (clamp visible in the result).
- `PageParams(per_page=0).per_page` → `1` (existing clamp, unchanged).
- `PageParams(per_page=5, max_per_page=0).per_page` → `1` (existing floor-wins clamp, unchanged).

## Acceptance criteria
1. `Paginator(items, per_page=0).total_pages` does **not** raise `ZeroDivisionError`; it returns `max(1, len(items))` (clamped to 1 item/page).
2. `Paginator([], per_page=0).total_pages` returns `1`.
3. `Paginator(items, per_page=0).total_pages` equals `len(Paginator(items, per_page=0).iterate_pages())` (the two entry points agree on the page count).
4. `Paginator(items, per_page=0).get_page(1).per_page` is `1` (clamp unchanged).
5. `PageResult.total_pages` docstring states the `per_page != 0` precondition (or the property is guarded, in which case state the new behavior).
6. Normal path unchanged: `Paginator([1,2,3,4,5], per_page=2).total_pages` is `3`.

## Pinning tests to add
- `test_paginator_total_pages_zero_per_page_no_raise`: `Paginator([1,2,3], per_page=0).total_pages` returns `3` (no `ZeroDivisionError`).
- `test_paginator_total_pages_zero_per_page_empty`: `Paginator([], per_page=0).total_pages` returns `1`.
- `test_paginator_total_pages_matches_iterate_pages_zero_per_page`: for `per_page=0`, `total_pages == len(iterate_pages())`.
- `test_paginator_get_page_zero_per_page_clamps`: `Paginator([1,2,3], per_page=0).get_page(1).per_page == 1` and `.items == [1]`.
- `test_paginator_total_pages_normal_unchanged`: `Paginator([1,2,3,4,5], per_page=2).total_pages == 3`.

## Docs update (same PR)
`docs/pagination.md` — the Contract Holes section documents this hole; after the fix, update it to state the new consistent-clamp contract (every entry point clamps `per_page` to `max(1, min(per_page, max_per_page))`; no path raises on `per_page=0`). Remove/adjust the Contract-holes bullet for this hole once merged, and keep the `PageResult.total_pages` `per_page != 0` precondition note.
