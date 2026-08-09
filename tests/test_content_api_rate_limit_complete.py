"""Complete rate limit module tests."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import (
    RateLimiter, SlidingWindowLimiter, FixedWindowLimiter,
    TokenBucketLimiter, RateLimitMiddleware, RateLimitStore,
    RateLimitConfig, RateLimitWindow, RateLimitResult,
    create_rate_limiter, create_rate_limit_middleware,
    check_rate_limit,
)


class TestRateLimitComplete:
    def test_all_exports(self):
        assert RateLimiter is not None
        assert SlidingWindowLimiter is not None
        assert FixedWindowLimiter is not None
        assert TokenBucketLimiter is not None
        assert RateLimitMiddleware is not None
        assert RateLimitStore is not None
        assert RateLimitConfig is not None
        assert RateLimitWindow is not None
        assert RateLimitResult is not None

    def test_all_factories(self):
        limiter = create_rate_limiter()
        assert limiter is not None
        mw = create_rate_limit_middleware()
        assert mw is not None

    def test_all_helpers(self):
        limiter = create_rate_limiter(max_requests=10, window_seconds=60)
        result = check_rate_limit(limiter, "user1")
        assert result.allowed is True

    def test_all_strategies(self):
        strategies = [
            RateLimiter(max_requests=2, window_seconds=60),
            SlidingWindowLimiter(max_requests=2, window_seconds=60),
            FixedWindowLimiter(max_requests=2, window_seconds=60),
            TokenBucketLimiter(rate=2, capacity=2),
        ]
        for strategy in strategies:
            assert strategy.check("user1").allowed is True
            assert strategy.check("user1").allowed is True
            assert strategy.check("user1").allowed is False
