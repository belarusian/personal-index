"""Tests for fixed window rate limiter."""

from __future__ import annotations

import time
import pytest
from personal_index.content_api_rate_limit import FixedWindowLimiter


class TestFixedWindowLimiter:
    def test_allows_under_limit(self):
        limiter = FixedWindowLimiter(max_requests=5, window_seconds=60)
        for _ in range(5):
            result = limiter.check("user1")
            assert result.allowed is True

    def test_blocks_at_limit(self):
        limiter = FixedWindowLimiter(max_requests=2, window_seconds=60)
        limiter.check("user1")
        limiter.check("user1")
        result = limiter.check("user1")
        assert result.allowed is False

    def test_window_reset(self):
        limiter = FixedWindowLimiter(max_requests=1, window_seconds=0.05)
        limiter.check("user1")
        time.sleep(0.06)
        result = limiter.check("user1")
        assert result.allowed is True

    def test_independent_keys(self):
        limiter = FixedWindowLimiter(max_requests=1, window_seconds=60)
        r1 = limiter.check("user1")
        r2 = limiter.check("user2")
        assert r1.allowed is True
        assert r2.allowed is True
