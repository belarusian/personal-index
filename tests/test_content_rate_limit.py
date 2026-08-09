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

    def test_denied_result(self):
        result = RateLimitResult(allowed=False, remaining=0, retry_after=5.0)
        assert result.allowed is False
        assert result.remaining == 0
        assert result.retry_after == 5.0
