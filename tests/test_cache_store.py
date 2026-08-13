"""Tests for cache store."""

import time

from personal_index.content_cache.cache_store import CacheStore


class TestCacheStore:
    def test_set_and_get(self):
        c = CacheStore()
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_get_missing(self):
        c = CacheStore()
        assert c.get("missing") is None

    def test_get_default(self):
        c = CacheStore()
        assert c.get("missing", "default") == "default"

    def test_delete(self):
        c = CacheStore()
        c.set("key1", "value1")
        assert c.delete("key1") is True
        assert c.get("key1") is None

    def test_delete_missing(self):
        c = CacheStore()
        assert c.delete("missing") is False

    def test_clear(self):
        c = CacheStore()
        c.set("k1", "v1")
        c.set("k2", "v2")
        c.clear()
        assert c.size() == 0

    def test_has(self):
        c = CacheStore()
        c.set("key1", "value1")
        assert c.has("key1") is True
        assert c.has("missing") is False

    def test_keys(self):
        c = CacheStore()
        c.set("a", 1)
        c.set("b", 2)
        k = c.keys()
        assert "a" in k
        assert "b" in k

    def test_size(self):
        c = CacheStore()
        assert c.size() == 0
        c.set("k1", "v1")
        assert c.size() == 1

    def test_ttl_expiry(self):
        c = CacheStore(default_ttl=None)
        c.set("key1", "value1", ttl=0.1)
        time.sleep(0.2)
        assert c.get("key1") is None

    def test_no_ttl(self):
        c = CacheStore(default_ttl=None)
        c.set("key1", "value1")
        assert c.get("key1") == "value1"

    def test_max_size_eviction(self):
        c = CacheStore(max_size=2, default_ttl=None)
        c.set("a", 1)
        time.sleep(0.01)
        c.set("b", 2)
        time.sleep(0.01)
        c.set("c", 3)
        assert "a" not in c.keys()

    def test_access_count(self):
        c = CacheStore(default_ttl=None)
        c.set("key1", "value1")
        c.get("key1")
        c.get("key1")
        entry = c._entries["key1"]
        assert entry.access_count == 2

    def test_has_expired(self):
        c = CacheStore(default_ttl=None)
        c.set("key1", "value1", ttl=0.1)
        time.sleep(0.2)
        assert c.has("key1") is False
