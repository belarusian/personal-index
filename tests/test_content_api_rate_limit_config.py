"""Tests for rate limit configuration."""

from __future__ import annotations

import pytest
from personal_index.content_api_rate_limit import RateLimitConfig


class TestRateLimitConfig:
    def test_default_config(self):
        config = RateLimitConfig()
        assert config.max_requests == 100
        assert config.window_seconds == 60

    def test_custom_config(self):
        config = RateLimitConfig(max_requests=50, window_seconds=30)
        assert config.max_requests == 50
        assert config.window_seconds == 30

    def test_per_endpoint_config(self):
        config = RateLimitConfig(
            max_requests=100,
            per_endpoint_limits={"search": 10, "upload": 5}
        )
        assert config.per_endpoint_limits["search"] == 10
        assert config.per_endpoint_limits["upload"] == 5

    def test_config_serialization(self):
        config = RateLimitConfig(max_requests=50, window_seconds=30)
        d = config.to_dict()
        assert d["max_requests"] == 50
        assert d["window_seconds"] == 30

    def test_config_empty_endpoint_limits(self):
        config = RateLimitConfig()
        assert config.per_endpoint_limits == {}
