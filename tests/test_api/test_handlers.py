"""Tests for API error handlers and middleware."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, MagicMock

import pytest

from personal_index.api.handlers import (
    APIError,
    ContentTypeMiddleware,
    ErrorHandler,
    TimingMiddleware,
    handle_api_error,
)
from personal_index.api.models import (
    APIResponse,
    ForbiddenError,
    NotFoundError,
    UnauthorizedError,
    ValidationError,
)


async def simple_app(scope, receive, send):
    """Simple ASGI app for testing."""
    await send({
        "type": "http.response.start",
        "status": 200,
        "headers": [],
    })
    await send({"type": "http.response.body", "body": b"ok"})


async def error_app(scope, receive, send):
    """ASGI app that raises an error."""
    raise NotFoundError("Resource not found")


async def exception_app(scope, receive, send):
    """ASGI app that raises a generic exception."""
    raise RuntimeError("Something broke")


class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_passes_through_normal_response(self):
        handler = ErrorHandler(simple_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await handler({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        assert len(messages) == 2
        assert messages[0]["status"] == 200

    @pytest.mark.asyncio
    async def test_handles_not_found_error(self):
        handler = ErrorHandler(error_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await handler({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        assert messages[0]["status"] == 404
        body = json.loads(messages[1]["body"])
        assert body["error"] == "not_found"

    @pytest.mark.asyncio
    async def test_handles_generic_exception(self):
        handler = ErrorHandler(exception_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await handler({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        assert messages[0]["status"] == 500
        body = json.loads(messages[1]["body"])
        assert body["error"] == "internal_error"

    @pytest.mark.asyncio
    async def test_debug_mode_shows_details(self):
        handler = ErrorHandler(error_app, debug=True)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await handler({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        body = json.loads(messages[1]["body"])
        assert body["message"] == "Resource not found"

    @pytest.mark.asyncio
    async def test_non_http_scope(self):
        handler = ErrorHandler(simple_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await handler({"type": "websocket"}, AsyncMock(), mock_send)
        assert len(messages) == 2


class TestTimingMiddleware:
    @pytest.mark.asyncio
    async def test_adds_timing_header(self):
        middleware = TimingMiddleware(simple_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await middleware({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        headers = {h[0]: h[1] for h in messages[0]["headers"]}
        assert b"x-response-time-ms" in headers


class TestContentTypeMiddleware:
    @pytest.mark.asyncio
    async def test_adds_json_content_type(self):
        middleware = ContentTypeMiddleware(simple_app)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await middleware({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        headers = {h[0]: h[1] for h in messages[0]["headers"]}
        assert headers.get(b"content-type") == b"application/json"

    @pytest.mark.asyncio
    async def test_preserves_existing_content_type(self):
        async def app_with_ct(scope, receive, send):
            await send({
                "type": "http.response.start",
                "status": 200,
                "headers": [(b"content-type", b"text/html")],
            })
            await send({"type": "http.response.body", "body": b"ok"})

        middleware = ContentTypeMiddleware(app_with_ct)
        messages = []

        async def mock_send(message):
            messages.append(message)

        await middleware({"type": "http", "method": "GET", "path": "/"}, AsyncMock(), mock_send)
        headers = {h[0]: h[1] for h in messages[0]["headers"]}
        assert headers[b"content-type"] == b"text/html"


class TestHandleAPIError:
    def test_handles_api_error(self):
        exc = NotFoundError("Not found")
        resp = handle_api_error(exc)
        assert resp.success is False
        assert resp.error == "not_found"

    def test_handles_generic_exception(self):
        exc = RuntimeError("Boom")
        resp = handle_api_error(exc)
        assert resp.success is False
        assert resp.error == "internal_error"
