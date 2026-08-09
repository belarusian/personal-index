"""Integration tests for rate limiting."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import (
    RateLimiter, SlidingWindowLimiter, TokenBucketLimiter,
    RateLimitMiddleware, RateLimitStore,
)


class TestRateLimitIntegration:
    def test_all_limiters_consistent(self):
        fixed = RateLimiter(max_requests=2, window_seconds=60)
        sliding = SlidingWindowLimiter(max_requests=2, window_seconds=60)
        bucket = TokenBucketLimiter(rate=2, capacity=2)

        for limiter in [fixed, sliding, bucket]:
            assert limiter.check("user1").allowed is True
            assert limiter.check("user1").allowed is True
            assert limiter.check("user1").allowed is False

    def test_middleware_with_store(self):
        mw = RateLimitMiddleware(max_requests=2, window_seconds=60)
        mw.process_request({"client_ip": "1.2.3.4"})
        mw.process_request({"client_ip": "1.2.3.4"})
        result = mw.process_request({"client_ip": "1.2.3.4"})
        assert result["allowed"] is False

    def test_store_cleanup(self):
        store = RateLimitStore()
        store.get_or_create("key1", 10, 0.01)
        store.get_or_create("key2", 10, 0.01)
        time.sleep(0.02)
        store.cleanup_expired()
        assert store.size() == 0
