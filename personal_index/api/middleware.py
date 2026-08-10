"""API middleware for personal-index."""

from __future__ import annotations

import logging
import time
from typing import Any, Optional

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """Middleware that logs all incoming requests."""

    def __init__(self, app, log_body: bool = False):
        self.app = app
        self.log_body = log_body

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        start_time = time.monotonic()
        path = scope.get("path", "unknown")
        method = scope.get("method", "UNKNOWN")

        # Capture response status
        status_code = None
        original_send = send

        async def capture_send(message):
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message.get("status", 0)
            await original_send(message)

        await self.app(scope, receive, capture_send)
        duration = time.monotonic() - start_time
        logger.info(
            "Request %s %s -> %s (%.3fs)",
            method,
            path,
            status_code or 0,
            duration,
        )


class CORSHeadersMiddleware:
    """Middleware that adds CORS headers to responses."""

    def __init__(
        self,
        app,
        allowed_origins: Optional[list] = None,
        allowed_methods: Optional[list] = None,
        allowed_headers: Optional[list] = None,
    ):
        self.app = app
        self.allowed_origins = allowed_origins or ["*"]
        self.allowed_methods = allowed_methods or [
            "GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"
        ]
        self.allowed_headers = allowed_headers or [
            "Content-Type", "Authorization", "X-Requested-With"
        ]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if scope["method"] == "OPTIONS":
            headers = self._build_cors_headers()
            await send({
                "type": "http.response.start",
                "status": 204,
                "headers": [[k.encode(), v.encode()] for k, v in headers],
            })
            await send({"type": "http.response.body", "body": b""})
            return

        original_send = send

        async def add_cors_headers(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                for key, value in self._build_cors_headers():
                    headers_list.append([key.encode(), value.encode()])
                message["headers"] = headers_list
            await original_send(message)

        await self.app(scope, receive, add_cors_headers)

    def _build_cors_headers(self) -> list:
        """Build CORS headers list."""
        return [
            ("Access-Control-Allow-Origin", ",".join(self.allowed_origins)),
            ("Access-Control-Allow-Methods", ",".join(self.allowed_methods)),
            ("Access-Control-Allow-Headers", ",".join(self.allowed_headers)),
        ]


class RequestIdMiddleware:
    """Middleware that assigns a unique request ID to each request."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        import uuid
        request_id = str(uuid.uuid4())[:8]
        scope["request_id"] = request_id

        original_send = send

        async def add_request_id(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                headers_list.append([b"x-request-id", request_id.encode()])
                message["headers"] = headers_list
            await original_send(message)

        await self.app(scope, receive, add_request_id)


def create_middleware_stack(
    app,
    enable_logging: bool = True,
    enable_cors: bool = True,
    enable_request_id: bool = True,
    cors_origins: Optional[list] = None,
) -> Any:
    """Create a stack of middleware for the application.

    Args:
        app: The base application.
        enable_logging: Whether to enable request logging.
        enable_cors: Whether to enable CORS headers.
        enable_request_id: Whether to enable request IDs.
        cors_origins: List of allowed CORS origins.

    Returns:
        The application wrapped with middleware.
    """
    if enable_request_id:
        app = RequestIdMiddleware(app)
    if enable_logging:
        app = RequestLoggingMiddleware(app)
    if enable_cors:
        app = CORSHeadersMiddleware(app, allowed_origins=cors_origins)
    return app
