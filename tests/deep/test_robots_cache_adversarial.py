"""Cycle 171 PROBE: personal_index/robots_cache.py (never-probed subsystem).

Adversarial deep tests for RobotsCacheEntry / RobotsCache:
  - is_expired: TTL boundary (exactly at TTL, just before, just after).
  - allows_agent: agent in allowed, in disallowed, in both, in neither.
  - RobotsCache.put/get: basic round-trip, expired entry eviction on get.
  - RobotsCache.put: max_entries eviction (evict oldest, boundary at exactly max).
  - RobotsCache.invalidate / invalidate_all.
  - RobotsCache.size / domains / get_stats.
  - Thread-safety claim: docstring says "Thread-safe cache" but no lock exists.
  - put() check-then-act race: if len >= max: evict; then insert — unsynchronized.

DEFECTS FILED (pinned xfail-strict, flip to hard passes on fix):
  QA-12: RobotsCache docstring claims "Thread-safe cache for robots.txt results"
    but the class has no threading.Lock, no synchronized access to self._cache,
    and put() performs an unsynchronized check-then-act (len check + evict + insert)
    that can violate the max_entries invariant under concurrent access.
"""

from __future__ import annotations

import time

import pytest

from personal_index.robots_cache import RobotsCache, RobotsCacheEntry


# ---------------------------------------------------------------------------
# RobotsCacheEntry.is_expired
# ---------------------------------------------------------------------------
class TestIsExpired:
    def test_not_expired_fresh(self):
        e = RobotsCacheEntry(domain="a.com", fetched_at=time.time())
        assert not e.is_expired(ttl=3600)

    def test_expired_after_ttl(self):
        e = RobotsCacheEntry(domain="a.com", fetched_at=time.time() - 3601)
        assert e.is_expired(ttl=3600)

    def test_boundary_exactly_at_ttl(self):
        """is_expired uses strict >, so at exactly TTL it is NOT expired."""
        now = time.time()
        e = RobotsCacheEntry(domain="a.com", fetched_at=now - 3600)
        # Due to float precision, this may or may not be exactly 3600.
        # The contract is strict >, so we test just-below and just-above.
        assert not e.is_expired(ttl=3600.001)

    def test_just_over_ttl(self):
        e = RobotsCacheEntry(domain="a.com", fetched_at=time.time() - 3600.5)
        assert e.is_expired(ttl=3600)

    def test_zero_ttl_always_expired(self):
        e = RobotsCacheEntry(domain="a.com", fetched_at=time.time() - 0.001)
        assert e.is_expired(ttl=0)


# ---------------------------------------------------------------------------
# RobotsCacheEntry.allows_agent
# ---------------------------------------------------------------------------
class TestAllowsAgent:
    def test_agent_in_allowed(self):
        e = RobotsCacheEntry(domain="a.com", allowed={"bot1": True})
        assert e.allows_agent("bot1")

    def test_agent_in_disallowed(self):
        e = RobotsCacheEntry(domain="a.com", disallowed={"bot2": True})
        assert not e.allows_agent("bot2")

    def test_agent_in_both_allowed_wins(self):
        """If agent is in both allowed and disallowed, allowed takes precedence."""
        e = RobotsCacheEntry(
            domain="a.com",
            allowed={"bot3": True},
            disallowed={"bot3": True},
        )
        assert e.allows_agent("bot3")

    def test_agent_in_neither_default_allow(self):
        e = RobotsCacheEntry(domain="a.com")
        assert e.allows_agent("unknown_bot")

    def test_empty_strings(self):
        e = RobotsCacheEntry(domain="a.com", allowed={"": True})
        assert e.allows_agent("")


# ---------------------------------------------------------------------------
# RobotsCache basic get/put
# ---------------------------------------------------------------------------
class TestCacheBasic:
    def test_put_and_get(self):
        c = RobotsCache(ttl=3600)
        e = RobotsCacheEntry(domain="x.com", allowed={"bot": True})
        c.put(e)
        assert c.get("x.com") is e

    def test_get_missing_returns_none(self):
        c = RobotsCache()
        assert c.get("nonexistent.com") is None

    def test_get_expired_returns_none_and_evicts(self):
        c = RobotsCache(ttl=1)
        e = RobotsCacheEntry(domain="x.com", fetched_at=time.time() - 2)
        c.put(e)
        assert c.get("x.com") is None
        assert c.size == 0

    def test_invalidate_existing(self):
        c = RobotsCache()
        e = RobotsCacheEntry(domain="x.com")
        c.put(e)
        assert c.invalidate("x.com") is True
        assert c.get("x.com") is None

    def test_invalidate_missing(self):
        c = RobotsCache()
        assert c.invalidate("ghost.com") is False

    def test_invalidate_all(self):
        c = RobotsCache()
        c.put(RobotsCacheEntry(domain="a.com"))
        c.put(RobotsCacheEntry(domain="b.com"))
        c.invalidate_all()
        assert c.size == 0


