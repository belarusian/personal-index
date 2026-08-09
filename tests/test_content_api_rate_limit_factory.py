"""Tests for rate limit factory functions."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import (
    create_rate_limiter,
    create_rate_limit_middleware,
    check_rate_limit,
)


class TestRateLimitFactories:
    def test_create_limiter(self):
        limiter = create_rate_limiter()
        assert limiter is not None

    def test_create_limiter_custom(self):
        limiter = create_rate_limiter(max_requests=50, window_seconds=30)
        assert limiter.max_requests == 50

    def test_create_middleware(self):
        mw = create_rate_limit_middleware()
        assert mw is not None

    def test_create_middleware_custom(self):
        mw = create_rate_limit_middleware(max_requests=50, window_seconds=30)
        assert mw.limiter.max_requests == 50

    def test_check_rate_limit(self):
        limiter = create_rate_limiter(max_requests=10, window_seconds=60)
        result = check_rate_limit(limiter, "user1")
        assert result.allowed is True
