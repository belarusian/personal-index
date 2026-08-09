"""Tests for token bucket rate limiter."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import TokenBucketLimiter


class TestTokenBucket:
    def test_allows_within_capacity(self):
        limiter = TokenBucketLimiter(rate=10, capacity=5)
        for _ in range(5):
            result = limiter.check("user1")
            assert result.allowed is True

    def test_blocks_when_empty(self):
        limiter = TokenBucketLimiter(rate=1, capacity=1)
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False

    def test_refills_over_time(self):
        limiter = TokenBucketLimiter(rate=100, capacity=1)
        limiter.check("user1")
        time.sleep(0.02)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_different_keys_independent(self):
        limiter = TokenBucketLimiter(rate=1, capacity=1)
        r1 = limiter.check("user1")
        r2 = limiter.check("user2")
        assert r1.allowed is True
        assert r2.allowed is True

    def test_retry_after_set(self):
        limiter = TokenBucketLimiter(rate=1, capacity=1)
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.retry_after is not None
