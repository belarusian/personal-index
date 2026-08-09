"""Edge case tests for rate limiting."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import (
    RateLimiter, SlidingWindowLimiter, TokenBucketLimiter,
    RateLimitResult, RateLimitConfig,
)


class TestRateLimitEdgeCases:
    def test_zero_max_requests(self):
        limiter = RateLimiter(max_requests=0, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is False

    def test_very_high_limit(self):
        limiter = RateLimiter(max_requests=1000000, window_seconds=60)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_unicode_key(self):
        limiter = RateLimiter(max_requests=10, window_seconds=60)
        result = limiter.check("пользователь")
        assert result.allowed is True

    def test_result_negative_remaining(self):
        r = RateLimitResult(allowed=False, remaining=-1, limit=10)
        headers = r.to_headers()
        assert headers["X-RateLimit-Remaining"] == "0"

    def test_config_zero_window(self):
        config = RateLimitConfig(max_requests=100, window_seconds=0)
        assert config.window_seconds == 0
