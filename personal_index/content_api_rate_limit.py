"""API rate limiting for personal-index content API."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 100
    window_seconds: int = 60
    per_endpoint_limits: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "max_requests": self.max_requests,
            "window_seconds": self.window_seconds,
            "per_endpoint_limits": self.per_endpoint_limits,
        }


@dataclass
class RateLimitWindow:
    """A fixed time window for tracking requests."""
    max_requests: int
    window_seconds: int
    request_count: int = 0
    window_start: float = field(default_factory=time.time)

    def record_request(self) -> None:
        """Record a new request in this window."""
        self.request_count += 1

    def reset(self) -> None:
        """Reset the window counter."""
        self.request_count = 0
        self.window_start = time.time()

    def is_expired(self) -> bool:
        """Check if this window has expired."""
        return (time.time() - self.window_start) > self.window_seconds


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""
    allowed: bool
    remaining: int
    limit: int
    retry_after: Optional[float] = None
    reset: Optional[int] = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "allowed": self.allowed,
            "remaining": self.remaining,
            "limit": self.limit,
        }
        if self.retry_after is not None:
            result["retry_after"] = self.retry_after
        if self.reset is not None:
            result["reset"] = self.reset
        return result

    def to_headers(self) -> dict[str, str]:
        """Generate rate limit HTTP headers."""
        headers = {
            "X-RateLimit-Limit": str(self.limit),
            "X-RateLimit-Remaining": str(max(0, self.remaining)),
        }
        if self.reset is not None:
            headers["X-RateLimit-Reset"] = str(self.reset)
        if self.retry_after is not None:
            headers["Retry-After"] = str(int(self.retry_after))
        return headers


class RateLimitStore:
    """In-memory store for rate limit windows."""

    def __init__(self):
        self._windows: dict[str, RateLimitWindow] = {}

    def get_or_create(
        self, key: str, max_requests: int, window_seconds: int
    ) -> RateLimitWindow:
        """Get existing window or create a new one.

        Args:
            key: The rate limit key (e.g., IP address).
            max_requests: Maximum requests allowed.
            window_seconds: Window duration in seconds.

        Returns:
            RateLimitWindow instance.
        """
        if key in self._windows:
            window = self._windows[key]
            if window.is_expired():
                window.reset()
            return window
        window = RateLimitWindow(max_requests=max_requests, window_seconds=window_seconds)
        self._windows[key] = window
        return window

    def cleanup_expired(self) -> int:
        """Remove expired windows.

        Returns:
            Number of windows removed.
        """
        expired_keys = [
            k for k, w in self._windows.items() if w.is_expired()
        ]
        for key in expired_keys:
            del self._windows[key]
        return len(expired_keys)

    def size(self) -> int:
        """Get the number of active windows."""
        return len(self._windows)


class RateLimiter:
    """Fixed-window rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store = RateLimitStore()

    def check(self, key: str) -> RateLimitResult:
        """Check if a request is allowed under the rate limit.

        Args:
            key: The rate limit key (e.g., IP address, API key).

        Returns:
            RateLimitResult with allowed status and metadata.
        """
        window = self._store.get_or_create(key, self.max_requests, self.window_seconds)

        if window.request_count >= self.max_requests:
            elapsed = time.time() - window.window_start
            retry_after = max(0, self.window_seconds - elapsed)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=self.max_requests,
                retry_after=retry_after,
                reset=int(self.window_seconds),
            )

        window.record_request()
        remaining = self.max_requests - window.request_count
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=self.max_requests,
            reset=int(self.window_seconds),
        )

    def get_remaining(self, key: str) -> int:
        """Get remaining requests for a key.

        Args:
            key: The rate limit key.

        Returns:
            Number of remaining requests.
        """
        if key not in self._store._windows:
            return self.max_requests
        window = self._store._windows[key]
        if window.is_expired():
            return self.max_requests
        return max(0, self.max_requests - window.request_count)

    def reset(self, key: str) -> None:
        """Reset the rate limit for a key.

        Args:
            key: The rate limit key.
        """
        if key in self._store._windows:
            self._store._windows[key].reset()


