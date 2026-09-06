# TICKET-547: Add CacheStore.get / set / has exact-contract docstrings + pinning test

Status: RESOLVED (merged via PR #971, issue #969 closed; merge commit 2bcb06b)
Module: personal_index/content_cache/cache_store.py
Methods: CacheStore.get, CacheStore.set, CacheStore.has
Type: (a) public methods lacking an exact-contract docstring + pinning test

## Symptom
The three docstrings are terse one-line stubs that omit the exact contract the code
actually delivers.

get (line 42) says only "Get a value from the cache" / "Cached value or default"
and omits:
  (1) an entry whose TTL has elapsed is treated as a miss: get returns the
      default (or None) rather than the stored value;
  (2) a miss on an EXPIRED entry lazily deletes the entry from the store
      (del self._entries[key]), so a subsequent has()/size() no longer sees it;
  (3) a hit increments the entry's access_count and refreshes last_accessed
      (used by LRU eviction).

set (line 62) says only "Set a value in the cache" and omits:
  (1) when ttl is None the entry inherits self.default_ttl (not "no expiry");
  (2) after inserting, if the store exceeds max_size the least-recently-used
      entry (min last_accessed) is evicted via _evict_lru.

has (line 103) says only "Check if a key exists and is not expired" and omits:
  (1) a miss on an EXPIRED entry lazily deletes the entry (del self._entries[key]),
      so the store shrinks as a side effect of a read.

## Evidence (verified live)
  get expired -> returns default; after that get, has() is False and size() is 0
  (lazy deletion). get hit -> access_count 0 -> 1. set with default_ttl=99.0 and
  ttl=None -> entry.ttl == 99.0. set with max_size=2 after touching 'a' then
  adding 'c' -> keys ['a','c'] (LRU 'b' evicted). has expired -> False and
  size() drops to 0 (lazy deletion).

## Existing coverage
tests/test_cache_store.py pins access_count, has_expired, ttl_expiry,
max_size_eviction, and the happy/missing/default cases, but does NOT pin the
lazy-deletion side effect of get/has, the default_ttl fallback in set, or the
docstring contract phrases.

## Minimal additive fix
Reword the three docstrings to state the exact contract (expired-entry miss +
lazy deletion + access tracking for get; default_ttl fallback + LRU eviction for
set; lazy deletion on expired miss for has). Add a pinning test class
TestCacheStoreDocstring547 asserting the key contract phrases appear in the
docstrings AND re-pinning the non-obvious behaviors (lazy deletion after an
expired get/has, default_ttl fallback, LRU eviction).

Issue: #969
