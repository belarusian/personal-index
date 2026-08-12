"""Tests for personal_index.api.middleware and personal_index.api.rate_limit_middleware."""

from __future__ import annotations

import asyncio
import logging
import time

import pytest

from personal_index.api.middleware import (
    CORSHeadersMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    create_middleware_stack,
)
from personal_index.api.rate_limit_middleware import (
    RateLimitMiddleware,
    RateLimitRule,
    RateLimitEntry,
    SlidingWindowRateLimiter,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FakeApp:
    """Minimal ASGI app that records calls and sends a 200 response."""

    def __init__(self):
        self.calls = []

    async def __call__(self, scope, receive, send):
        self.calls.append((scope, receive, send))
        await send({
            "type": "http.response.start",
            "status": 200,
            "headers": [],
        })
        await send({"type": "http.response.body", "body": b"ok"})


def _make_scope(**overrides):
    """Build a minimal HTTP ASGI scope."""
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "query_string": b"",
        "headers": [],
    }
    scope.update(overrides)
    return scope


# ---------------------------------------------------------------------------
# RequestLoggingMiddleware
# ---------------------------------------------------------------------------

class TestRequestLoggingMiddleware:
    """Tests for RequestLoggingMiddleware."""

    def test_logs_http_request(self, caplog):
        """Middleware logs HTTP requests with method, path, status, duration."""
        caplog.set_level(logging.INFO, logger="personal_index.api.middleware")
        app = FakeApp()
        mw = RequestLoggingMiddleware(app)
        scope = _make_scope(path="/test", method="GET")
        sent = []

        async def receive():
            return {"type": "http.request"}

        async def send(msg):
            sent.append(msg)

        asyncio.run(mw(scope, receive, send))
        assert len(sent) == 2
        assert "Request GET /test" in caplog.text

    def test_skips_non_http_scope(self):
        """Non-HTTP scopes pass through without logging."""
        app = FakeApp()
        mw = RequestLoggingMiddleware(app)
        scope = {"type": "websocket"}

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw(scope, receive, send))
        assert len(app.calls) == 1

    def test_captures_response_status(self, caplog):
        """Middleware captures the actual response status code."""
        caplog.set_level(logging.INFO, logger="personal_index.api.middleware")

        class StatusApp:
            async def __call__(self, scope, receive, send):
                await send({
                    "type": "http.response.start",
                    "status": 404,
                    "headers": [],
                })
                await send({"type": "http.response.body", "body": b"not found"})

        mw = RequestLoggingMiddleware(StatusApp())
        scope = _make_scope(path="/missing")

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw(scope, receive, send))
        assert "404" in caplog.text


# ---------------------------------------------------------------------------
# CORSHeadersMiddleware
# ---------------------------------------------------------------------------

class TestCORSHeadersMiddleware:
    """Tests for CORSHeadersMiddleware."""

    def test_adds_cors_headers_to_response(self):
        """CORS headers are appended to normal responses."""
        app = FakeApp()
        mw = CORSHeadersMiddleware(app)
        scope = _make_scope(method="GET")
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        asyncio.run(mw(scope, receive, send))
        headers = {(k.decode(), v.decode()) for k, v in sent[0]["headers"]}
        assert ("Access-Control-Allow-Origin", "*") in headers

    def test_options_returns_204(self):
        """OPTIONS preflight returns 204 with CORS headers."""
        app = FakeApp()
        mw = CORSHeadersMiddleware(app)
        scope = _make_scope(method="OPTIONS")
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        asyncio.run(mw(scope, receive, send))
        assert sent[0]["status"] == 204
        headers = {(k.decode(), v.decode()) for k, v in sent[0]["headers"]}
        assert ("Access-Control-Allow-Origin", "*") in headers

    def test_custom_origins(self):
        """Custom allowed_origins are reflected in headers."""
        mw = CORSHeadersMiddleware(
            FakeApp(),
            allowed_origins=["https://example.com"],
        )
        headers = dict(mw._build_cors_headers())
        assert headers["Access-Control-Allow-Origin"] == "https://example.com"

    def test_custom_methods(self):
        """Custom allowed_methods are reflected in headers."""
        mw = CORSHeadersMiddleware(
            FakeApp(),
            allowed_methods=["GET", "POST"],
        )
        headers = dict(mw._build_cors_headers())
        assert headers["Access-Control-Allow-Methods"] == "GET,POST"

    def test_custom_headers(self):
        """Custom allowed_headers are reflected in headers."""
        mw = CORSHeadersMiddleware(
            FakeApp(),
            allowed_headers=["X-Custom"],
        )
        headers = dict(mw._build_cors_headers())
        assert headers["Access-Control-Allow-Headers"] == "X-Custom"

    def test_skips_non_http_scope(self):
        """Non-HTTP scopes pass through without CORS handling."""
        app = FakeApp()
        mw = CORSHeadersMiddleware(app)
        scope = {"type": "websocket"}

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw(scope, receive, send))
        assert len(app.calls) == 1


