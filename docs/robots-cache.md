# robots_cache — Exact Contract

Module: `personal_index/robots_cache.py` (131 lines)

Caching layer for robots.txt parsing results. Two public types:
`RobotsCacheEntry` (a single cached parse result) and `RobotsCache`
(a bounded in-memory store keyed by domain).

## Public API

### RobotsCacheEntry (dataclass)

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| domain | str | (required) | The domain this entry was fetched for |
| allowed | dict[str, bool] | `{}` | user-agent → allow flag (see `allows_agent`) |
| disallowed | dict[str, bool] | `{}` | user-agent → disallow flag (see `allows_agent`) |
| crawl_delay | float \| None | `None` | robots.txt `Crawl-delay` if present |
| sitemap_urls | list[str] | `[]` | Sitemap URLs found in the robots.txt |
| fetched_at | float | `time.time()` | epoch seconds when the entry was created |
| raw_content | str | `""` | raw robots.txt body (may be empty) |

#### Methods

- `is_expired(ttl: float) -> bool`
  Returns `True` iff `(time.time() - self.fetched_at) > ttl`. Strictly greater:
  an entry exactly `ttl` seconds old is **not** expired.

- `allows_agent(user_agent: str) -> bool`
  Returns `True` if `user_agent in self.allowed`, else `user_agent not in
  self.disallowed`. **Default-allow**: an agent listed in neither dict is
  allowed. See Contract Hole 2 — the dict *values* are ignored.

### RobotsCache

`__init__(self, ttl: float = 3600, max_entries: int = 1000)`
Creates an empty store. `ttl` is the per-entry time-to-live in seconds;
`max_entries` is the capacity bound enforced by `put`.

- `get(domain: str) -> RobotsCacheEntry | None`
  Returns the entry for `domain`, or `None` if absent **or expired**.
  **Side effect**: if the entry is expired it is **deleted** from the cache
  (lazy eviction) before returning `None`.

- `put(entry: RobotsCacheEntry) -> None`
  Stores `entry` keyed by `entry.domain`. **Side effect**: if the cache is at
  capacity (`len >= max_entries`) it first evicts the single oldest entry via
  `_evict_oldest()`, then inserts. Re-putting an existing domain overwrites it
  (no capacity bump).

- `invalidate(domain: str) -> bool`
  Removes `domain` if present. Returns `True` if it was found and removed,
  `False` if absent.

- `invalidate_all() -> None`
  Clears every entry.

- `_evict_oldest() -> None` (private)
  Removes the entry with the minimum `fetched_at`. No-op if the cache is empty.
  Eviction is by **insertion time** (`fetched_at`), not by last-access — this is
  FIFO-by-creation, not LRU (see Contract Hole 3).

- `size` — **`@property`**, `-> int`. Number of entries. Access as
  `cache.size`, **not** `cache.size()`.

- `domains` — **`@property`**, `-> list[str]`. A fresh list of all cached
  domains (insertion order). Access as `cache.domains`, **not** `cache.domains()`.

- `get_stats() -> dict`
  Returns `{"size": int, "ttl": float, "max_entries": int, "domains": list[str]}`.

## Contract Holes

### 1. "Thread-safe" claim with no locking (ARCH-32)

The class docstring reads **"Thread-safe cache for robots.txt results."** but
the module imports only `logging`, `time`, and `dataclasses` — there is **no
`threading` import and no lock anywhere**. Every mutating path is a
non-atomic read-modify-write:

- `get()`: `entry = self._cache.get(domain)` … `del self._cache[domain]`
  (read-then-delete).
- `put()`: `if len(self._cache) >= self._max_entries: self._evict_oldest()`
  then `self._cache[entry.domain] = entry` (len-check → evict → set).
- `_evict_oldest()`: `min(...)` then `del ...`.

Under concurrent access these can race (two threads both see `len ==
max_entries` and both evict, or a `get` deletes an entry another thread just
`put`). The "Thread-safe" claim is a **false over-promise**.

**Decision (for the implementer)**: either (a) add a `threading.Lock` around
every public method body and keep the claim, or (b) reword the docstring to
state the cache is **not** thread-safe and the caller must serialize access.
The contract must match the code.

### 2. `allows_agent` ignores the dict values

`allowed` and `disallowed` are typed `dict[str, bool]`, implying the boolean
value carries meaning. `allows_agent` only checks **key membership**:
`user_agent in self.allowed` / `user_agent not in self.disallowed`. A value of
`False` in `allowed` still returns `True` (allowed), and a value of `True` in
`disallowed` still returns `False` (disallowed) — the value is never read. The
`bool` in the type is misleading; the dicts are effectively `set[str]`.

### 3. Eviction is FIFO-by-creation, not LRU

`_evict_oldest` evicts by minimum `fetched_at` (insertion time). A frequently
`get`-accessed entry is evicted just as readily as a cold one, because `get`
never refreshes `fetched_at`. The name "oldest" is accurate for creation order
but the cache is not a least-recently-used cache.

## Pinning Tests (for ARCH-32)

- Thread-safety: either a concurrency test that exercises `put`/`get` from
  multiple threads and asserts no lost updates / no `KeyError` (if the fix adds
  a lock), or a docstring-assertion test pinning the corrected "not
  thread-safe" claim (if the fix rewords the docstring).
- `allows_agent` guard path: an agent in neither dict → `True` (default-allow);
  an agent in `disallowed` → `False`; an agent in `allowed` with value `False`
  → still `True` (pins Contract Hole 2).
- `get` lazy-expiry: an expired entry is deleted on `get` (subsequent `get`
  returns `None` and `size` drops by one).
