"""Error handlers and middleware for the personal-index API."""

from __future__ import annotations

import logging
import time
from typing import Any

from personal_index.api.models import (
    APIError,
    APIResponse,
    ErrorResponse,
)

logger = logging.getLogger(__name__)


class ErrorHandler:
    """ASGI middleware that catches API exceptions and returns proper error responses."""

    def __init__(self, app: Any, debug: bool = False):
        self.app = app
        self.debug = debug

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        try:
            await self.app(scope, receive, send)
        except APIError as exc:
            error_response = ErrorResponse(
                error=exc.error_code,
                message=exc.message,
                status_code=exc.status_code,
                details=exc.details if self.debug else {},
            )
            await self._send_error(send, error_response)
        except Exception as exc:
            logger.exception("Unhandled exception")
            error_response = ErrorResponse(
                error="internal_error",
                message="An unexpected error occurred" if not self.debug else str(exc),
                status_code=500,
            )
            await self._send_error(send, error_response)

    @staticmethod
    async def _send_error(send, error_response: ErrorResponse) -> None:
        """Send an error response."""
        body = error_response.to_dict()
        import json
        await send({
            "type": "http.response.start",
            "status": error_response.status_code,
            "headers": [
                (b"content-type", b"application/json"),
            ],
        })
        await send({
            "type": "http.response.body",
            "body": json.dumps(body).encode("utf-8"),
        })


class TimingMiddleware:
    """Middleware that adds response timing headers."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start = time.monotonic()
        original_send = send

        async def timed_send(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                duration_ms = (time.monotonic() - start) * 1000
                headers_list.append((b"x-response-time-ms", f"{duration_ms:.1f}".encode()))
                message["headers"] = headers_list
            await original_send(message)

        await self.app(scope, receive, timed_send)


class ContentTypeMiddleware:
    """Middleware that ensures JSON content-type for API responses."""

    def __init__(self, app: Any):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        original_send = send

        async def ensure_json_type(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                has_content_type = any(
                    h[0].lower() == b"content-type" for h in headers_list
                )
                if not has_content_type:
                    headers_list.append((b"content-type", b"application/json"))
                message["headers"] = headers_list
            await original_send(message)

        await self.app(scope, receive, ensure_json_type)


def handle_api_error(exc: Exception) -> APIResponse:
    """Convert an exception to an API response.

    Args:
        exc: The exception to convert.

    Returns:
        APIResponse with error details.
    """
    if isinstance(exc, APIError):
        return APIResponse.error_response(
            message=exc.message,
            error_code=exc.error_code,
        )
    return APIResponse.error_response(
        message="An unexpected error occurred",
        error_code="internal_error",
    )
