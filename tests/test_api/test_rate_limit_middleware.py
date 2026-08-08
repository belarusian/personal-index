"""Tests for API rate limiting middleware."""

from __future__ import annotations

import time

import pytest

from personal_index.api.rate_limit_middleware import (
    RateLimitMiddleware,
    RateLimitRule,
    SlidingWindowRateLimiter,
)


class TestRateLimitRule:
    """Tests for RateLimitRule."""

    def test_matches_any_path(self):
        """Test rule matches any path when no pattern set."""
        rule = RateLimitRule(max_requests=10, window_seconds=60)
        assert rule.matches("GET", "/anything")

    def test_matches_path_pattern(self):
        """Test rule matches path pattern."""
        rule = RateLimitRule(
            max_requests=10, window_seconds=60, path_pattern="/api"
        )
        assert rule.matches("GET", "/api/v1/users")
        assert not rule.matches("GET", "/health")

    def test_matches_methods(self):
        """Test rule matches specific methods."""
        rule = RateLimitRule(
            max_requests=10, window_seconds=60, methods=["POST"]
        )
        assert rule.matches("POST", "/api/data")
        assert not rule.matches("GET", "/api/data")


class TestSlidingWindowRateLimiter:
    """Tests for SlidingWindowRateLimiter."""

    @pytest.fixture
    def limiter(self):
        """Create a rate limiter with test rules."""
        rules = [
            RateLimitRule(max_requests=5, window_seconds=10.0, key="ip"),
        ]
        return SlidingWindowRateLimiter(rules=rules)

    def test_allows_within_limit(self, limiter):
        """Test requests within limit are allowed."""
        allowed, headers = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True
        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "5"

    def test_blocks_over_limit(self, limiter):
        """Test requests over limit are blocked."""
        # Use up all requests
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")

        allowed, headers = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is False
        assert "Retry-After" in headers

    def test_different_identifiers_separate(self, limiter):
        """Test different identifiers have separate limits."""
        for _ in range(5):
            limiter.is_allowed("1.1.1.1", "GET", "/api/test")

        # Different IP should still be allowed
        allowed, _ = limiter.is_allowed("2.2.2.2", "GET", "/api/test")
        assert allowed is True

    def test_remaining_decreases(self, limiter):
        """Test remaining count decreases with each request."""
        _, headers1 = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        _, headers2 = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert int(headers2["X-RateLimit-Remaining"]) < int(headers1["X-RateLimit-Remaining"])

    def test_get_status(self, limiter):
        """Test getting rate limit status."""
        limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        status = limiter.get_status("127.0.0.1")
        assert status["identifier"] == "127.0.0.1"
        assert len(status["rules"]) == 1

    def test_reset_identifier(self, limiter):
        """Test resetting rate limits for an identifier."""
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")

        limiter.reset("127.0.0.1")
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True

    def test_reset_all(self, limiter):
        """Test resetting all rate limits."""
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")

        limiter.reset()
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True

    def test_rule_path_filtering(self):
        """Test that rules only apply to matching paths."""
        rules = [
            RateLimitRule(
                max_requests=2, window_seconds=60, path_pattern="/api/v1"
            ),
        ]
        limiter = SlidingWindowRateLimiter(rules=rules)

        # /api/v1 path is limited
        for _ in range(2):
            limiter.is_allowed("127.0.0.1", "GET", "/api/v1/test")
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/v1/test")
        assert allowed is False

        # /health path is not limited by this rule
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/health")
        assert allowed is True


class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware."""

    def test_default_key_extractor(self):
        """Test default key extraction from scope."""
        scope = {"client": ("192.168.1.1", 12345)}
        key = RateLimitMiddleware._default_key_extractor(scope)
        assert key == "192.168.1.1"

    def test_default_key_extractor_no_client(self):
        """Test key extraction when no client."""
        scope = {}
        key = RateLimitMiddleware._default_key_extractor(scope)
        assert key == "unknown"

    def test_middleware_blocks_over_limit(self):
        """Test middleware blocks requests over limit."""
        rules = [RateLimitRule(max_requests=1, window_seconds=60)]
        limiter = SlidingWindowRateLimiter(rules=rules)

        class FakeApp:
            async def __call__(self, scope, receive, send):
                await send({
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [],
                })
                await send({"type": "http.response.body", "body": b"ok"})

        middleware = RateLimitMiddleware(FakeApp(), limiter=limiter)
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        scope = {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "client": ("127.0.0.1", 12345),
        }

        import asyncio
        # First request should pass
        asyncio.get_event_loop().run_until_complete(
            middleware(scope, receive, send)
        )
        assert sent[-1]["body"] == b"ok"

        # Second request should be blocked
        sent.clear()
        asyncio.get_event_loop().run_until_complete(
            middleware(scope, receive, send)
        )
        assert sent[0]["status"] == 429

    def test_middleware_skips_non_http(self):
        """Test middleware skips non-HTTP scopes."""
        limiter = SlidingWindowRateLimiter()

        class FakeApp:
            async def __call__(self, scope, receive, send):
                pass

        middleware = RateLimitMiddleware(FakeApp(), limiter=limiter)

        async def receive():
            return {}

        async def send(msg):
            pass

        import asyncio
        asyncio.get_event_loop().run_until_complete(
            middleware({"type": "websocket"}, receive, send)
        )