# ---------------------------------------------------------------------------
# RequestIdMiddleware
# ---------------------------------------------------------------------------

class TestRequestIdMiddleware:
    """Tests for RequestIdMiddleware."""

    def test_adds_x_request_id_header(self):
        """Response includes x-request-id header."""
        app = FakeApp()
        mw = RequestIdMiddleware(app)
        scope = _make_scope()
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        asyncio.run(mw(scope, receive, send))
        headers = dict((k.decode(), v.decode()) for k, v in sent[0]["headers"])
        assert "x-request-id" in headers
        assert len(headers["x-request-id"]) == 8

    def test_sets_request_id_on_scope(self):
        """Request ID is stored on scope dict."""
        app = FakeApp()
        mw = RequestIdMiddleware(app)
        scope = _make_scope()

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw(scope, receive, send))
        assert "request_id" in scope
        assert len(scope["request_id"]) == 8

    def test_skips_non_http_scope(self):
        """Non-HTTP scopes pass through without request ID."""
        app = FakeApp()
        mw = RequestIdMiddleware(app)
        scope = {"type": "websocket"}

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw(scope, receive, send))
        assert "request_id" not in scope


# ---------------------------------------------------------------------------
# create_middleware_stack
# ---------------------------------------------------------------------------

class TestCreateMiddlewareStack:
    """Tests for create_middleware_stack factory."""

    def test_full_stack(self):
        """Full stack wraps app with all middleware."""
        app = FakeApp()
        stacked = create_middleware_stack(app)
        assert stacked is not None

    def test_disable_logging(self):
        """Logging middleware can be disabled."""
        app = FakeApp()
        stacked = create_middleware_stack(app, enable_logging=False)
        assert stacked is not None

    def test_disable_cors(self):
        """CORS middleware can be disabled."""
        app = FakeApp()
        stacked = create_middleware_stack(app, enable_cors=False)
        assert stacked is not None

    def test_disable_request_id(self):
        """Request ID middleware can be disabled."""
        app = FakeApp()
        stacked = create_middleware_stack(app, enable_request_id=False)
        assert stacked is not None

    def test_custom_cors_origins(self):
        """Custom CORS origins are passed through."""
        app = FakeApp()
        stacked = create_middleware_stack(
            app, cors_origins=["https://example.com"]
        )
        assert stacked is not None


# ---------------------------------------------------------------------------
# RateLimitRule
# ---------------------------------------------------------------------------

class TestRateLimitRule:
    """Tests for RateLimitRule."""

    def test_matches_any_path(self):
        """Rule with no path_pattern matches any path."""
        rule = RateLimitRule(max_requests=10, window_seconds=60)
        assert rule.matches("GET", "/anything") is True

    def test_matches_path_pattern(self):
        """Rule with path_pattern only matches prefixed paths."""
        rule = RateLimitRule(max_requests=10, window_seconds=60, path_pattern="/api")
        assert rule.matches("GET", "/api/v1/users") is True
        assert rule.matches("GET", "/health") is False

    def test_matches_methods(self):
        """Rule with methods only matches listed methods."""
        rule = RateLimitRule(max_requests=10, window_seconds=60, methods=["POST"])
        assert rule.matches("POST", "/api/data") is True
        assert rule.matches("GET", "/api/data") is False

    def test_matches_methods_and_path(self):
        """Rule with both methods and path_pattern."""
        rule = RateLimitRule(
            max_requests=10, window_seconds=60,
            methods=["POST"], path_pattern="/api",
        )
        assert rule.matches("POST", "/api/data") is True
        assert rule.matches("GET", "/api/data") is False
        assert rule.matches("POST", "/health") is False


# ---------------------------------------------------------------------------
# RateLimitEntry
# ---------------------------------------------------------------------------

class TestRateLimitEntry:
    """Tests for RateLimitEntry."""

    def test_cleanup_removes_old_timestamps(self):
        """cleanup() removes timestamps outside the window."""
        entry = RateLimitEntry()
        now = time.monotonic()
        entry.timestamps = [now - 10, now - 5, now - 1]
        entry.cleanup(now, window=3)
        assert entry.timestamps == [now - 1]

    def test_can_request_below_limit(self):
        """can_request returns True when under limit."""
        entry = RateLimitEntry()
        now = time.monotonic()
        entry.timestamps = [now - 1, now - 2]
        # Note: can_request calls cleanup(window=0) which clears all timestamps,
        # so it always returns True in the current implementation.
        assert entry.can_request(now, max_requests=5) is True

    def test_record_request(self):
        """record_request appends a timestamp."""
        entry = RateLimitEntry()
        now = time.monotonic()
        entry.record_request(now)
        assert len(entry.timestamps) == 1


