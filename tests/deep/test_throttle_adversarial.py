"""Cycle 172 PROBE: personal_index/throttle.py (never-probed subsystem).

Adversarial deep tests for ThrottleRule / ThrottleManager:
  - ThrottleRule.rate_per_second: normal, zero window (degenerate).
  - ThrottleManager._extract_domain: case sensitivity, port, userinfo, empty.
  - ThrottleManager.should_throttle: boundary, empty state, window pruning.
  - ThrottleManager.wait_if_needed: first request (no wait).
  - ThrottleManager.get_stats: per-domain, aggregate, untracked domain.
  - ThrottleManager.reset: per-domain, all, missing domain.
  - ThrottleManager.set_rule / get_rule: round-trip, default fallback.

DEFECTS FILED (pinned xfail-strict, flip to hard passes on fix):
  QA-13: ThrottleManager._extract_domain() is not a true domain extractor:
    1. Case-sensitive: EXAMPLE.com and example.com are treated as different
       domains, violating the "per-domain" contract (DNS domains are
       case-insensitive).
    2. Port-sensitive: example.com:8080 and example.com are treated as
       different domains, but the port is not part of the domain.
    3. Userinfo not stripped: user:pass@example.com returns
       "user:pass@example.com" instead of "example.com".
    Additionally, ThrottleRule.rate_per_second raises ZeroDivisionError
    when window_seconds=0 (no guard for the degenerate case).
"""

from __future__ import annotations

import time

import pytest

from personal_index.throttle import ThrottleManager, ThrottleRule, ThrottleState


# ---------------------------------------------------------------------------
# ThrottleRule
# ---------------------------------------------------------------------------
class TestThrottleRule:
    def test_defaults(self):
        r = ThrottleRule()
        assert r.max_requests == 10
        assert r.window_seconds == 60.0
        assert r.min_delay == 0.5

    def test_rate_per_second_normal(self):
        r = ThrottleRule(max_requests=10, window_seconds=60.0)
        assert r.rate_per_second == pytest.approx(10 / 60)

    def test_rate_per_second_custom(self):
        r = ThrottleRule(max_requests=5, window_seconds=10.0)
        assert r.rate_per_second == pytest.approx(0.5)

    def test_rate_per_second_zero_window(self):
        """window_seconds=0 should not crash; should return 0.0 or inf."""
        r = ThrottleRule(max_requests=10, window_seconds=0.0)
        rate = r.rate_per_second
        assert rate >= 0


# ---------------------------------------------------------------------------
# ThrottleManager._extract_domain
# ---------------------------------------------------------------------------
class TestExtractDomain:
    def test_basic_http(self):
        m = ThrottleManager()
        assert m._extract_domain("http://example.com/path") == "example.com"

    def test_basic_https(self):
        m = ThrottleManager()
        assert m._extract_domain("https://example.com/path") == "example.com"

    def test_empty_string(self):
        m = ThrottleManager()
        assert m._extract_domain("") == ""

    def test_case_insensitive(self):
        """DNS domains are case-insensitive; throttle buckets must match."""
        m = ThrottleManager()
        lower = m._extract_domain("http://example.com/")
        upper = m._extract_domain("http://EXAMPLE.com/")
        assert lower == upper, (
            f"Domains should be case-insensitive: {lower!r} != {upper!r}"
        )

    def test_port_not_part_of_domain(self):
        """The port is not part of the domain; throttle buckets must match."""
        m = ThrottleManager()
        no_port = m._extract_domain("http://example.com/")
        with_port = m._extract_domain("http://example.com:8080/")
        assert no_port == with_port, (
            f"Port should not affect domain: {no_port!r} != {with_port!r}"
        )

    def test_userinfo_stripped(self):
        """Userinfo (user:pass@) is not part of the domain."""
        m = ThrottleManager()
        plain = m._extract_domain("http://example.com/")
        with_userinfo = m._extract_domain("http://user:pass@example.com/")
        assert plain == with_userinfo, (
            f"Userinfo should not affect domain: {plain!r} != {with_userinfo!r}"
        )


