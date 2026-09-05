"""Tests for request throttling."""

import time
from unittest.mock import patch

from personal_index.throttle import ThrottleManager, ThrottleRule, ThrottleState


class TestThrottleRule:
    def test_default_values(self):
        rule = ThrottleRule()
        assert rule.max_requests == 10
        assert rule.window_seconds == 60.0

    def test_rate_per_second(self):
        rule = ThrottleRule(max_requests=60, window_seconds=60.0)
        assert rule.rate_per_second == 1.0

    def test_custom_rule(self):
        rule = ThrottleRule(max_requests=5, window_seconds=10.0, min_delay=0.2)
        assert rule.max_requests == 5
        assert rule.min_delay == 0.2


class TestThrottleState:
    def test_default_values(self):
        state = ThrottleState()
        assert state.total_requests == 0
        assert state.total_wait_time == 0.0


class TestThrottleManager:
    def test_default_rule(self):
        mgr = ThrottleManager()
        rule = mgr.get_rule("example.com")
        assert rule.max_requests == 10

    def test_set_custom_rule(self):
        mgr = ThrottleManager()
        custom = ThrottleRule(max_requests=5)
        mgr.set_rule("example.com", custom)
        assert mgr.get_rule("example.com").max_requests == 5

    def test_should_throttle_false(self):
        mgr = ThrottleManager()
        assert mgr.should_throttle("http://example.com/page") is False

    def test_should_throttle_true(self):
        mgr = ThrottleManager()
        mgr.set_rule("example.com", ThrottleRule(max_requests=2, window_seconds=60.0))
        mgr._states["example.com"] = ThrottleState(
            request_times=[time.time() - 1, time.time() - 0.5],
        )
        assert mgr.should_throttle("http://example.com/page") is True

    def test_wait_if_needed_no_wait(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep") as mock_sleep:
            mgr.wait_if_needed("http://example.com/page")
            mock_sleep.assert_not_called()

    def test_wait_records_request(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep"):
            mgr.wait_if_needed("http://example.com/page")
        state = mgr._states.get("example.com")
        assert state is not None
        assert state.total_requests == 1

    def test_extract_domain(self):
        mgr = ThrottleManager()
        assert mgr._extract_domain("http://example.com/path") == "example.com"
        assert mgr._extract_domain("https://sub.example.com") == "sub.example.com"

    def test_stats_single_domain(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep"):
            mgr.wait_if_needed("http://example.com/page")
        stats = mgr.get_stats("example.com")
        assert stats["total_requests"] == 1

    def test_stats_all_domains(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep"):
            mgr.wait_if_needed("http://a.com/page")
            mgr.wait_if_needed("http://b.com/page")
        stats = mgr.get_stats()
        assert stats["domains_tracked"] == 2
        assert stats["total_requests"] == 2

    def test_reset_single_domain(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep"):
            mgr.wait_if_needed("http://example.com/page")
        mgr.reset("example.com")
        assert "example.com" not in mgr._states

    def test_reset_all(self):
        mgr = ThrottleManager()
        with patch("personal_index.throttle.time.sleep"):
            mgr.wait_if_needed("http://a.com/page")
            mgr.wait_if_needed("http://b.com/page")
        mgr.reset()
        assert len(mgr._states) == 0

    def test_expired_requests_cleaned(self):
        mgr = ThrottleManager()
        mgr.set_rule("example.com", ThrottleRule(max_requests=2, window_seconds=1.0))
        mgr._states["example.com"] = ThrottleState(
            request_times=[time.time() - 10, time.time() - 9],
        )
        assert mgr.should_throttle("http://example.com/page") is False


class TestShouldThrottleBoundary:
    """Pin the corrected should_throttle claim: True iff the domain has made
    at least max_requests requests within the window (max_requests-1 is False)."""

    def test_boundary_below_max_is_false(self):
        mgr = ThrottleManager()
        mgr.set_rule("example.com", ThrottleRule(max_requests=3, window_seconds=60.0))
        now = time.time()
        mgr._states["example.com"] = ThrottleState(
            request_times=[now - 1, now - 0.5],  # 2 < max_requests=3
        )
        assert mgr.should_throttle("http://example.com/page") is False

    def test_boundary_at_max_is_true(self):
        mgr = ThrottleManager()
        mgr.set_rule("example.com", ThrottleRule(max_requests=3, window_seconds=60.0))
        now = time.time()
        mgr._states["example.com"] = ThrottleState(
            request_times=[now - 1, now - 0.5, now - 0.1],  # 3 == max_requests
        )
        assert mgr.should_throttle("http://example.com/page") is True
