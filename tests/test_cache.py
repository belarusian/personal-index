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
