"""Tests for rate limiter module."""

from __future__ import annotations

import time

import pytest

from personal_index.rate_limiter import RateLimiter, RateLimitConfig


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def setup_method(self):
        self.limiter = RateLimiter(RateLimitConfig(
            max_requests=3,
            time_window=1.0,
            per_domain=True,
        ))

    def test_can_request_initially(self):
        assert self.limiter.can_request("http://example.com/page1") is True

    def test_can_request_after_limit(self):
        for i in range(3):
            self.limiter.record_request(f"http://example.com/page{i}")
        assert self.limiter.can_request("http://example.com/page3") is False

    def test_different_domains_independent(self):
        for i in range(3):
            self.limiter.record_request(f"http://example.com/page{i}")
        # Different domain should still be allowed
        assert self.limiter.can_request("http://other.com/page1") is True

    def test_wait_time_when_allowed(self):
        assert self.limiter.wait_time("http://example.com") == 0.0

    def test_wait_time_when_limited(self):
        for i in range(3):
            self.limiter.record_request(f"http://example.com/page{i}")
        wait = self.limiter.wait_time("http://example.com/page3")
        assert wait > 0

    def test_reset(self):
        for i in range(3):
            self.limiter.record_request(f"http://example.com/page{i}")
        self.limiter.reset()
        assert self.limiter.can_request("http://example.com/page3") is True

    def test_get_stats(self):
        self.limiter.record_request("http://example.com/page1")
        self.limiter.record_request("http://other.com/page1")
        stats = self.limiter.get_stats()
        assert stats["domains_tracked"] == 2
        assert stats["global_requests"] == 2

    def test_default_config(self):
        limiter = RateLimiter()
        assert limiter.config.max_requests == 10
        assert limiter.config.time_window == 60.0

    def test_extract_domain(self):
        domain = RateLimiter._extract_domain("https://www.example.com/path?q=1")
        assert domain == "www.example.com"

    def test_extract_domain_no_scheme(self):
        domain = RateLimiter._extract_domain("example.com")
        assert domain == "example.com"

    def test_global_limit(self):
        limiter = RateLimiter(RateLimitConfig(
            max_requests=2,
            time_window=1.0,
            per_domain=False,
        ))
        limiter.record_request("http://a.com/page1")
        limiter.record_request("http://b.com/page1")
        assert limiter.can_request("http://c.com/page1") is False

    def test_record_request(self):
        self.limiter.record_request("http://example.com/page1")
        stats = self.limiter.get_stats()
        assert stats["domains_tracked"] == 1
