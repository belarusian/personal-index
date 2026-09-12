# ARCH-32: robots_cache — "Thread-safe" docstring claim with no locking

Status: IMPLEMENTED #1285@0721e40
Component: `personal_index/robots_cache.py`
Issue: #1090
Refs: ARCH-2 (#983 umbrella)

## Symptom

The `RobotsCache` class docstring reads **"Thread-safe cache for robots.txt
results."** but the module imports only `logging`, `time`, and `dataclasses` —
there is **no `threading` import and no lock anywhere in the file**. Every
mutating public path is a non-atomic read-modify-write:

- `get()`: `entry = self._cache.get(domain)` … `del self._cache[domain]`
  (read-then-delete; a concurrent `put` can insert between the two).
- `put()`: `if len(self._cache) >= self._max_entries: self._evict_oldest()`
  then `self._cache[entry.domain] = entry` (len-check → evict → set; two
  threads can both pass the len-check and both evict, over-evicting).
- `_evict_oldest()`: `min(self._cache, key=...)` then `del self._cache[oldest]`
  (min-then-delete; a concurrent mutation can make the key stale → `KeyError`).

The "Thread-safe" claim is a **false over-promise**: a caller that trusts it
and shares one `RobotsCache` across threads has no guarantee of consistency.

## Evidence

- `personal_index/robots_cache.py` line 49: `class RobotsCache:` docstring
  "Thread-safe cache for robots.txt results."
- `personal_index/robots_cache.py` lines 1-10: imports are `logging`, `time`,
  `dataclasses` only — no `threading`.
- `personal_index/robots_cache.py` `get()` (line ~57-73): read then `del`.
- `personal_index/robots_cache.py` `put()` (line ~75-83): len-check, evict, set.
- `personal_index/robots_cache.py` `_evict_oldest()` (line ~103-109): min then `del`.

## Minimal additive fix

Pick ONE of the two, and make the docstring match the code:

**Option A (make it actually thread-safe)**: add `import threading`, create
`self._lock = threading.Lock()` in `__init__`, and wrap the body of every
public method (`get`, `put`, `invalidate`, `invalidate_all`) with
`with self._lock:`. Keep the "Thread-safe" docstring.

**Option B (correct the claim)**: reword the class docstring to state the cache
is **not** thread-safe and the caller must serialize access (e.g. "In-memory
cache for robots.txt results. Not thread-safe; callers must serialize access.").
No locking added.

The contract decision is: the docstring must match the code. Option A is
preferred if the cache is intended to be shared across the pipeline's worker
threads; Option B if it is only ever used single-threaded.

## Acceptance criteria

1. The class docstring's thread-safety claim matches the code: either a lock
   guards every public method (Option A) or the docstring explicitly states the
   cache is not thread-safe (Option B).
2. If Option A: a concurrency test (below) passes with no lost updates, no
   `KeyError`, and `size` never exceeds `max_entries`.
3. If Option B: a docstring-assertion test pins the corrected "not thread-safe"
   wording.
4. No behavior change to the single-threaded `get`/`put`/`invalidate`/
   `invalidate_all`/`size`/`domains`/`get_stats` contract (see
   `docs/robots-cache.md`).

## Pinning tests to add

- **Thread-safety (Option A)**: spawn N threads hammering `put`/`get`/
  `invalidate` on a shared `RobotsCache(max_entries=small)`; assert no
  exception, `size <= max_entries`, and no lost/`KeyError` entries.
- **Docstring claim (Option B)**: assert the `RobotsCache` docstring contains
  the corrected "not thread-safe" wording (pins the reworded claim against the
  class object, not just the file text).
- **`allows_agent` guard path** (secondary hole, same module): agent in neither
  dict → `True` (default-allow); agent in `disallowed` → `False`; agent in
  `allowed` with value `False` → still `True` (pins that the dict *value* is
  ignored — only key membership matters).
- **`get` lazy-expiry**: an expired entry is deleted on `get` (subsequent
  `get` returns `None` and `size` drops by one).

## Docs update (same PR)

`docs/robots-cache.md` (new) documents the full public API and lists this as
Contract Hole 1; `docs/README.md` gains the robots-cache index line under
"Core subsystems".
