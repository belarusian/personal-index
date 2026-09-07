# Cache (`personal_index.cache`)

Status: **spec** — audited against current code (cycle 169).

## LRUCache
`LRUCache(max_size=128)`.
- `get(key, default=None) -> Any` — returns the value or `default`; updates
  recency (move-to-most-recent).
- `put(key, value)` — inserts/updates; evicts the least-recently-used entry
  when over `max_size`.
- `delete(key) -> bool` — True if present and removed.
- `clear()`, `__contains__`, `__len__`.
- `size` (property) -> int — current item count.
- `hit_rate` (property) -> float — hits / (hits + misses); 0.0 when no lookups.
- `stats() -> dict` — size, max_size, hits, misses, hit_rate.

## TTLCache
`TTLCache(ttl=300.0, max_size=1000)`.
- `get(key, default=None) -> Any` — returns the value if present and not
  expired (an expired entry is deleted and `default` returned); counts
  hits/misses.
- `put(key, value, ttl=None)` — per-entry TTL override (defaults to the
  cache-level `ttl`).
- `delete(key) -> bool`, `clear()`, `__contains__`, `__len__`.
- `size() -> int` — evicts expired entries first, then returns the count.
- `_evict_expired() -> int` — removes all expired entries, returns the count.
- `hit_rate` (property) -> float, `stats() -> dict`.

## CacheDecorator
`CacheDecorator(lru_size=128, ttl=None)` — a callable decorator factory; wraps
a function so repeated calls with the same args return the cached result.

## Contract holes
- None found this cycle. `LRUCache.get` / `set` / `has` docstrings were already
  reworded to exact-contract form in cycle 167.