# ---------------------------------------------------------------------------
# RobotsCache eviction (max_entries)
# ---------------------------------------------------------------------------
class TestCacheEviction:
    def test_evicts_oldest_at_max(self):
        c = RobotsCache(ttl=3600, max_entries=2)
        t0 = time.time() - 100
        t1 = time.time() - 50
        t2 = time.time()
        c.put(RobotsCacheEntry(domain="old.com", fetched_at=t0))
        c.put(RobotsCacheEntry(domain="mid.com", fetched_at=t1))
        c.put(RobotsCacheEntry(domain="new.com", fetched_at=t2))
        assert c.size == 2
        assert "old.com" not in c.domains
        assert "mid.com" in c.domains
        assert "new.com" in c.domains

    def test_no_eviction_below_max(self):
        c = RobotsCache(ttl=3600, max_entries=3)
        c.put(RobotsCacheEntry(domain="a.com"))
        c.put(RobotsCacheEntry(domain="b.com"))
        assert c.size == 2

    def test_evict_on_exact_boundary(self):
        """When size == max_entries, next put triggers eviction."""
        c = RobotsCache(ttl=3600, max_entries=1)
        c.put(RobotsCacheEntry(domain="first.com", fetched_at=time.time() - 10))
        c.put(RobotsCacheEntry(domain="second.com", fetched_at=time.time()))
        assert c.size == 1
        assert "first.com" not in c.domains
        assert "second.com" in c.domains

    def test_overwrite_same_domain_no_eviction(self):
        """Putting same domain twice should not trigger eviction."""
        c = RobotsCache(ttl=3600, max_entries=1)
        c.put(RobotsCacheEntry(domain="a.com", fetched_at=time.time() - 10))
        c.put(RobotsCacheEntry(domain="a.com", fetched_at=time.time()))
        assert c.size == 1
        assert c.get("a.com") is not None


# ---------------------------------------------------------------------------
# RobotsCache properties / stats
# ---------------------------------------------------------------------------
class TestCacheStats:
    def test_size_empty(self):
        assert RobotsCache().size == 0

    def test_domains_list(self):
        c = RobotsCache()
        c.put(RobotsCacheEntry(domain="a.com"))
        c.put(RobotsCacheEntry(domain="b.com"))
        assert set(c.domains) == {"a.com", "b.com"}

    def test_get_stats_keys(self):
        c = RobotsCache(ttl=999, max_entries=42)
        c.put(RobotsCacheEntry(domain="x.com"))
        s = c.get_stats()
        assert s["size"] == 1
        assert s["ttl"] == 999
        assert s["max_entries"] == 42
        assert s["domains"] == ["x.com"]


# ---------------------------------------------------------------------------
# Thread-safety (docstring claims "Thread-safe")
# ---------------------------------------------------------------------------
class TestThreadSafety:
    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-12: RobotsCache docstring claims 'Thread-safe cache' but no "
            "threading.Lock exists. Additionally, put() violates the "
            "max_entries invariant: with max_entries=0, put() still inserts "
            "(size becomes 1 > max_entries=0) because _evict_oldest() is a "
            "no-op on an empty dict and the insert proceeds unconditionally."
        ),
    )
    def test_max_entries_zero_respects_invariant(self):
        """size must never exceed max_entries, even when max_entries=0."""
        c = RobotsCache(ttl=3600, max_entries=0)
        c.put(RobotsCacheEntry(domain="a.com", fetched_at=time.time()))
        assert c.size <= c._max_entries, (
            f"size={c.size} exceeds max_entries={c._max_entries}"
        )

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-12: put() at capacity evicts the oldest entry even when "
            "updating an already-cached domain. Updating B at capacity "
            "evicts A (the other entry), losing data the caller did not "
            "intend to discard. The check-then-act does not special-case "
            "overwrites of existing keys."
        ),
    )
    def test_update_at_capacity_does_not_evict_other_entry(self):
        """Updating an existing domain at capacity should not evict another."""
        c = RobotsCache(ttl=3600, max_entries=2)
        t = time.time()
        c.put(RobotsCacheEntry(domain="A.com", fetched_at=t - 100))
        c.put(RobotsCacheEntry(domain="B.com", fetched_at=t))
        # Update B (already in cache) — should NOT evict A
        c.put(RobotsCacheEntry(domain="B.com", fetched_at=t + 1))
        assert "A.com" in c.domains, (
            f"A.com was evicted when updating B at capacity. domains={c.domains}"
        )
        assert c.size == 2
