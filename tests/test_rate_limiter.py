"""Tests for rate limiter module."""

from __future__ import annotations

import time

import pytest

from personal_index.rate_limiter import (
    RateLimiter,
    RateLimitConfig,
    RateLimitStatus,
    TokenBucket,
)


class TestRateLimitConfig:
    def test_defaults(self):
        config = RateLimitConfig()
        assert config.max_requests == 10
        assert config.window_seconds == 60.0
        assert config.burst_size == 10

    def test_custom_config(self):
        config = RateLimitConfig(max_requests=5, window_seconds=30.0, burst_size=10)
        assert config.max_requests == 5
        assert config.window_seconds == 30.0
        assert config.burst_size == 10


class TestRateLimitStatus:
    def test_creation(self):
        status = RateLimitStatus(remaining=5, limit=10, reset_at=100.0)
        assert status.remaining == 5
        assert status.limit == 10
        assert status.reset_at == 100.0
        assert status.retry_after == 0.0


class TestTokenBucket:
    def test_acquire_within_limit(self):
        config = RateLimitConfig(max_requests=5, window_seconds=1.0)
        bucket = TokenBucket(config)
        for _ in range(5):
            assert bucket.acquire() is True

    def test_acquire_exceeds_limit(self):
        config = RateLimitConfig(max_requests=2, window_seconds=1.0)
        bucket = TokenBucket(config)
        assert bucket.acquire() is True
        assert bucket.acquire() is True
        assert bucket.acquire() is False

    def test_wait_time_when_empty(self):
        config = RateLimitConfig(max_requests=2, window_seconds=1.0)
        bucket = TokenBucket(config)
        bucket.acquire()
        bucket.acquire()
        assert bucket.wait_time() > 0

    def test_wait_time_when_available(self):
        config = RateLimitConfig(max_requests=5, window_seconds=1.0)
        bucket = TokenBucket(config)
        assert bucket.wait_time() == 0.0

    def test_status(self):
        config = RateLimitConfig(max_requests=5, window_seconds=1.0)
        bucket = TokenBucket(config)
        status = bucket.status()
        assert status.remaining == 5
        assert status.limit == 5

    def test_refill_over_time(self):
        config = RateLimitConfig(max_requests=2, window_seconds=0.1)
        bucket = TokenBucket(config)
        bucket.acquire()
        bucket.acquire()
        assert bucket.acquire() is False
        time.sleep(0.15)
        assert bucket.acquire() is True

    def test_burst_size(self):
        config = RateLimitConfig(max_requests=5, window_seconds=10.0, burst_size=10)
        bucket = TokenBucket(config)
        for _ in range(10):
            assert bucket.acquire() is True
        assert bucket.acquire() is False


class TestRateLimiter:
    def setup_method(self):
        self.limiter = RateLimiter(RateLimitConfig(max_requests=3, window_seconds=1.0))

    def test_can_request(self):
        assert self.limiter.can_request("example.com") is True

    def test_can_request_exhausted(self):
        for _ in range(3):
            self.limiter.can_request("example.com")
        assert self.limiter.can_request("example.com") is False

    def test_separate_domains(self):
        self.limiter.can_request("a.com")
        self.limiter.can_request("a.com")
        self.limiter.can_request("a.com")
        assert self.limiter.can_request("a.com") is False
        assert self.limiter.can_request("b.com") is True

    def test_wait_for_request(self):
        config = RateLimitConfig(max_requests=1, window_seconds=0.1)
        limiter = RateLimiter(config)
        limiter.can_request("example.com")
        assert limiter.wait_for_request("example.com", timeout=1.0) is True

    def test_wait_for_request_timeout(self):
        config = RateLimitConfig(max_requests=1, window_seconds=100.0)
        limiter = RateLimiter(config)
        limiter.can_request("example.com")
        assert limiter.wait_for_request("example.com", timeout=0.01) is False

    def test_get_status(self):
        status = self.limiter.get_status("example.com")
        assert isinstance(status, RateLimitStatus)
        assert status.limit == 3

    def test_get_wait_time(self):
        assert self.limiter.get_wait_time("example.com") == 0.0

    def test_reset_domain(self):
        for _ in range(3):
            self.limiter.can_request("example.com")
        assert self.limiter.can_request("example.com") is False
        self.limiter.reset_domain("example.com")
        assert self.limiter.can_request("example.com") is True

    def test_reset_all(self):
        for _ in range(3):
            self.limiter.can_request("a.com")
        for _ in range(3):
            self.limiter.can_request("b.com")
        self.limiter.reset_all()
        assert self.limiter.can_request("a.com") is True
        assert self.limiter.can_request("b.com") is True

    def test_get_all_statuses(self):
        self.limiter.can_request("a.com")
        self.limiter.can_request("b.com")
        statuses = self.limiter.get_all_statuses()
        assert "a.com" in statuses
        assert "b.com" in statuses

    def test_set_domain_config(self):
        self.limiter.set_domain_config(
            "strict.com",
            RateLimitConfig(max_requests=1, window_seconds=1.0),
        )
        self.limiter.can_request("strict.com")
        assert self.limiter.can_request("strict.com") is False
