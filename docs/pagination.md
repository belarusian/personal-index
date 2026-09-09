# pagination — `personal_index.pagination`

Pagination utilities for search and browse results. Wraps a flat `list[Any]`
in a `Paginator` that slices it into `PageResult` pages, and exposes two
standalone dataclasses — `PageParams` (a clamped page/limit pair) and
`PageResult` (a page plus its derived navigation fields).

Stdlib-only (`math`, `dataclasses`, `typing`). No I/O, no network, no disk —
every method is a pure in-memory transform over the input list.

## Public API

### `PageParams` (dataclass)

A clamped (page, per_page) pair.

| Field | Type | Default |
|-------|------|---------|
| `page` | `int` | `1` |
| `per_page` | `int` | `20` |
| `max_per_page` | `int` | `100` |

- `__post_init__` — **clamps both fields**: `page = max(1, page)` and
  `per_page = max(1, min(per_page, max_per_page))`. So after construction
  `page >= 1` and `1 <= per_page <= max_per_page` **always** hold. A
  hand-built `PageParams(page=0)` becomes `page=1`; `PageParams(per_page=0)`
  becomes `per_page=1`; `PageParams(per_page=5, max_per_page=0)` becomes
  `per_page=1` (the `max(1, ...)` floor wins over the `min(..., 0)` cap).
  This is the ONLY place in the module that clamps — see the Contract Holes
  section for why that matters.
- `offset` (property) — `(page - 1) * per_page`; the zero-based slice start.
- `limit` (property) — `per_page`; the slice length.

### `PageResult` (dataclass)

One page plus its derived navigation fields.

| Field | Type |
|-------|------|
| `items` | `list[Any]` |
| `total` | `int` |
| `page` | `int` |
| `per_page` | `int` |

Derived properties (all pure, no side effects):

- `total_pages` — `max(1, ceil(total / per_page))`. **Guard path:** when
  `total == 0` (or `total < per_page`) returns `1`, never `0`. **Division
  path:** this is a raw `math.ceil(total / per_page)` with **no guard on
  `per_page == 0`** — a `PageResult` built directly with `per_page=0` raises
  `ZeroDivisionError` here (the `Paginator` never produces such a result, so
  this only bites hand-built instances).
- `has_next` — `page < total_pages`.
- `has_prev` — `page > 1`.
- `next_page` — `page + 1` if `has_next` else `None`.
- `prev_page` — `page - 1` if `has_prev` else `None`.
- `start_index` — `(page - 1) * per_page + 1`; 1-based first item on the page.
- `end_index` — `min(page * per_page, total)`; 1-based last item on the page
  (clamped to `total`, so the last partial page reports its true end).
- `to_dict` — returns a dict with keys `items`, `total`, `page`, `per_page`,
  `total_pages`, `has_next`, `has_prev`, `next_page`, `prev_page`,
  `start_index`, `end_index`. **One-way:** there is no `from_dict`, so a
  serialized `PageResult` cannot be reloaded (the `items` list is embedded
  verbatim, so round-tripping is only meaningful for the scalar fields).

### `Paginator`

`__init__(self, items: list[Any], per_page: int = 20, max_per_page: int = 100)`
— stores `self._items`, `self._per_page`, `self._max_per_page` **raw, with no
clamping** (unlike `PageParams.__post_init__`). See the Contract Holes
section.

- `get_page(page: int = 1, per_page: int | None = None) -> PageResult` —
  builds a `PageParams` (so `page` and `per_page` **are** clamped here),
  slices `items[offset:offset+limit]`, and returns a `PageResult` with
  `total = len(items)`. A `per_page` argument of `None` uses the constructor
  default. Because it routes through `PageParams`, `get_page` **never** raises
  on `per_page=0`/negative — it silently clamps to `1`.
- `total_items` (property) — `len(items)`.
- `total_pages` (property) — `max(1, ceil(len(items) / self._per_page))`
  using the **raw, unclamped** `self._per_page`. **Guard path:** empty
  collection returns `1`. **Division path:** `per_page=0` (constructor) raises
  `ZeroDivisionError` here — the asymmetry with `get_page` is the ticketed
  hole.
- `iterate_pages(per_page: int | None = None) -> list[PageResult]` — calls
  `get_page` in a loop (page 1, 2, ... until `has_next` is false), so it
  inherits `get_page`'s clamping and **never** raises on `per_page=0`/negative
  (it clamps to 1 and returns `len(items)` single-item pages). Always returns
  at least one page, even for an empty collection.

## Contract Holes

**Single most important hole — `Paginator.total_pages` divides by the raw,
unclamped constructor `per_page`, so `per_page=0` raises `ZeroDivisionError`
while `get_page`/`iterate_pages` silently clamp to 1.** `PageParams.__post_init__`
clamps `per_page` to `max(1, min(per_page, max_per_page))`, and `get_page` /
`iterate_pages` both route through `PageParams`, so they **silently clamp** a
`per_page=0` (or negative) request to `1` and return a page of 1 item. But
`Paginator.__init__` stores `self._per_page` **raw** (no clamping), and the
`total_pages` property does `math.ceil(len(self._items) / self._per_page)`
directly on that raw value. Empirically:

    Paginator([1, 2, 3], per_page=0).total_pages   # ZeroDivisionError: division by zero
    Paginator([], per_page=0).total_pages          # ZeroDivisionError: division by zero
    Paginator([1, 2, 3], per_page=0).get_page(1)   # PageResult(items=[1], per_page=1)  -- silently clamped
    Paginator([1, 2, 3], per_page=0).iterate_pages()  # 3 single-item pages -- silently clamped

So the same `per_page=0` input **raises** through `total_pages` but **silently
returns 1-item pages** through `get_page`/`iterate_pages`. The guard is
inconsistent: one path raises, the other two clamp, and the clamp is invisible
(no warning, no error). This is a guard-path inconsistency hole (the ARCH-2
umbrella class): a caller who checks `total_pages` before iterating crashes,
while a caller who only iterates gets a surprising 1-item-per-page result with
no signal. See `tickets/ARCH-58.md`.

Secondary (documented here, not ticketed): `PageResult.total_pages` has the
same raw division, so a **hand-built** `PageResult(items, total, page,
per_page=0)` also raises `ZeroDivisionError` on `total_pages`. The `Paginator`
never produces such a result (it clamps via `PageParams`), so this only bites
direct construction — but the docstring should state the `per_page != 0`
precondition explicitly.
