"""Tests for API middleware."""

from __future__ import annotations

import logging
import pytest

from personal_index.api.middleware import (
    CORSHeadersMiddleware,
    RequestIdMiddleware,
    RequestLoggingMiddleware,
    create_middleware_stack,
)


class FakeApp:
    """Fake ASGI app for testing middleware."""

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


class TestRequestLoggingMiddleware:
    """Tests for request logging middleware."""

    def test_logs_request(self, caplog):
        """Test that middleware logs requests."""
        caplog.set_level(logging.INFO, logger="personal_index.api.middleware")
        app = FakeApp()
        middleware = RequestLoggingMiddleware(app)

        scope = {"type": "http", "path": "/test", "method": "GET"}
        received_messages = []
        sent_messages = []

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent_messages.append(message)

        import asyncio
        asyncio.run(middleware(scope, receive, send))

        assert len(sent_messages) == 2
        assert "Request GET /test" in caplog.text

    def test_skips_non_http(self):
        """Test that non-HTTP scopes pass through."""
        app = FakeApp()
        middleware = RequestLoggingMiddleware(app)

        scope = {"type": "websocket"}

        async def receive():
            return {}

        async def send(message):
            pass

        import asyncio
        asyncio.run(middleware(scope, receive, send))
        assert len(app.calls) == 1


class TestCORSHeadersMiddleware:
    """Tests for CORS headers middleware."""

    def test_adds_cors_headers(self):
        """Test that CORS headers are added to responses."""
        app = FakeApp()
        middleware = CORSHeadersMiddleware(app)

        scope = {"type": "http", "method": "GET"}
        sent_messages = []

        async def receive():
            return {"type": "http.request"}

        async def send(message):
            sent_messages.append(message)

        import asyncio
        asyncio.run(middleware(scope, receive, send))

        headers = dict(
            (k.decode(), v.decode())
            for k, v in sent_messages[0]["headers"]
        )
        assert "Access-Control-Allow-Origin" in headers

    def test_options_returns_204(self):
        """Test that OPTIONS requests return 204."""
        app = FakeApp()
        middleware = CORSHeadersMiddleware(app)

        scope = {"type": "http", "method": "OPTIONS"}
        sent_messages = []

        async def receive():
            return {}

        async def send(message):
            sent_messages.append(message)

        import asyncio
        asyncio.run(middleware(scope, receive, send))

        assert sent_messages[0]["status"] == 204

    def test_custom_origins(self):
        """Test custom allowed origins."""
        app = FakeApp()
        middleware = CORSHeadersMiddleware(
            app, allowed_origins=["https://example.com"]
        )
        headers = middleware._build_cors_headers()
        origin_header = dict(headers)["Access-Control-Allow-Origin"]
        assert origin_header == "https://example.com"


class TestRequestIdMiddleware:
    """Tests for request ID middleware."""

    def test_adds_request_id_header(self):
        """Test that request ID header is added."""
        app = FakeApp()
        middleware = RequestIdMiddleware(app)

        scope = {"type": "http", "method": "GET"}
        sent_messages = []

        async def receive():
            return {}

        async def send(message):
            sent_messages.append(message)

        import asyncio
        asyncio.run(middleware(scope, receive, send))

        headers = dict(
            (k.decode(), v.decode())
            for k, v in sent_messages[0]["headers"]
        )
        assert "x-request-id" in headers
        assert len(headers["x-request-id"]) == 8

    def test_sets_scope_request_id(self):
        """Test that request ID is set on scope."""
        app = FakeApp()
        middleware = RequestIdMiddleware(app)

        scope = {"type": "http", "method": "GET"}

        async def receive():
            return {}

        async def send(message):
            pass

        import asyncio
        asyncio.run(middleware(scope, receive, send))
        assert "request_id" in scope


class TestCreateMiddlewareStack:
    """Tests for middleware stack creation."""

    def test_creates_full_stack(self):
        """Test creating full middleware stack."""
        app = FakeApp()
        stacked = create_middleware_stack(app)
        assert stacked is not None

    def test_disables_logging(self):
        """Test disabling logging middleware."""
        app = FakeApp()
        stacked = create_middleware_stack(app, enable_logging=False)
        assert stacked is not None

    def test_disables_cors(self):
        """Test disabling CORS middleware."""
        app = FakeApp()
        stacked = create_middleware_stack(app, enable_cors=False)
        assert stacked is not None
