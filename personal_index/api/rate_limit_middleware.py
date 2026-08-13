"""Rate limiting middleware for the API server."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class RateLimitRule:
    """A rate limiting rule."""

    max_requests: int
    window_seconds: float
    key: str = "ip"  # ip, user, api_key
    path_pattern: str | None = None
    methods: list[str] | None = None

    def matches(self, method: str, path: str) -> bool:
        """Check if this rule matches the request."""
        if self.methods and method not in self.methods:
            return False
        return not (self.path_pattern and not path.startswith(self.path_pattern))


@dataclass
class RateLimitEntry:
    """Tracks request timestamps for rate limiting."""

    timestamps: list[float] = field(default_factory=list)
    window_start: float = field(default_factory=time.monotonic)

    def cleanup(self, current_time: float, window: float):
        """Remove expired timestamps."""
        cutoff = current_time - window
        self.timestamps = [t for t in self.timestamps if t > cutoff]

    def can_request(self, current_time: float, max_requests: int) -> bool:
        """Check if a request is allowed."""
        self.cleanup(current_time, window=0)  # Will be set by caller
        return len(self.timestamps) < max_requests

    def record_request(self, current_time: float):
        """Record a new request timestamp."""
        self.timestamps.append(current_time)


class SlidingWindowRateLimiter:
    """Sliding window rate limiter for API requests."""

    def __init__(self, rules: list[RateLimitRule] | None = None):
        self.rules = rules or [
            RateLimitRule(max_requests=100, window_seconds=60.0, key="ip"),
        ]
        self._buckets: dict[str, dict[str, RateLimitEntry]] = defaultdict(dict)
        self._global_limit: int = 1000
        self._global_window: float = 60.0
        self._global_timestamps: list[float] = []

    def _get_key(self, identifier: str, rule: RateLimitRule) -> str:
        """Generate a rate limit key."""
        return f"{rule.key}:{identifier}:{rule.path_pattern or '*'}"

    def is_allowed(
        self,
        identifier: str,
        method: str,
        path: str,
    ) -> tuple[bool, dict[str, Any]]:
        """Check if a request is allowed under rate limits."""
        now = time.monotonic()
        headers: dict[str, Any] = {}

        if self._check_global_limit(now, headers):
            return False, headers

        for rule in self.rules:
            if not rule.matches(method, path):
                continue

            key = self._get_key(identifier, rule)
            if key not in self._buckets[identifier]:
                self._buckets[identifier][key] = RateLimitEntry()

            entry = self._buckets[identifier][key]
            entry.cleanup(now, rule.window_seconds)

            if len(entry.timestamps) >= rule.max_requests:
                self._build_rejected_headers(entry, now, rule, headers)
                return False, headers

            entry.record_request(now)
            self._build_allowed_headers(entry, now, rule, headers)

        self._global_timestamps.append(now)
        return True, headers

    def _check_global_limit(
        self, now: float, headers: dict[str, Any]
    ) -> bool:
        """Return True if global limit exceeded."""
        self._global_timestamps = [
            t for t in self._global_timestamps if now - t < self._global_window
        ]
        if len(self._global_timestamps) >= self._global_limit:
            retry_after = self._global_window - (now - self._global_timestamps[0])
            headers["Retry-After"] = str(max(1, int(retry_after)))
            return True
        return False

    def _build_rejected_headers(
        self,
        entry: RateLimitEntry,
        now: float,
        rule: RateLimitRule,
        headers: dict[str, Any],
    ) -> None:
        """Build headers for a rate-limited response."""
        oldest = entry.timestamps[0] if entry.timestamps else now
        retry_after = rule.window_seconds - (now - oldest)
        headers["Retry-After"] = str(max(1, int(retry_after)))
        headers["X-RateLimit-Limit"] = str(rule.max_requests)
        headers["X-RateLimit-Remaining"] = "0"

    def _build_allowed_headers(
        self,
        entry: RateLimitEntry,
        now: float,
        rule: RateLimitRule,
        headers: dict[str, Any],
    ) -> None:
        """Build headers for an allowed response."""
        remaining = rule.max_requests - len(entry.timestamps)
        headers["X-RateLimit-Limit"] = str(rule.max_requests)
        headers["X-RateLimit-Remaining"] = str(remaining)
        headers["X-RateLimit-Reset"] = str(int(now + rule.window_seconds))

    def get_status(self, identifier: str) -> dict[str, Any]:
        """Get rate limit status for an identifier."""
        now = time.monotonic()
        status = {"identifier": identifier, "rules": []}

        for rule in self.rules:
            key = self._get_key(identifier, rule)
            entry = self._buckets.get(identifier, {}).get(key)
            if entry:
                entry.cleanup(now, rule.window_seconds)
                remaining = max(0, rule.max_requests - len(entry.timestamps))
                status["rules"].append({  # type: ignore[attr-defined]
                    "key": rule.key,
                    "limit": rule.max_requests,
                    "remaining": remaining,
                    "window": rule.window_seconds,
                })

        return status

    def reset(self, identifier: str | None = None):
        """Reset rate limits.

        Args:
            identifier: Specific identifier to reset, or None for all.
        """
        if identifier:
            self._buckets.pop(identifier, None)
        else:
            self._buckets.clear()
        self._global_timestamps.clear()


class RateLimitMiddleware:
    """ASGI middleware for rate limiting."""

    def __init__(
        self,
        app: Any,
        limiter: SlidingWindowRateLimiter | None = None,
        key_extractor: Callable | None = None,
    ):
        self.app = app
        self.limiter = limiter or SlidingWindowRateLimiter()
        self.key_extractor = key_extractor or self._default_key_extractor

    @staticmethod
    def _default_key_extractor(scope: dict[str, Any]) -> str:
        """Extract client identifier from ASGI scope."""
        client = scope.get("client")
        if client:
            return client[0]  # type: ignore[no-any-return]  # IP address
        return "unknown"

    async def __call__(self, scope, receive, send):
        """Process request with rate limiting."""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        identifier = self.key_extractor(scope)
        method = scope.get("method", "GET")
        path = scope.get("path", "/")

        allowed, headers = self.limiter.is_allowed(identifier, method, path)

        if not allowed:
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    [k.encode(), v.encode()]
                    for k, v in headers.items()
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Rate limit exceeded"}',
            })
            return

        # Add rate limit headers to response
        original_send = send

        async def add_headers(message):
            if message["type"] == "http.response.start":
                headers_list = list(message.get("headers", []))
                for k, v in headers.items():
                    headers_list.append([k.encode(), v.encode()])
                message["headers"] = headers_list
            await original_send(message)

        await self.app(scope, receive, add_headers)
