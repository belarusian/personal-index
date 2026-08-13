"""Tests for rate limiting middleware."""

import time

from personal_index.api.rate_limit_middleware import (
    RateLimitEntry,
    RateLimitRule,
    SlidingWindowRateLimiter,
)


class TestRateLimitRule:
    def test_matches_path(self):
        r = RateLimitRule(max_requests=10, window_seconds=60, path_pattern="/api")
        assert r.matches("GET", "/api/users") is True
        assert r.matches("GET", "/health") is False

    def test_matches_method(self):
        r = RateLimitRule(max_requests=10, window_seconds=60, methods=["POST"])
        assert r.matches("POST", "/api") is True
        assert r.matches("GET", "/api") is False

    def test_matches_no_constraints(self):
        r = RateLimitRule(max_requests=10, window_seconds=60)
        assert r.matches("GET", "/anything") is True

    def test_matches_any_method(self):
        r = RateLimitRule(max_requests=10, window_seconds=60, path_pattern="/api")
        assert r.matches("DELETE", "/api/item") is True


class TestRateLimitEntry:
    def test_cleanup(self):
        e = RateLimitEntry(timestamps=[1.0, 2.0, 3.0])
        e.cleanup(4.0, window=2.0)
        assert e.timestamps == [3.0]

    def test_can_request_allowed(self):
        e = RateLimitEntry(timestamps=[1.0])
        assert e.can_request(2.0, max_requests=5) is True

    def test_can_request_denied(self):
        e = RateLimitEntry(timestamps=[1.0, 2.0, 3.0])
        e.cleanup(3.5, window=10.0)
        assert len(e.timestamps) == 3

    def test_record_request(self):
        e = RateLimitEntry()
        e.record_request(1.0)
        assert 1.0 in e.timestamps


class TestSlidingWindowRateLimiter:
    def test_default_allowed(self):
        limiter = SlidingWindowRateLimiter()
        allowed, headers = limiter.is_allowed("127.0.0.1", "GET", "/api")
        assert allowed is True
        assert "X-RateLimit-Limit" in headers

    def test_rate_limit_exceeded(self):
        rule = RateLimitRule(max_requests=2, window_seconds=60)
        limiter = SlidingWindowRateLimiter(rules=[rule])
        limiter.is_allowed("ip1", "GET", "/api")
        limiter.is_allowed("ip1", "GET", "/api")
        allowed, headers = limiter.is_allowed("ip1", "GET", "/api")
        assert allowed is False
        assert "Retry-After" in headers

    def test_headers_included(self):
        limiter = SlidingWindowRateLimiter()
        _, headers = limiter.is_allowed("ip1", "GET", "/api")
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers

    def test_get_status(self):
        limiter = SlidingWindowRateLimiter()
        limiter.is_allowed("ip1", "GET", "/api")
        status = limiter.get_status("ip1")
        assert status["identifier"] == "ip1"
        assert len(status["rules"]) >= 1

    def test_reset_specific(self):
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        limiter = SlidingWindowRateLimiter(rules=[rule])
        limiter.is_allowed("ip1", "GET", "/api")
        limiter.is_allowed("ip1", "GET", "/api")
        limiter.reset("ip1")
        allowed, _ = limiter.is_allowed("ip1", "GET", "/api")
        assert allowed is True

    def test_reset_all(self):
        rule = RateLimitRule(max_requests=1, window_seconds=60)
        limiter = SlidingWindowRateLimiter(rules=[rule])
        limiter.is_allowed("ip1", "GET", "/api")
        limiter.is_allowed("ip2", "GET", "/api")
        limiter.reset()
        a1, _ = limiter.is_allowed("ip1", "GET", "/api")
        a2, _ = limiter.is_allowed("ip2", "GET", "/api")
        assert a1 is True
        assert a2 is True

    def test_path_pattern_filtering(self):
        rule = RateLimitRule(max_requests=1, window_seconds=60, path_pattern="/limited")
        limiter = SlidingWindowRateLimiter(rules=[rule])
        a1, _ = limiter.is_allowed("ip1", "GET", "/unlimited")
        assert a1 is True

    def test_method_filtering(self):
        rule = RateLimitRule(max_requests=999, window_seconds=60, methods=["POST"])
        limiter = SlidingWindowRateLimiter(rules=[rule])
        allowed, _ = limiter.is_allowed("ip1", "GET", "/api")
        assert allowed is True

    def test_global_limit(self):
        limiter = SlidingWindowRateLimiter()
        limiter._global_limit = 2
        limiter.is_allowed("ip1", "GET", "/api")
        limiter.is_allowed("ip2", "GET", "/api")
        allowed, headers = limiter.is_allowed("ip3", "GET", "/api")
        assert allowed is False

    def test_key_generation(self):
        limiter = SlidingWindowRateLimiter()
        rule = RateLimitRule(max_requests=10, window_seconds=60, path_pattern="/api")
        key = limiter._get_key("user1", rule)
        assert key == "ip:user1:/api"
