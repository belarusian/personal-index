"""Tests for content cache module."""

import time

from personal_index.content_cache.cache_policy import CachePolicy, EvictionPolicy
from personal_index.content_cache.cache_stats import CacheStats
from personal_index.content_cache.cache_store import CacheStore


class TestCacheStore:
    def test_set_and_get(self) -> None:
        store = CacheStore()
        store.set("key1", "value1")
        assert store.get("key1") == "value1"

    def test_get_missing(self) -> None:
        store = CacheStore()
        assert store.get("missing", "default") == "default"

    def test_delete(self) -> None:
        store = CacheStore()
        store.set("key1", "value1")
        assert store.delete("key1") is True
        assert store.get("key1") is None

    def test_delete_missing(self) -> None:
        store = CacheStore()
        assert store.delete("missing") is False

    def test_clear(self) -> None:
        store = CacheStore()
        store.set("key1", "value1")
        store.set("key2", "value2")
        store.clear()
        assert store.size() == 0

    def test_has(self) -> None:
        store = CacheStore()
        store.set("key1", "value1")
        assert store.has("key1") is True
        assert store.has("missing") is False

    def test_ttl_expiry(self) -> None:
        store = CacheStore(default_ttl=None)
        store.set("key1", "value1", ttl=0.05)
        assert store.get("key1") == "value1"
        time.sleep(0.1)
        assert store.get("key1") is None

    def test_max_size_eviction(self) -> None:
        store = CacheStore(max_size=2, default_ttl=None)
        store.set("key1", "v1")
        store.set("key2", "v2")
        store.set("key3", "v3")
        assert store.size() <= 2

    def test_keys(self) -> None:
        store = CacheStore(default_ttl=None)
        store.set("a", 1)
        store.set("b", 2)
        keys = store.keys()
        assert set(keys) == {"a", "b"}

    def test_size(self) -> None:
        store = CacheStore(default_ttl=None)
        store.set("a", 1)
        assert store.size() == 1


class TestCachePolicy:
    def test_defaults(self) -> None:
        policy = CachePolicy()
        assert policy.eviction_policy == EvictionPolicy.LRU
        assert policy.max_size == 1000
        assert policy.default_ttl == 3600.0

    def test_custom_policy(self) -> None:
        policy = CachePolicy(
            eviction_policy=EvictionPolicy.LFU,
            max_size=100,
        )
        assert policy.eviction_policy == EvictionPolicy.LFU
        assert policy.max_size == 100


class TestCacheStats:
    def test_hit_rate(self) -> None:
        stats = CacheStats(hits=8, misses=2)
        assert stats.hit_rate == 0.8

    def test_miss_rate(self) -> None:
        stats = CacheStats(hits=8, misses=2)
        assert stats.miss_rate == 0.2

    def test_zero_total(self) -> None:
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_reset(self) -> None:
        stats = CacheStats(hits=10, misses=5, sets=20)
        stats.reset()
        assert stats.hits == 0
        assert stats.misses == 0
        assert stats.sets == 0
