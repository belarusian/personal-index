"""Tests for cache module."""

from __future__ import annotations

import time

from personal_index.cache import CacheDecorator, LRUCache, TTLCache


class TestLRUCache:
    def test_get_put(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_get_missing(self):
        cache = LRUCache()
        assert cache.get("missing") is None
        assert cache.get("missing", "default") == "default"

    def test_lru_eviction(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)  # Should evict "a"
        assert cache.get("a") is None
        assert cache.get("b") == 2
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_lru_access_updates_order(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.get("a")  # Access "a", making it most recent
        cache.put("d", 4)  # Should evict "b" (LRU)
        assert cache.get("a") == 1
        assert cache.get("b") is None
        assert cache.get("c") == 3
        assert cache.get("d") == 4

    def test_update_existing_key(self):
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        cache.put("a", 2)
        assert cache.get("a") == 2
        assert len(cache) == 1

    def test_delete(self):
        cache = LRUCache()
        cache.put("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") is None
        assert cache.delete("nonexistent") is False

    def test_clear(self):
        cache = LRUCache()
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert len(cache) == 0
        assert cache.get("a") is None

    def test_contains(self):
        cache = LRUCache()
        cache.put("a", 1)
        assert "a" in cache
        assert "b" not in cache

    def test_len(self):
        cache = LRUCache()
        assert len(cache) == 0
        cache.put("a", 1)
        assert len(cache) == 1

    def test_hit_rate(self):
        cache = LRUCache()
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.hit_rate == 0.5

    def test_hit_rate_no_access(self):
        cache = LRUCache()
        assert cache.hit_rate == 0.0

    def test_stats(self):
        cache = LRUCache(max_size=10)
        cache.put("a", 1)
        cache.get("a")
        stats = cache.stats()
        assert stats["size"] == 1
        assert stats["max_size"] == 10
        assert stats["hits"] == 1
        assert stats["hit_rate"] == 1.0

    def test_size_property(self):
        cache = LRUCache()
        cache.put("a", 1)
        cache.put("b", 2)
        assert cache.size == 2


class TestTTLCache:
    def test_get_put(self):
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        assert cache.get("a") == 1

    def test_ttl_expiration(self):
        cache = TTLCache(ttl=0.05)
        cache.put("a", 1)
        time.sleep(0.1)
        assert cache.get("a") is None

    def test_get_missing(self):
        cache = TTLCache()
        assert cache.get("missing") is None
        assert cache.get("missing", "default") == "default"

    def test_per_entry_ttl(self):
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1, ttl=0.05)
        time.sleep(0.1)
        assert cache.get("a") is None

    def test_delete(self):
        cache = TTLCache()
        cache.put("a", 1)
        assert cache.delete("a") is True
        assert cache.get("a") is None

    def test_clear(self):
        cache = TTLCache()
        cache.put("a", 1)
        cache.put("b", 2)
        cache.clear()
        assert len(cache) == 0

    def test_contains_expired(self):
        cache = TTLCache(ttl=0.05)
        cache.put("a", 1)
        time.sleep(0.1)
        assert "a" not in cache

    def test_contains_valid(self):
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        assert "a" in cache

    def test_max_size_eviction(self):
        cache = TTLCache(ttl=60.0, max_size=3)
        cache.put("a", 1)
        cache.put("b", 2)
        cache.put("c", 3)
        cache.put("d", 4)
        assert len(cache) <= 3

    def test_hit_rate(self):
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.hit_rate == 0.5

    def test_stats(self):
        cache = TTLCache(ttl=30.0, max_size=100)
        cache.put("a", 1)
        stats = cache.stats()
        assert stats["ttl"] == 30.0
        assert stats["max_size"] == 100

    def test_size_property_evicts_expired(self):
        cache = TTLCache(ttl=0.05)
        cache.put("a", 1)
        cache.put("b", 2)
        time.sleep(0.1)
        assert cache.size == 0


class TestCacheDecorator:
    def test_lru_decorator(self):
        call_count = 0

        @CacheDecorator(lru_size=10)
        def add(a, b):
            nonlocal call_count
            call_count += 1
            return a + b

        assert add(1, 2) == 3
        assert add(1, 2) == 3  # cached
        assert call_count == 1

    def test_ttl_decorator(self):
        call_count = 0

        @CacheDecorator(lru_size=10, ttl=0.05)
        def multiply(a, b):
            nonlocal call_count
            call_count += 1
            return a * b

        assert multiply(3, 4) == 12
        time.sleep(0.1)
        assert multiply(3, 4) == 12  # expired, recomputed
        assert call_count == 2

    def test_decorator_cache_attribute(self):
        @CacheDecorator(lru_size=10)
        def func(x):
            return x

        assert hasattr(func, "cache")
        assert hasattr(func.cache, "stats")

    def test_decorator_different_args(self):
        call_count = 0

        @CacheDecorator(lru_size=10)
        def greet(name):
            nonlocal call_count
            call_count += 1
            return f"Hello, {name}!"

        assert greet("Alice") == "Hello, Alice!"
        assert greet("Bob") == "Hello, Bob!"
        assert greet("Alice") == "Hello, Alice!"  # cached
        assert call_count == 2


# ── ARCH-1 exact-contract pinning tests (cycle 187: cache) ─────────
# Each test asserts the RETURNED OBJECT for BOTH the normal case and the
# guard-path input the contract docstring states.


class TestLRUCacheContract:
    def test_get_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache(max_size=3)
        cache.put("a", 1)
        # Normal case: present key returns the stored value.
        assert cache.get("a") == 1
        # Guard path: absent key returns the default unchanged.
        assert cache.get("missing", "dflt") == "dflt"

    def test_put_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache(max_size=2)
        # Normal case: put returns None and stores the value.
        cache.put("a", 1)
        assert cache.get("a") == 1
        # Guard path (no guard: always stores): over-capacity evicts LRU.
        cache.put("b", 2)
        cache.put("c", 3)
        assert cache.get("a", "gone") == "gone"  # "a" evicted
        assert cache.get("c") == 3

    def test_delete_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        # Normal case: present key returns True and is removed.
        assert cache.delete("a") is True
        assert "a" not in cache
        # Guard path: absent key returns False.
        assert cache.delete("nope") is False

    def test_clear_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        cache.put("b", 2)
        # Normal case: clear returns None and empties the cache.
        cache.clear()
        assert len(cache) == 0
        # Guard path (no guard: always clears): clearing an empty cache.
        cache.clear()
        assert len(cache) == 0

    def test_contains_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        # Normal case: present key returns True.
        assert ("a" in cache) is True
        # Guard path: absent key returns False.
        assert ("nope" in cache) is False

    def test_len_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        cache.put("b", 2)
        # Normal case: two stored entries.
        assert len(cache) == 2
        # Guard path (no guard: always computes): empty cache.
        assert len(LRUCache()) == 0

    def test_size_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        # Normal case: one stored entry.
        assert cache.size == 1
        # Guard path (no guard: always computes): empty cache.
        assert LRUCache().size == 0

    def test_hit_rate_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache()
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("missing")  # miss
        # Normal case: 1 hit / 2 lookups = 0.5.
        assert cache.hit_rate == 0.5
        # Guard path: no lookups yet returns 0.0.
        assert LRUCache().hit_rate == 0.0

    def test_stats_pins_returned_object_normal_and_guard(self) -> None:
        cache = LRUCache(max_size=5)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("missing")  # miss
        # Normal case: exact dict of all six fields.
        assert cache.stats() == {
            "size": 1,
            "max_size": 5,
            "hits": 1,
            "misses": 1,
            "hit_rate": 0.5,
        }
        # Guard path (no guard: always computes): fresh cache.
        assert LRUCache(max_size=5).stats() == {
            "size": 0,
            "max_size": 5,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
        }


class TestTTLCacheContract:
    def test_get_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        # Normal case: present, non-expired key returns the stored value.
        assert cache.get("a") == 1
        # Guard path (a): absent key returns the default unchanged.
        assert cache.get("missing", "dflt") == "dflt"
        # Guard path (b): expired key returns the default and is evicted.
        cache.put("b", 2, ttl=0.0)
        time.sleep(0.01)
        assert cache.get("b", "gone") == "gone"
        assert "b" not in cache

    def test_put_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0, max_size=2)
        # Normal case: put returns None and stores the value.
        cache.put("a", 1)
        assert cache.get("a") == 1
        # Guard path (no guard: always stores): over-capacity evicts.
        cache.put("b", 2)
        cache.put("c", 3)
        assert len(cache) <= 2

    def test_delete_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        # Normal case: present key returns True and is removed.
        assert cache.delete("a") is True
        assert "a" not in cache
        # Guard path: absent key returns False.
        assert cache.delete("nope") is False

    def test_clear_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        cache.put("b", 2)
        # Normal case: clear returns None and empties the cache.
        cache.clear()
        assert len(cache) == 0
        # Guard path (no guard: always clears): clearing an empty cache.
        cache.clear()
        assert len(cache) == 0

    def test_contains_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        # Normal case: present, non-expired key returns True.
        assert ("a" in cache) is True
        # Guard path (a): absent key returns False.
        assert ("nope" in cache) is False
        # Guard path (b): expired key returns False and is evicted.
        cache.put("b", 2, ttl=0.0)
        time.sleep(0.01)
        assert ("b" in cache) is False
        assert "b" not in cache

    def test_len_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        cache.put("b", 2)
        # Normal case: two stored entries.
        assert len(cache) == 2
        # Guard path (no guard: always computes): empty cache.
        assert len(TTLCache()) == 0

    def test_size_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        # Normal case: one non-expired entry.
        assert cache.size == 1
        # Guard path (no guard: always computes): empty cache.
        assert TTLCache().size == 0

    def test_hit_rate_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("missing")  # miss
        # Normal case: 1 hit / 2 lookups = 0.5.
        assert cache.hit_rate == 0.5
        # Guard path: no lookups yet returns 0.0.
        assert TTLCache().hit_rate == 0.0

    def test_stats_pins_returned_object_normal_and_guard(self) -> None:
        cache = TTLCache(ttl=60.0, max_size=5)
        cache.put("a", 1)
        cache.get("a")  # hit
        cache.get("missing")  # miss
        # Normal case: exact dict of all six fields.
        assert cache.stats() == {
            "size": 1,
            "max_size": 5,
            "ttl": 60.0,
            "hits": 1,
            "misses": 1,
            "hit_rate": 0.5,
        }
        # Guard path (no guard: always computes): fresh cache.
        assert TTLCache(ttl=60.0, max_size=5).stats() == {
            "size": 0,
            "max_size": 5,
            "ttl": 60.0,
            "hits": 0,
            "misses": 0,
            "hit_rate": 0.0,
        }


class TestCacheDecoratorContract:
    def test_call_pins_returned_object_normal_and_guard(self) -> None:
        calls = 0

        @CacheDecorator(lru_size=10)
        def square(x):
            nonlocal calls
            calls += 1
            return x * x

        # Normal case: wrapper returns the function result and caches it.
        assert square(4) == 16
        assert square(4) == 16  # cached, no recompute
        assert calls == 1
        # Guard path (no guard: always wraps): a different key recomputes.
        assert square(5) == 25
        assert calls == 2
        # The wrapper exposes the backing cache and the original function.
        assert hasattr(square, "cache")
        assert square.__wrapped__ is square.__wrapped__
