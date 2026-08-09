"""Tests for content_rate_limit module."""

from __future__ import annotations

import time
import pytest
from personal_index.content_rate_limit import (
    ContentRateLimiter,
    RateLimitConfig,
    RateLimitResult,
)


class TestRateLimitConfig:
    def test_default_config(self):
        config = RateLimitConfig()
        assert config.max_requests == 100
        assert config.window_seconds == 60.0
        assert config.burst_size == 10

    def test_custom_config(self):
        config = RateLimitConfig(max_requests=50, window_seconds=30.0, burst_size=5)
        assert config.max_requests == 50
        assert config.window_seconds == 30.0
        assert config.burst_size == 5

    def test_config_rate_per_second(self):
        config = RateLimitConfig(max_requests=60, window_seconds=60.0)
        assert config.rate_per_second == 1.0


class TestRateLimitResult:
    def test_allowed_result(self):
        result = RateLimitResult(allowed=True, remaining=99, retry_after=0.0)
        assert result.allowed is True
        assert result.remaining == 99
        assert result.retry_after == 0.0
        assert result.is_limited is False

    def test_denied_result(self):
        result = RateLimitResult(allowed=False, remaining=0, retry_after=5.0)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 5.0
        assert result.is_limited is True


class TestContentRateLimiterInit:
    def test_default_init(self):
        limiter = ContentRateLimiter()
        assert limiter._default_config.max_requests == 100

    def test_custom_config_init(self):
        config = RateLimitConfig(max_requests=50)
        limiter = ContentRateLimiter(default_config=config)
        assert limiter._default_config.max_requests == 50


class TestContentRateLimiterCheck:
    def test_check_allows_within_burst(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=5)
        limiter = ContentRateLimiter(default_config=config)
        for i in range(5):
            result = limiter.check("endpoint1")
            assert result.allowed is True, f"Request {i} should be allowed"

    def test_check_denies_after_burst(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=3)
        limiter = ContentRateLimiter(default_config=config)
        for i in range(3):
            limiter.check("endpoint1")
        result = limiter.check("endpoint1")
        assert result.allowed is False

    def test_check_independent_keys(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=2)
        limiter = ContentRateLimiter(default_config=config)
        limiter.check("endpoint1")
        limiter.check("endpoint1")
        result1 = limiter.check("endpoint1")
        result2 = limiter.check("endpoint2")
        assert result1.allowed is False
        assert result2.allowed is True

    def test_check_remaining_count(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=5)
        limiter = ContentRateLimiter(default_config=config)
        result = limiter.check("ep1")
        assert result.remaining >= 0

    def test_check_retry_after(self):
        config = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=2)
        limiter = ContentRateLimiter(default_config=config)
        limiter.check("ep1")
        limiter.check("ep1")
        result = limiter.check("ep1")
        assert result.retry_after > 0


class TestContentRateLimiterPerKeyConfig:
    def test_set_config(self):
        limiter = ContentRateLimiter()
        custom = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=2)
        limiter.set_config("strict", custom)
        limiter.check("strict")
        limiter.check("strict")
        result = limiter.check("strict")
        assert result.allowed is False

    def test_default_vs_custom_config(self):
        limiter = ContentRateLimiter()
        custom = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=1)
        limiter.set_config("strict", custom)
        # Default key should allow more
        for _ in range(10):
            limiter.check("default")
        # Strict key should be limited
        limiter.check("strict")
        result = limiter.check("strict")
        assert result.allowed is False


class TestContentRateLimiterWait:
    def test_wait_if_needed_allows(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=5)
        limiter = ContentRateLimiter(default_config=config)
        assert limiter.wait_if_needed("ep1", timeout=1.0) is True

    def test_get_wait_time_zero(self):
        config = RateLimitConfig(max_requests=100, window_seconds=60.0, burst_size=5)
        limiter = ContentRateLimiter(default_config=config)
        assert limiter.get_wait_time("ep1") == 0.0

    def test_get_wait_time_after_exhaust(self):
        config = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=2)
        limiter = ContentRateLimiter(default_config=config)
        limiter.check("ep1")
        limiter.check("ep1")
        wait = limiter.get_wait_time("ep1")
        assert wait > 0


class TestContentRateLimiterReset:
    def test_reset_key(self):
        config = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=2)
        limiter = ContentRateLimiter(default_config=config)
        limiter.check("ep1")
        limiter.check("ep1")
        limiter.reset("ep1")
        result = limiter.check("ep1")
        assert result.allowed is True

    def test_reset_all(self):
        config = RateLimitConfig(max_requests=10, window_seconds=60.0, burst_size=2)
        limiter = ContentRateLimiter(default_config=config)
        limiter.check("ep1")
        limiter.check("ep1")
        limiter.check("ep2")
        limiter.check("ep2")
        limiter.reset_all()
        assert limiter.check("ep1").allowed is True
        assert limiter.check("ep2").allowed is True


class TestContentRateLimiterStats:
    def test_stats_specific_key(self):
        limiter = ContentRateLimiter()
        limiter.check("ep1")
        limiter.check("ep1")
        stats = limiter.stats("ep1")
        assert stats["key"] == "ep1"
        assert stats["total_requests"] == 2

    def test_stats_all(self):
        limiter = ContentRateLimiter()
        limiter.check("ep1")
        limiter.check("ep2")
        stats = limiter.stats()
        assert stats["tracked_keys"] == 2
        assert "ep1" in stats["buckets"]
        assert "ep2" in stats["buckets"]

    def test_stats_unknown_key(self):
        limiter = ContentRateLimiter()
        stats = limiter.stats("unknown")
        assert stats["key"] == "unknown"
        assert stats["total_requests"] == 0
