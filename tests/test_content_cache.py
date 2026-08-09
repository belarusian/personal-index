"""Tests for content_cache module."""

from __future__ import annotations

import time
import pytest
from personal_index.content_cache import ContentCache, CacheEntry


class TestCacheEntry:
    def test_entry_not_expired(self):
        entry = CacheEntry(value="test", ttl=3600.0)
        assert not entry.is_expired

    def test_entry_expired(self):
        entry = CacheEntry(value="test", created_at=time.monotonic() - 100, ttl=10.0)
        assert entry.is_expired

    def test_entry_age(self):
        entry = CacheEntry(value="test")
        time.sleep(0.05)
        assert entry.age >= 0.05

    def test_entry_access_count(self):
        entry = CacheEntry(value="test")
        assert entry.access_count == 0


class TestContentCacheInit:
    def test_default_init(self):
        cache = ContentCache()
        assert cache.max_size == 1000
        assert cache.default_ttl == 3600.0
        assert cache.size == 0

    def test_custom_init(self):
        cache = ContentCache(max_size=500, default_ttl=1800.0)
        assert cache.max_size == 500
        assert cache.default_ttl == 1800.0
        assert cache.size == 0


class TestContentCachePutGet:
    def test_put_and_get(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"

    def test_get_missing_key(self):
        cache = ContentCache()
        assert cache.get("missing") is None

    def test_get_missing_key_with_default(self):
        cache = ContentCache()
        assert cache.get("missing", "default") == "default"

    def test_put_overwrites(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        cache.put("key1", "value2")
        assert cache.get("key1") == "value2"

    def test_put_with_custom_ttl(self):
        cache = ContentCache()
        cache.put("key1", "value1", ttl=100.0)
        assert cache.get("key1") == "value1"

    def test_put_with_operation(self):
        cache = ContentCache()
        cache.put("key1", "value1", operation="extract")
        assert cache.get("key1") == "value1"


class TestContentCacheTTL:
    def test_ttl_expiration(self):
        cache = ContentCache(default_ttl=0.05)
        cache.put("key1", "value1")
        assert cache.get("key1") == "value1"
        time.sleep(0.1)
        assert cache.get("key1") is None

    def test_custom_ttl_expiration(self):
        cache = ContentCache()
        cache.put("key1", "value1", ttl=0.05)
        assert cache.get("key1") == "value1"
        time.sleep(0.1)
        assert cache.get("key1") is None


class TestContentCacheDelete:
    def test_delete_existing(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        assert cache.delete("key1") is True
        assert cache.get("key1") is None

    def test_delete_missing(self):
        cache = ContentCache()
        assert cache.delete("missing") is False


class TestContentCacheClear:
    def test_clear(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        cache.clear()
        assert cache.size == 0
        assert cache.get("key1") is None


class TestContentCacheSize:
    def test_len(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        cache.put("key2", "value2")
        assert len(cache) == 2

    def test_size_property(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        assert cache.size == 1

    def test_contains(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        assert "key1" in cache
        assert "missing" not in cache

    def test_max_size_eviction(self):
        cache = ContentCache(max_size=3)
        cache.put("key1", "v1")
        cache.put("key2", "v2")
        cache.put("key3", "v3")
        cache.put("key4", "v4")
        assert len(cache) == 3
        assert cache.get("key1") is None  # evicted


class TestContentCacheStats:
    def test_hit_rate(self):
        cache = ContentCache()
        cache.put("key1", "value1")
        cache.get("key1")
        cache.get("missing")
        assert cache.hit_rate == 0.5

    def test_stats_dict(self):
        cache = ContentCache(max_size=100, default_ttl=600.0)
        stats = cache.stats()
        assert stats["max_size"] == 100
        assert stats["default_ttl"] == 600.0
        assert "hits" in stats
        assert "misses" in stats
        assert "evictions" in stats


class TestContentCacheGetOrCompute:
    def test_get_or_compute_miss(self):
        cache = ContentCache()
        call_count = [0]
        def compute():
            call_count[0] += 1
            return "computed"
        result = cache.get_or_compute("key1", compute)
        assert result == "computed"
        assert call_count[0] == 1

    def test_get_or_compute_hit(self):
        cache = ContentCache()
        call_count = [0]
        def compute():
            call_count[0] += 1
            return "computed"
        cache.get_or_compute("key1", compute)
        cache.get_or_compute("key1", compute)
        assert call_count[0] == 1


class TestContentCacheKeyGeneration:
    def test_generate_key(self):
        cache = ContentCache()
        key = cache.generate_key("extract", "url1", format="html")
        assert isinstance(key, str)
        assert len(key) > 0

    def test_generate_key_consistent(self):
        cache = ContentCache()
        key1 = cache.generate_key("extract", "url1", format="html")
        key2 = cache.generate_key("extract", "url1", format="html")
        assert key1 == key2

    def test_generate_key_different_args(self):
        cache = ContentCache()
        key1 = cache.generate_key("extract", "url1")
        key2 = cache.generate_key("extract", "url2")
        assert key1 != key2


class TestCacheDecorator:
    def test_decorator_caches_result(self):
        from personal_index.content_cache import CacheDecorator
        call_count = [0]

        @CacheDecorator(ttl=60.0)
        def expensive_op(x):
            call_count[0] += 1
            return x * 2

        assert expensive_op(5) == 10
        assert expensive_op(5) == 10
        assert call_count[0] == 1

    def test_decorator_different_args(self):
        from personal_index.content_cache import CacheDecorator
        call_count = [0]

        @CacheDecorator(ttl=60.0)
        def expensive_op(x):
            call_count[0] += 1
            return x * 2

        assert expensive_op(5) == 10
        assert expensive_op(3) == 6
        assert call_count[0] == 2

    def test_decorator_ttl_expiration(self):
        from personal_index.content_cache import CacheDecorator
        call_count = [0]

        @CacheDecorator(ttl=0.05)
        def expensive_op(x):
            call_count[0] += 1
            return x * 2

        assert expensive_op(5) == 10
        time.sleep(0.1)
        assert expensive_op(5) == 10
        assert call_count[0] == 2

    def test_decorator_cache_property(self):
        from personal_index.content_cache import CacheDecorator

        @CacheDecorator(ttl=60.0)
        def my_func(x):
            return x

        assert my_func.cache is not None
        assert isinstance(my_func.cache, ContentCache)

    def test_decorator_wrapped_attribute(self):
        from personal_index.content_cache import CacheDecorator

        @CacheDecorator(ttl=60.0)
        def my_func(x):
            return x

        assert hasattr(my_func, '__wrapped__')
