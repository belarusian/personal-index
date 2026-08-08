"""Tests for the robots.txt cache module."""

import time
import pytest
from personal_index.robots_cache import RobotsCache, RobotsCacheEntry


class TestRobotsCacheEntry:
    def test_default_values(self):
        entry = RobotsCacheEntry(domain="example.com")
        assert entry.domain == "example.com"
        assert entry.crawl_delay is None
        assert entry.sitemap_urls == []

    def test_is_expired(self):
        entry = RobotsCacheEntry(domain="example.com")
        entry.fetched_at = time.time() - 7200
        assert entry.is_expired(ttl=3600) is True
        # Use 7201 to account for tiny timing gap between setup and assertion
        assert entry.is_expired(ttl=7201) is False

    def test_allows_agent(self):
        entry = RobotsCacheEntry(domain="example.com")
        entry.allowed = {"*": True}
        entry.disallowed = {"BadBot": False}
        assert entry.allows_agent("*") is True
        assert entry.allows_agent("BadBot") is False
        assert entry.allows_agent("UnknownBot") is True

    def test_raw_content(self):
        entry = RobotsCacheEntry(domain="example.com", raw_content="User-agent: *")
        assert entry.raw_content == "User-agent: *"


class TestRobotsCache:
    def test_put_and_get(self):
        cache = RobotsCache()
        entry = RobotsCacheEntry(domain="example.com")
        cache.put(entry)
        result = cache.get("example.com")
        assert result is not None
        assert result.domain == "example.com"

    def test_get_missing(self):
        cache = RobotsCache()
        assert cache.get("nonexistent.com") is None

    def test_invalidate(self):
        cache = RobotsCache()
        cache.put(RobotsCacheEntry(domain="example.com"))
        assert cache.invalidate("example.com") is True
        assert cache.get("example.com") is None

    def test_invalidate_missing(self):
        cache = RobotsCache()
        assert cache.invalidate("nonexistent.com") is False

    def test_invalidate_all(self):
        cache = RobotsCache()
        cache.put(RobotsCacheEntry(domain="a.com"))
        cache.put(RobotsCacheEntry(domain="b.com"))
        cache.invalidate_all()
        assert cache.size == 0

    def test_ttl_expiry(self):
        cache = RobotsCache(ttl=1)
        entry = RobotsCacheEntry(domain="example.com")
        entry.fetched_at = time.time() - 2
        cache.put(entry)
        assert cache.get("example.com") is None

    def test_max_entries_eviction(self):
        cache = RobotsCache(max_entries=3)
        for i in range(5):
            entry = RobotsCacheEntry(domain=f"domain{i}.com")
            entry.fetched_at = time.time() - (5 - i)
            cache.put(entry)
        assert cache.size <= 3

    def test_size(self):
        cache = RobotsCache()
        assert cache.size == 0
        cache.put(RobotsCacheEntry(domain="a.com"))
        cache.put(RobotsCacheEntry(domain="b.com"))
        assert cache.size == 2

    def test_domains(self):
        cache = RobotsCache()
        cache.put(RobotsCacheEntry(domain="a.com"))
        cache.put(RobotsCacheEntry(domain="b.com"))
        assert "a.com" in cache.domains
        assert "b.com" in cache.domains

    def test_get_stats(self):
        cache = RobotsCache(ttl=1800)
        stats = cache.get_stats()
        assert stats["ttl"] == 1800
        assert stats["size"] == 0

    def test_evict_oldest(self):
        cache = RobotsCache(max_entries=2)
        e1 = RobotsCacheEntry(domain="old.com")
        e1.fetched_at = time.time() - 100
        e2 = RobotsCacheEntry(domain="new.com")
        e2.fetched_at = time.time()
        cache.put(e1)
        cache.put(e2)
        cache.put(RobotsCacheEntry(domain="extra.com"))
        assert cache.get("old.com") is None
        assert cache.get("new.com") is not None
