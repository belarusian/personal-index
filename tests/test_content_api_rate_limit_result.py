"""Tests for rate limit result."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import RateLimitResult


class TestRateLimitResult:
    def test_allowed_result(self):
        r = RateLimitResult(allowed=True, remaining=9, limit=10)
        assert r.allowed is True

    def test_denied_result(self):
        r = RateLimitResult(allowed=False, remaining=0, limit=10, retry_after=30)
        assert r.retry_after == 30

    def test_headers_generation(self):
        r = RateLimitResult(allowed=True, remaining=5, limit=10, reset=60)
        headers = r.to_headers()
        assert headers["X-RateLimit-Limit"] == "10"
        assert headers["X-RateLimit-Remaining"] == "5"
        assert headers["X-RateLimit-Reset"] == "60"

    def test_headers_with_retry(self):
        r = RateLimitResult(allowed=False, remaining=0, limit=10, retry_after=30)
        headers = r.to_headers()
        assert "Retry-After" in headers

    def test_serialization(self):
        r = RateLimitResult(allowed=True, remaining=5, limit=10)
        d = r.to_dict()
        assert d["allowed"] is True
        assert d["remaining"] == 5

    def test_remaining_zero(self):
        r = RateLimitResult(allowed=False, remaining=0, limit=10)
        headers = r.to_headers()
        assert headers["X-RateLimit-Remaining"] == "0"
