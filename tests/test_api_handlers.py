"""Tests for personal_index.api.handlers."""

from unittest.mock import AsyncMock, patch

import pytest

from personal_index.api.handlers import (
    ContentTypeMiddleware,
    ErrorHandler,
    TimingMiddleware,
    handle_api_error,
)
from personal_index.api.models import APIError, APIResponse


class TestErrorHandler:
    @pytest.mark.asyncio
    async def test_handles_api_error(self):
        app = AsyncMock()
        app.side_effect = APIError("test error", status_code=400, error_code="bad_request")
        handler = ErrorHandler(app, debug=False)
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()
        await handler(scope, receive, send)
        assert send.call_count == 2
        start_msg = send.call_args_list[0][0][0]
        assert start_msg["status"] == 400

    @pytest.mark.asyncio
    async def test_handles_unexpected_exception(self):
        app = AsyncMock()
        app.side_effect = RuntimeError("unexpected")
        handler = ErrorHandler(app, debug=False)
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()
        with patch("personal_index.api.handlers.logger") as mock_log:
            await handler(scope, receive, send)
            # TICKET-67: logger.exception should be called without redundant exc arg
            mock_log.exception.assert_called_once()
            call_args = mock_log.exception.call_args
            assert call_args[0][0] == "Unhandled exception"
            # No extra positional args (the exception is auto-included by logging.exception)
            assert len(call_args[0]) == 1

    @pytest.mark.asyncio
    async def test_passes_through_non_http(self):
        app = AsyncMock()
        handler = ErrorHandler(app)
        scope = {"type": "websocket"}
        receive = AsyncMock()
        send = AsyncMock()
        await handler(scope, receive, send)
        app.assert_called_once_with(scope, receive, send)


class TestTimingMiddleware:
    @pytest.mark.asyncio
    async def test_adds_timing_header(self):
        app = AsyncMock()
        middleware = TimingMiddleware(app)
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "headers": []})
            await send({"type": "http.response.body", "body": b""})

        app.side_effect = mock_app
        await middleware(scope, receive, send)
        start_msg = send.call_args_list[0][0][0]
        headers = {h[0]: h[1] for h in start_msg["headers"]}
        assert b"x-response-time-ms" in headers


class TestContentTypeMiddleware:
    @pytest.mark.asyncio
    async def test_adds_json_content_type(self):
        app = AsyncMock()
        middleware = ContentTypeMiddleware(app)
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "headers": []})
            await send({"type": "http.response.body", "body": b""})

        app.side_effect = mock_app
        await middleware(scope, receive, send)
        start_msg = send.call_args_list[0][0][0]
        headers = {h[0]: h[1] for h in start_msg["headers"]}
        assert headers.get(b"content-type") == b"application/json"

    @pytest.mark.asyncio
    async def test_does_not_duplicate_content_type(self):
        app = AsyncMock()
        middleware = ContentTypeMiddleware(app)
        scope = {"type": "http"}
        receive = AsyncMock()
        send = AsyncMock()

        async def mock_app(scope, receive, send):
            await send({"type": "http.response.start", "headers": [(b"content-type", b"text/html")]})
            await send({"type": "http.response.body", "body": b""})

        app.side_effect = mock_app
        await middleware(scope, receive, send)
        start_msg = send.call_args_list[0][0][0]
        content_types = [h[1] for h in start_msg["headers"] if h[0].lower() == b"content-type"]
        assert len(content_types) == 1


class TestHandleApiError:
    def test_handles_api_error(self):
        exc = APIError("test", status_code=400, error_code="bad_request")
        result = handle_api_error(exc)
        assert isinstance(result, APIResponse)
        assert result.success is False

    def test_handles_generic_exception(self):
        exc = RuntimeError("something broke")
        result = handle_api_error(exc)
        assert isinstance(result, APIResponse)
        assert result.success is False
