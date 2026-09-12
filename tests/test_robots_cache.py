"""Tests for the robots.txt cache module."""

import threading
import time

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


class TestRobotsCacheThreadSafety:
    """Pinning tests for the 'Thread-safe' docstring claim (ARCH-32, Option A)."""

    def test_concurrent_put_get_invalidate_no_lost_updates(self):
        """N threads hammer put/get/invalidate on a shared small cache.

        Asserts no exception (no KeyError), size never exceeds max_entries,
        and no lost updates (every domain that survives is retrievable).
        """
        max_entries = 8
        cache = RobotsCache(ttl=3600, max_entries=max_entries)
        n_threads = 16
        ops_per_thread = 200
        errors: list[BaseException] = []
        size_violations: list[int] = []

        def worker(tid: int) -> None:
            try:
                for i in range(ops_per_thread):
                    domain = f"domain{tid}-{i % 5}.com"
                    cache.put(RobotsCacheEntry(domain=domain))
                    cache.get(domain)
                    if i % 10 == 0:
                        cache.invalidate(domain)
                    # size must never exceed max_entries under the lock
                    if cache.size > max_entries:
                        size_violations.append(cache.size)
            except BaseException as exc:  # noqa: BLE001 - record any failure
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"concurrent access raised: {errors}"
        assert not size_violations, f"size exceeded max_entries: {size_violations}"
        assert cache.size <= max_entries
        # No lost updates: every domain currently in the cache is retrievable.
        for domain in cache.domains:
            assert cache.get(domain) is not None

    def test_concurrent_put_respects_max_entries(self):
        """Concurrent puts never let the cache grow past max_entries."""
        max_entries = 5
        cache = RobotsCache(ttl=3600, max_entries=max_entries)
        n_threads = 8
        errors: list[BaseException] = []

        def worker(tid: int) -> None:
            try:
                for i in range(100):
                    cache.put(RobotsCacheEntry(domain=f"d{tid}-{i}.com"))
            except BaseException as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(t,)) for t in range(n_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"concurrent put raised: {errors}"
        assert cache.size <= max_entries


class TestAllowsAgentGuard:
    """Pinning tests for the allows_agent key-membership contract (ARCH-32)."""

    def test_agent_in_neither_dict_is_allowed(self):
        entry = RobotsCacheEntry(domain="example.com")
        entry.allowed = {}
        entry.disallowed = {}
        assert entry.allows_agent("UnknownBot") is True

    def test_agent_in_disallowed_is_denied(self):
        entry = RobotsCacheEntry(domain="example.com")
        entry.disallowed = {"BadBot": True}
        assert entry.allows_agent("BadBot") is False

    def test_agent_in_allowed_value_false_still_allowed(self):
        """Only key membership matters; the dict value is ignored."""
        entry = RobotsCacheEntry(domain="example.com")
        entry.allowed = {"WeirdBot": False}
        assert entry.allows_agent("WeirdBot") is True


class TestGetLazyExpiry:
    """Pinning test for get() lazy-expiry (ARCH-32)."""

    def test_expired_entry_deleted_on_get(self):
        cache = RobotsCache(ttl=1)
        entry = RobotsCacheEntry(domain="example.com")
        entry.fetched_at = time.time() - 2
        cache.put(entry)
        assert cache.size == 1
        # First get on an expired entry deletes it and returns None.
        assert cache.get("example.com") is None
        assert cache.size == 0
        # Subsequent get also returns None (entry is gone).
        assert cache.get("example.com") is None
        assert cache.size == 0