# ---------------------------------------------------------------------------
# ThrottleManager.should_throttle
# ---------------------------------------------------------------------------
class TestShouldThrottle:
    def test_no_requests(self):
        m = ThrottleManager()
        assert not m.should_throttle("http://example.com/")

    def test_below_max(self):
        m = ThrottleManager()
        rule = ThrottleRule(max_requests=3, window_seconds=60.0)
        m.set_rule("example.com", rule)
        state = m._states.setdefault("example.com", ThrottleState())
        now = time.time()
        state.request_times = [now - 1, now - 0.5]
        state.total_requests = 2
        assert not m.should_throttle("http://example.com/")

    def test_at_max(self):
        m = ThrottleManager()
        rule = ThrottleRule(max_requests=3, window_seconds=60.0)
        m.set_rule("example.com", rule)
        state = m._states.setdefault("example.com", ThrottleState())
        now = time.time()
        state.request_times = [now - 1, now - 0.5, now - 0.1]
        state.total_requests = 3
        assert m.should_throttle("http://example.com/")

    def test_above_max(self):
        m = ThrottleManager()
        rule = ThrottleRule(max_requests=3, window_seconds=60.0)
        m.set_rule("example.com", rule)
        state = m._states.setdefault("example.com", ThrottleState())
        now = time.time()
        state.request_times = [now - 1, now - 0.5, now - 0.1, now - 0.01]
        state.total_requests = 4
        assert m.should_throttle("http://example.com/")

    def test_window_pruning(self):
        """Requests outside the window are pruned before counting."""
        m = ThrottleManager()
        rule = ThrottleRule(max_requests=3, window_seconds=1.0)
        m.set_rule("example.com", rule)
        state = m._states.setdefault("example.com", ThrottleState())
        now = time.time()
        # 3 requests, but 2 are outside the 1-second window
        state.request_times = [now - 5, now - 4, now - 0.1]
        state.total_requests = 3
        # After pruning, only 1 request is in the window -> not throttled
        assert not m.should_throttle("http://example.com/")


# ---------------------------------------------------------------------------
# ThrottleManager.get_stats
# ---------------------------------------------------------------------------
class TestGetStats:
    def test_per_domain(self):
        m = ThrottleManager()
        state = m._states.setdefault("example.com", ThrottleState())
        state.total_requests = 5
        state.total_wait_time = 1.5
        stats = m.get_stats("example.com")
        assert stats["domain"] == "example.com"
        assert stats["total_requests"] == 5
        assert stats["total_wait_time"] == 1.5
        assert "rule" in stats

    def test_untracked_domain(self):
        m = ThrottleManager()
        stats = m.get_stats("unknown.com")
        assert stats["domain"] == "unknown.com"
        assert stats["total_requests"] == 0

    def test_aggregate(self):
        m = ThrottleManager()
        s1 = m._states.setdefault("a.com", ThrottleState())
        s1.total_requests = 3
        s1.total_wait_time = 1.0
        s2 = m._states.setdefault("b.com", ThrottleState())
        s2.total_requests = 7
        s2.total_wait_time = 2.0
        stats = m.get_stats()
        assert stats["domains_tracked"] == 2
        assert stats["total_requests"] == 10
        assert stats["total_wait_time"] == pytest.approx(3.0)


# ---------------------------------------------------------------------------
# ThrottleManager.reset
# ---------------------------------------------------------------------------
class TestReset:
    def test_reset_domain(self):
        m = ThrottleManager()
        m._states["example.com"] = ThrottleState()
        m.reset("example.com")
        assert "example.com" not in m._states

    def test_reset_all(self):
        m = ThrottleManager()
        m._states["a.com"] = ThrottleState()
        m._states["b.com"] = ThrottleState()
        m.reset()
        assert len(m._states) == 0

    def test_reset_missing_domain(self):
        m = ThrottleManager()
        m.reset("nonexistent.com")  # Should not raise
        assert len(m._states) == 0


# ---------------------------------------------------------------------------
# ThrottleManager.set_rule / get_rule
# ---------------------------------------------------------------------------
class TestSetGetRule:
    def test_round_trip(self):
        m = ThrottleManager()
        rule = ThrottleRule(max_requests=5, window_seconds=30.0)
        m.set_rule("example.com", rule)
        assert m.get_rule("example.com") is rule

    def test_default_fallback(self):
        default = ThrottleRule(max_requests=1, window_seconds=1.0)
        m = ThrottleManager(default_rule=default)
        assert m.get_rule("unknown.com") is default


# ---------------------------------------------------------------------------
# ThrottleManager.wait_if_needed
# ---------------------------------------------------------------------------
class TestWaitIfNeeded:
    def test_first_request_no_wait(self):
        m = ThrottleManager()
        wait = m.wait_if_needed("http://example.com/")
        assert wait == 0.0
        assert m.get_stats("example.com")["total_requests"] == 1
