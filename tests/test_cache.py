"""Tests for the cache module."""

import os
import time
import pytest
from personal_index.cache import Cache, CacheEntry


class TestCacheEntry:
    def test_create_entry(self):
        entry = CacheEntry(url="https://example.com", content="Hello")
        assert entry.url == "https://example.com"
        assert entry.content == "Hello"

    def test_not_expired(self):
        entry = CacheEntry(
            url="https://example.com",
            content="Hello",
            cached_at=time.time(),
            expires_at=time.time() + 3600,
        )
        assert entry.is_expired() is False

    def test_expired(self):
        entry = CacheEntry(
            url="https://example.com",
            content="Hello",
            cached_at=time.time() - 7200,
            expires_at=time.time() - 3600,
        )
        assert entry.is_expired() is True

    def test_no_expiry(self):
        entry = CacheEntry(url="https://example.com", content="Hello", expires_at=0)
        assert entry.is_expired() is False

    def test_to_dict_and_from_dict(self):
        entry = CacheEntry(
            url="https://example.com",
            content="Hello",
            etag="abc123",
        )
        data = entry.to_dict()
        restored = CacheEntry.from_dict(data)
        assert restored.url == "https://example.com"
        assert restored.etag == "abc123"


class TestCache:
    def test_create_cache(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        assert cache.hits == 0
        assert cache.misses == 0

    def test_put_and_get(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "<html>Hello</html>")
        entry = cache.get("https://example.com")
        assert entry is not None
        assert entry.content == "<html>Hello</html>"
        assert cache.hits == 1

    def test_get_nonexistent(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        entry = cache.get("https://nonexistent.com")
        assert entry is None
        assert cache.misses == 1

    def test_hit_rate(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "Hello")
        cache.get("https://example.com")  # hit
        cache.get("https://other.com")  # miss
        assert cache.hit_rate == 0.5

    def test_invalidate(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "Hello")
        cache.invalidate("https://example.com")
        assert cache.get("https://example.com") is None

    def test_clear(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://a.com", "A")
        cache.put("https://b.com", "B")
        cache.clear()
        assert len(cache._memory_cache) == 0
        assert cache.hits == 0
        assert cache.misses == 0
        # After clear, gets should return None and count as misses
        assert cache.get("https://a.com") is None
        assert cache.get("https://b.com") is None
        assert cache.misses == 2

    def test_ttl_expiry(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"), ttl=0)
        cache.put("https://example.com", "Hello")
        # TTL is 0, so it expires immediately
        time.sleep(0.01)
        entry = cache.get("https://example.com")
        assert entry is None

    def test_max_size_eviction(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"), max_size=2)
        cache.put("https://a.com", "A")
        cache.put("https://b.com", "B")
        cache.put("https://c.com", "C")  # Should evict oldest
        assert len(cache._memory_cache) <= 2

    def test_stats(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        stats = cache.stats()
        assert "memory_entries" in stats
        assert "hits" in stats
        assert "misses" in stats
        assert "hit_rate" in stats
        assert "ttl" in stats

    def test_content_type_stored(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "Hello", content_type="text/plain")
        entry = cache.get("https://example.com")
        assert entry.content_type == "text/plain"

    def test_status_code_stored(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "Hello", status_code=200)
        entry = cache.get("https://example.com")
        assert entry.status_code == 200

    def test_etag_stored(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        cache.put("https://example.com", "Hello", etag="abc123")
        entry = cache.get("https://example.com")
        assert entry.etag == "abc123"

    def test_persistence(self, tmp_path):
        cache_dir = str(tmp_path / "cache")
        cache = Cache(cache_dir=cache_dir)
        cache.put("https://example.com", "Hello")

        cache2 = Cache(cache_dir=cache_dir)
        entry = cache2.get("https://example.com")
        assert entry is not None
        assert entry.content == "Hello"

    def test_url_to_key_deterministic(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        key1 = cache._url_to_key("https://example.com")
        key2 = cache._url_to_key("https://example.com")
        assert key1 == key2

    def test_url_to_key_different(self, tmp_path):
        cache = Cache(cache_dir=str(tmp_path / "cache"))
        key1 = cache._url_to_key("https://a.com")
        key2 = cache._url_to_key("https://b.com")
        assert key1 != key2
