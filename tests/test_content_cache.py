"""Tests for the content cache module."""

import time
from pathlib import Path

import pytest

from personal_index.content_cache import (
    CacheEntry,
    CacheStats,
    FileCache,
    MemoryCache,
)


class TestCacheEntry:
    def test_create(self) -> None:
        entry = CacheEntry(
            key="test",
            value="data",
            created_at=time.time(),
        )
        assert entry.key == "test"
        assert entry.access_count == 0


class TestCacheStats:
    def test_hit_rate_zero(self) -> None:
        stats = CacheStats()
        assert stats.hit_rate == 0.0

    def test_hit_rate_perfect(self) -> None:
        stats = CacheStats(hits=10, misses=0)
        assert stats.hit_rate == 1.0

    def test_hit_rate_half(self) -> None:
        stats = CacheStats(hits=5, misses=5)
        assert stats.hit_rate == 0.5


class TestMemoryCache:
    def setup_method(self) -> None:
        self.cache = MemoryCache(max_size=5)

    def test_set_and_get(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.get("key1") == "value1"

    def test_get_default(self) -> None:
        assert self.cache.get("nonexistent") is None
        assert self.cache.get("nonexistent", "default") == "default"

    def test_delete(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.delete("key1") is True
        assert self.cache.get("key1") is None

    def test_delete_nonexistent(self) -> None:
        assert self.cache.delete("nonexistent") is False

    def test_clear(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        self.cache.clear()
        assert self.cache.size() == 0

    def test_has(self) -> None:
        self.cache.set("key1", "value1")
        assert self.cache.has("key1") is True
        assert self.cache.has("nonexistent") is False

    def test_lru_eviction(self) -> None:
        for i in range(6):
            self.cache.set(f"key{i}", f"value{i}")
        # First key should be evicted
        assert self.cache.get("key0") is None
        assert self.cache.get("key5") == "value5"

    def test_lru_access_updates_order(self) -> None:
        cache = MemoryCache(max_size=3)
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.set("key3", "value3")
        # Access key1 to make it recently used
        cache.get("key1")
        # Add more to trigger eviction
        cache.set("key4", "value4")
        # key2 should be evicted (least recently used)
        assert cache.get("key2") is None
        assert cache.get("key1") == "value1"

    def test_ttl_expiry(self) -> None:
        self.cache.set("key1", "value1", ttl=0.1)
        assert self.cache.get("key1") == "value1"
        time.sleep(0.15)
        assert self.cache.get("key1") is None

    def test_default_ttl(self) -> None:
        cache = MemoryCache(default_ttl=0.1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None

    def test_access_count(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.get("key1")
        self.cache.get("key1")
        entry = self.cache._store["key1"]
        assert entry.access_count == 2

    def test_stats(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.get("key1")  # hit
        self.cache.get("missing")  # miss
        stats = self.cache.get_stats()
        assert stats.hits == 1
        assert stats.misses == 1
        assert stats.hit_rate == 0.5

    def test_keys(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key2", "value2")
        keys = self.cache.keys()
        assert set(keys) == {"key1", "key2"}

    def test_update_existing_key(self) -> None:
        self.cache.set("key1", "value1")
        self.cache.set("key1", "value2")
        assert self.cache.get("key1") == "value2"
        assert self.cache.size() == 1

    def test_complex_values(self) -> None:
        data = {"nested": {"key": [1, 2, 3]}}
        self.cache.set("complex", data)
        result = self.cache.get("complex")
        assert result == data


class TestFileCache:
    def test_set_and_get(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", {"data": "value"})
        result = cache.get("key1")
        assert result == {"data": "value"}

    def test_get_default(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        assert cache.get("nonexistent") is None
        assert cache.get("nonexistent", "default") == "default"

    def test_delete(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_clear(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache")
        cache.set("key1", "value1")
        cache.set("key2", "value2")
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_cleanup_expired(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache", default_ttl=0.1)
        cache.set("key1", "value1")
        cache.set("key2", "value2", ttl=3600)
        time.sleep(0.15)
        removed = cache.cleanup_expired()
        assert removed == 1
        assert cache.get("key2") == "value2"

    def test_ttl_expiry(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path / "cache", default_ttl=0.1)
        cache.set("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.15)
        assert cache.get("key1") is None