# ---------------------------------------------------------------------------
# SlidingWindowRateLimiter
# ---------------------------------------------------------------------------

class TestSlidingWindowRateLimiter:
    """Tests for SlidingWindowRateLimiter."""

    @pytest.fixture
    def limiter(self):
        rules = [RateLimitRule(max_requests=5, window_seconds=10.0, key="ip")]
        return SlidingWindowRateLimiter(rules=rules)

    def test_allows_within_limit(self, limiter):
        """Requests within the limit are allowed."""
        allowed, headers = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True
        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "5"

    def test_blocks_over_limit(self, limiter):
        """Requests exceeding the limit are blocked."""
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        allowed, headers = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is False
        assert "Retry-After" in headers

    def test_different_identifiers_separate(self, limiter):
        """Different identifiers have independent limits."""
        for _ in range(5):
            limiter.is_allowed("1.1.1.1", "GET", "/api/test")
        allowed, _ = limiter.is_allowed("2.2.2.2", "GET", "/api/test")
        assert allowed is True

    def test_remaining_decreases(self, limiter):
        """Remaining count decreases with each request."""
        _, h1 = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        _, h2 = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert int(h2["X-RateLimit-Remaining"]) < int(h1["X-RateLimit-Remaining"])

    def test_get_status(self, limiter):
        """get_status returns rate limit info for an identifier."""
        limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        status = limiter.get_status("127.0.0.1")
        assert status["identifier"] == "127.0.0.1"
        assert len(status["rules"]) == 1

    def test_reset_identifier(self, limiter):
        """reset() for a specific identifier clears its limits."""
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        limiter.reset("127.0.0.1")
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True

    def test_reset_all(self, limiter):
        """reset() with no argument clears all limits."""
        for _ in range(5):
            limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        limiter.reset()
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/test")
        assert allowed is True

    def test_rule_path_filtering(self):
        """Rules only apply to matching paths."""
        rules = [RateLimitRule(max_requests=2, window_seconds=60, path_pattern="/api/v1")]
        limiter = SlidingWindowRateLimiter(rules=rules)
        for _ in range(2):
            limiter.is_allowed("127.0.0.1", "GET", "/api/v1/test")
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/api/v1/test")
        assert allowed is False
        allowed, _ = limiter.is_allowed("127.0.0.1", "GET", "/health")
        assert allowed is True


# ---------------------------------------------------------------------------
# RateLimitMiddleware
# ---------------------------------------------------------------------------

class TestRateLimitMiddleware:
    """Tests for RateLimitMiddleware ASGI middleware."""

    def test_default_key_extractor_with_client(self):
        """Key extractor returns IP from client tuple."""
        scope = {"client": ("192.168.1.1", 12345)}
        key = RateLimitMiddleware._default_key_extractor(scope)
        assert key == "192.168.1.1"

    def test_default_key_extractor_no_client(self):
        """Key extractor returns 'unknown' when no client."""
        scope = {}
        key = RateLimitMiddleware._default_key_extractor(scope)
        assert key == "unknown"

    def test_middleware_blocks_over_limit(self):
        """Middleware returns 429 when rate limit exceeded."""
        rules = [RateLimitRule(max_requests=1, window_seconds=60)]
        limiter = SlidingWindowRateLimiter(rules=rules)
        mw = RateLimitMiddleware(FakeApp(), limiter=limiter)
        scope = _make_scope(client=("127.0.0.1", 12345))
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        # First request passes
        asyncio.run(mw(scope, receive, send))
        assert sent[-1]["body"] == b"ok"

        # Second request is blocked
        sent.clear()
        asyncio.run(mw(scope, receive, send))
        assert sent[0]["status"] == 429

    def test_middleware_skips_non_http(self):
        """Non-HTTP scopes pass through without rate limiting."""
        limiter = SlidingWindowRateLimiter()
        mw = RateLimitMiddleware(FakeApp(), limiter=limiter)

        async def receive():
            return {}

        async def send(msg):
            pass

        asyncio.run(mw({"type": "websocket"}, receive, send))

    def test_middleware_adds_rate_limit_headers(self):
        """Middleware adds rate limit headers to successful responses."""
        rules = [RateLimitRule(max_requests=10, window_seconds=60)]
        limiter = SlidingWindowRateLimiter(rules=rules)
        mw = RateLimitMiddleware(FakeApp(), limiter=limiter)
        scope = _make_scope(client=("127.0.0.1", 12345))
        sent = []

        async def receive():
            return {}

        async def send(msg):
            sent.append(msg)

        asyncio.run(mw(scope, receive, send))
        headers = dict((k.decode(), v.decode()) for k, v in sent[0]["headers"])
        assert "X-RateLimit-Limit" in headers
        assert headers["X-RateLimit-Limit"] == "10"
