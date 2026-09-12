# content-rollback — Exact Contract

Module: `personal_index/content_rollback.py` (64 lines, stdlib-only imports:
`dataclasses`, `typing`).

In-memory content rollback management. Two public types: `RollbackPoint` (a
5-field `@dataclass` snapshot of content) and `ContentRollback` (the engine:
`create_rollback_point`, `get_rollback_points`, `rollback`, `clear`). State
lives entirely in a single in-process `dict[str, list[RollbackPoint]]` keyed
by URL; there is **no** persistence layer — no `save`/`load`, no file, no
serialization. **Persistence contract (Option B):** rollback points are
in-memory only and are lost on process exit; this is a per-process scratch
store, not a durable history. A rollback point created in one process is
NOT available in the next process.

## Public API

### RollbackPoint

`@dataclass` with 5 fields:

- `url: str`
- `content: str`
- `title: str = ""`
- `timestamp: str = ""`
- `metadata: dict[str, Any] = field(default_factory=dict)`

There is no `__post_init__` and no methods. `timestamp` is a plain `str` with
no stamping, parsing, or validation — a caller-supplied value is preserved
verbatim, and the default is the empty string. `metadata` uses
`field(default_factory=dict)` so each instance gets its own fresh dict (no
shared mutable default).

### ContentRollback

Plain class (not a dataclass). `__init__(self) -> None`:

- `self._rollback_points: dict[str, list[RollbackPoint]] = {}` — keyed by URL,
  each value the ordered list of that URL's rollback points (index 0 = the
  oldest point created for that URL).

- **Persistence contract (Option B):** the store is in-memory only. There
  is no `save`/`load`, no file, and no serialization; every rollback point
  is lost on process exit. This is a per-process scratch store, not a
  durable history — a rollback point created in one process is NOT
  available in the next process. No caller-facing API implies durability.

- `create_rollback_point(self, point: RollbackPoint) -> None`:
  - if `point.url` is not yet a key, initializes `self._rollback_points[point.url] = []`.
  - appends `point` to that URL's list.
  - **Stores the `RollbackPoint` object by reference** (no copy), so mutating
    the caller's `point` after creation mutates the stored snapshot.
  - Returns `None`.

- `get_rollback_points(self, url: str) -> list[RollbackPoint]`:
  - returns `list(self._rollback_points.get(url, []))` — a **shallow copy** of
    the internal list (the list itself is copied, but the `RollbackPoint`
    elements are still shared by reference).
  - returns `[]` for a URL that has no rollback points (guard path, no
    exception).
  - order is creation order (index 0 = oldest).

- `rollback(self, url: str, index: int = 0) -> RollbackPoint | None`:
  - a **pure accessor**: it does not mutate the stored points and does not
    apply the rollback to any current content.
  - `points = self._rollback_points.get(url, [])`; if `points` is empty →
    returns `None` (guard path).
  - otherwise returns `points[index]`.
  - `index` defaults to `0` (the oldest point). A negative `index` is passed
    straight to list indexing, so `index=-1` returns the **newest** point. An
    out-of-range `index` (e.g. `index >= len(points)`, or a negative index
    whose magnitude exceeds the list length) raises `IndexError` — there is no
    bounds check and no `None`/clamp fallback for the non-empty case.

- `clear(self, url: str | None = None) -> None`:
  - two paths, selected by the truthiness of `url`:
    - `url` truthy → `self._rollback_points.pop(url, None)` — removes only
      that URL's list; other URLs are untouched. Popping an absent URL is a
      no-op (no exception).
    - `url` falsy (`None` or `""`) → `self._rollback_points.clear()` — removes
      **all** URLs.
  - mutates only the internal store and returns `None`; it does not apply any
    rollback to current content.

## Contract Holes

**Resolved — persistence (ARCH-47).** The store was previously in-memory
only, so every rollback point was lost on process exit. This is now
documented as an intentional design constraint with **Option B (document
the in-memory-only contract)**: rollback points are in-memory only and are
lost on process exit; this is a per-process scratch store, not a durable
history. The contract is stated in the `ContentRollback` docstring and the
Public API entry above, and pinned by `test_persistence_contract` in
`tests/test_content_rollback.py` (no `save`/`load` surface exists and the
docstring states points are lost on exit).


## Secondary notes (not ticketed)

- **`rollback` index semantics are underspecified.** The docstring says
  "0 = oldest" but never states the out-of-range or negative behavior. As
  implemented, `index >= len(points)` raises `IndexError` (no `None`/clamp),
  and a negative `index` selects from the newest end (`-1` = newest). The
  contract should pin exactly which of these is intended.
- **Name-vs-body over-promise on `rollback`.** The method name `rollback`
  over-promises a restore semantic the body does not implement: it is a pure
  accessor that returns a `RollbackPoint` and mutates nothing. A caller
  expecting "roll the content back to this point" gets only the snapshot
  object and must apply it themselves.
- **`create_rollback_point` stores by reference.** The `RollbackPoint` is
  appended without a copy, so a caller that mutates the object after creation
  silently mutates the stored snapshot. `get_rollback_points` returns a copy of
  the *list* but still shares the `RollbackPoint` elements, so the same
  aliasing applies on the read side.
- **No unbounded-retention guard.** There is no cap on the number of rollback
  points per URL; every `create_rollback_point` grows the list indefinitely.
  (Less severe than the persistence hole because the store is in-memory, but
  the contract never states a retention/eviction policy.)
