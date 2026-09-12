# ARCH-47: content-rollback — in-memory-only store loses every rollback point on process exit

Status: CLAIMED 2026-09-12
Component: `personal_index/content_rollback.py`
Issue: #1136
Refs: ARCH-2 (#983 umbrella); same persistence-class as ARCH-40 (storage), ARCH-44 (content-pin), ARCH-46 (content-versioning)

## Symptom

The entire `ContentRollback` store is a single in-process
`dict[str, list[RollbackPoint]]` (`self._rollback_points`) with **no**
`save`/`load`, no file, and no serialization. A `ContentRollback` instance is
the only holder of the state, and the moment the process exits (or the
instance is garbage-collected) every rollback point for every URL is gone.

This defeats the subsystem's core purpose: a "rollback point" is only useful
if it survives long enough to be rolled back to, and an in-memory-only
snapshot cannot outlive the process that created it. Compare the sibling
subsystems that DO persist — `personal_index/content_versioning.py`
(JSON-file-backed, ARCH-46), `personal_index/content_pin.py` (JSON-file-backed,
ARCH-44), and `personal_index/storage.py` (JSON-file-backed, ARCH-40) — all of
which at least attempt durability. `content_rollback` is the only "history /
snapshot" subsystem in the package with no persistence at all, so the
persistence contract is the single most important hole here.

## Public contract (the fix must preserve the happy path)

- All four public methods keep their current signatures and behavior:
  `create_rollback_point` (appends the `RollbackPoint` to the URL's list,
  initializing the list on first use; stores by reference; returns `None`),
  `get_rollback_points` (returns a shallow copy of the list, `[]` for an
  absent URL, creation order), `rollback` (pure accessor, `points[index]`,
  `None` if the URL has no points, `index` defaults to 0 = oldest),
  `clear` (truthy url → pop that url; falsy url → clear all; returns `None`).
- The persistence contract must be made explicit (pick one and document it in
  the `ContentRollback` docstring + `docs/content-rollback.md`):
  - **Option A (add persistence):** add `save(path)` / `load(path)` (or an
    `__init__(storage_path: str | None = None)` that loads on construction) so
    rollback points survive process exit, mirroring the JSON-file-backed
    pattern of the sibling subsystems. `RollbackPoint` must be made
    serializable (it is a plain `@dataclass` of `str`/`dict[str, Any]`, so a
    `dataclasses.asdict` / `dataclasses.fields` round-trip is sufficient).
  - **Option B (document the in-memory-only contract):** if persistence is
    intentionally out of scope, state it explicitly in the `ContentRollback`
    docstring and `docs/content-rollback.md` — "rollback points are in-memory
    only and are lost on process exit; this is a per-process scratch store,
    not a durable history" — so a caller is not misled into treating it as
    durable.
- Whichever option is chosen, the postcondition must hold and be stated: a
  caller reading the docstring must know, without reading the source, whether
  a rollback point created in one process is available in the next.

## Acceptance criteria

1. The happy path is unchanged: all four public methods behave exactly as
   documented in `docs/content-rollback.md`.
2. The persistence contract is stated in the `ContentRollback` docstring and
   in `docs/content-rollback.md` (Option A: rollback points survive process
   exit via save/load; Option B: the in-memory-only, lost-on-exit contract is
   stated explicitly).
3. If Option A: a `save`/`load` round-trip preserves every `RollbackPoint`
   (url, content, title, timestamp, metadata) for every URL, and a fresh
   instance constructed from the saved path reflects the loaded points.
4. If Option B: the docstring and the docs page both state that points are
   lost on process exit, and no caller-facing API implies durability.

## Pinning tests to add (tests/test_content_rollback.py)

- `test_rollback_point_roundtrip` (happy path) — create two `RollbackPoint`s
  for the same URL, `get_rollback_points` returns both in creation order, and
  `rollback(url)` returns the oldest (index 0) while `rollback(url, -1)`
  returns the newest.
- `test_rollback_absent_url_is_none` (guard path) — `rollback("no-such-url")`
  returns `None` and `get_rollback_points("no-such-url")` returns `[]` (no
  exception).
- `test_persistence_contract` (the contract hole) — Option A: `save` to a
  temp path, construct a fresh `ContentRollback` from that path, and assert
  every point survives (url, content, title, timestamp, metadata); Option B:
  assert the documented in-memory-only contract by confirming there is no
  `save`/`load` surface and the docstring states points are lost on exit. This
  single test pins the whole contract hole.

## Docs update (same PR)

`docs/content-rollback.md` "Contract Holes" section (already authored in this
PR) names this as the primary hole; the implementer must update the
`ContentRollback` entry in the "Public API" section to state the chosen
persistence contract once implemented.
