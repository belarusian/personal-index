# content-rollback — Exact Contract

Module: `personal_index/content_rollback.py` (64 lines, stdlib-only imports:
`dataclasses`, `typing`).

In-memory content rollback management. Two public types: `RollbackPoint` (a
5-field `@dataclass` snapshot of content) and `ContentRollback` (the engine:
`create_rollback_point`, `get_rollback_points`, `rollback`, `clear`). State
lives entirely in a single in-process `dict[str, list[RollbackPoint]]` keyed
by URL; there is **no** persistence layer — no `save`/`load`, no file, no
serialization. Every rollback point is lost when the process exits.

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

**Primary hole — in-memory-only persistence: every rollback point is lost on
process exit (ARCH-47).** The entire store is a single in-process
`dict[str, list[RollbackPoint]]` with no `save`/`load`, no file, and no
serialization. A `ContentRollback` instance is the only holder of the state,
and the moment the process exits (or the instance is garbage-collected) every
rollback point for every URL is gone. This defeats the subsystem's core
purpose: a "rollback point" is only useful if it survives long enough to be
rolled back to, and an in-memory-only snapshot cannot outlive the process that
created it. Compare the sibling subsystems that DO persist —
`personal_index/content_versioning.py` (JSON-file-backed, ARCH-46),
`personal_index/content_pin.py` (JSON-file-backed, ARCH-44), and
`personal_index/storage.py` (JSON-file-backed, ARCH-40) — all of which at
least attempt durability. The fix must make the persistence contract explicit
(pick one and document it in the `ContentRollback` docstring + this page):

- **Option A (add persistence):** add `save(path)` / `load(path)` (or a
  `__init__(storage_path=...)` that loads on construction) so rollback points
  survive process exit, mirroring the JSON-file-backed pattern of the sibling
  subsystems.
- **Option B (document the in-memory-only contract):** if persistence is
  intentionally out of scope, state it explicitly in the `ContentRollback`
  docstring and this page — "rollback points are in-memory only and are lost
  on process exit; this is a per-process scratch store, not a durable
  history" — so a caller is not misled into treating it as durable.

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