class SlidingWindowLimiter:
    """Sliding window rate limiter using request timestamps."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._requests: dict[str, list[float]] = {}

    def check(self, key: str) -> RateLimitResult:
        """Check if a request is allowed.

        Args:
            key: The rate limit key.

        Returns:
            RateLimitResult with allowed status.
        """
        now = time.time()
        window_start = now - self.window_seconds

        if key not in self._requests:
            self._requests[key] = []

        # Remove expired timestamps
        self._requests[key] = [
            ts for ts in self._requests[key] if ts > window_start
        ]

        if len(self._requests[key]) >= self.max_requests:
            oldest = self._requests[key][0] if self._requests[key] else now
            retry_after = max(0, oldest + self.window_seconds - now)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=self.max_requests,
                retry_after=retry_after,
            )

        self._requests[key].append(now)
        remaining = self.max_requests - len(self._requests[key])
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=self.max_requests,
        )


class FixedWindowLimiter:
    """Fixed window rate limiter."""

    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._store = RateLimitStore()

    def check(self, key: str) -> RateLimitResult:
        """Check if a request is allowed.

        Args:
            key: The rate limit key.

        Returns:
            RateLimitResult with allowed status.
        """
        window = self._store.get_or_create(key, self.max_requests, self.window_seconds)

        if window.request_count >= self.max_requests:
            elapsed = time.time() - window.window_start
            retry_after = max(0, self.window_seconds - elapsed)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=self.max_requests,
                retry_after=retry_after,
            )

        window.record_request()
        remaining = self.max_requests - window.request_count
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=self.max_requests,
        )


class TokenBucketLimiter:
    """Token bucket rate limiter."""

    def __init__(self, rate: float = 10.0, capacity: int = 10):
        self.rate = rate  # tokens per second
        self.capacity = capacity
        self._buckets: dict[str, dict] = {}

    def check(self, key: str) -> RateLimitResult:
        """Check if a request is allowed.

        Args:
            key: The rate limit key.

        Returns:
            RateLimitResult with allowed status.
        """
        now = time.time()

        if key not in self._buckets:
            self._buckets[key] = {
                "tokens": float(self.capacity),
                "last_refill": now,
            }

        bucket = self._buckets[key]
        elapsed = now - bucket["last_refill"]
        bucket["tokens"] = min(
            self.capacity, bucket["tokens"] + elapsed * self.rate
        )
        bucket["last_refill"] = now

        if bucket["tokens"] < 1.0:
            retry_after = (1.0 - bucket["tokens"]) / self.rate
            return RateLimitResult(
                allowed=False,
                remaining=0,
                limit=self.capacity,
                retry_after=retry_after,
            )

        bucket["tokens"] -= 1.0
        remaining = int(bucket["tokens"])
        return RateLimitResult(
            allowed=True,
            remaining=remaining,
            limit=self.capacity,
        )


class RateLimitMiddleware:
    """Middleware for applying rate limits to requests."""

    def __init__(
        self,
        max_requests: int = 100,
        window_seconds: int = 60,
        key_extractor: Optional[str] = None,
    ):
        self.limiter = RateLimiter(
            max_requests=max_requests,
            window_seconds=window_seconds,
        )
        self.key_extractor = key_extractor or "client_ip"

    def process_request(self, request: dict) -> dict:
        """Process a request through the rate limiter.

        Args:
            request: Request dict containing client info.

        Returns:
            Dict with rate limit result and headers.
        """
        key = request.get(self.key_extractor, request.get("client_ip", "unknown"))
        result = self.limiter.check(key)

        response: dict[str, Any] = {
            "allowed": result.allowed,
            "remaining": result.remaining,
            "limit": result.limit,
            "headers": result.to_headers(),
        }

        if not result.allowed:
            response["error"] = "Rate limit exceeded"
            if result.retry_after:
                response["retry_after"] = result.retry_after

        return response


def create_rate_limiter(
    max_requests: int = 100,
    window_seconds: int = 60,
) -> RateLimiter:
    """Factory function to create a rate limiter.

    Args:
        max_requests: Maximum requests per window.
        window_seconds: Window duration in seconds.

    Returns:
        RateLimiter instance.
    """
    return RateLimiter(max_requests=max_requests, window_seconds=window_seconds)


def create_rate_limit_middleware(
    max_requests: int = 100,
    window_seconds: int = 60,
) -> RateLimitMiddleware:
    """Factory function to create rate limit middleware.

    Args:
        max_requests: Maximum requests per window.
        window_seconds: Window duration in seconds.

    Returns:
        RateLimitMiddleware instance.
    """
    return RateLimitMiddleware(max_requests=max_requests, window_seconds=window_seconds)


def check_rate_limit(limiter: RateLimiter, key: str) -> RateLimitResult:
    """Convenience function to check rate limit.

    Args:
        limiter: The rate limiter instance.
        key: The rate limit key.

    Returns:
        RateLimitResult.
    """
    return limiter.check(key)
