"""Rate limiting for content API calls.

Provides per-endpoint and per-client rate limiting with configurable
windows, burst sizes, and retry-after headers.
"""

from __future__ import annotations

import time
import threading
import logging
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""

    max_requests: int = 100
    window_seconds: float = 60.0
    burst_size: int = 10

    @property
    def rate_per_second(self) -> float:
        return self.max_requests / self.window_seconds


@dataclass
class RateLimitResult:
    """Result of a rate limit check."""

    allowed: bool
    remaining: int
    retry_after: float = 0.0

    @property
    def is_limited(self) -> bool:
        return not self.allowed


class _EndpointBucket:
    """Token bucket for a single endpoint/client pair."""

    def __init__(self, config: RateLimitConfig) -> None:
        self._max_tokens = float(config.burst_size)
        self._refill_rate = config.rate_per_second
        self._tokens = self._max_tokens
        self._last_refill = time.monotonic()
        self._lock = threading.Lock()
        self._total_requests = 0
        self._total_limited = 0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._max_tokens, self._tokens + elapsed * self._refill_rate)
        self._last_refill = now

    def try_acquire(self) -> RateLimitResult:
        with self._lock:
            self._refill()
            self._total_requests += 1
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return RateLimitResult(
                    allowed=True,
                    remaining=int(self._tokens),
                    retry_after=0.0,
                )
            self._total_limited += 1
            wait_time = (1.0 - self._tokens) / self._refill_rate if self._refill_rate > 0 else 1.0
            return RateLimitResult(
                allowed=False,
                remaining=0,
                retry_after=round(wait_time, 2),
            )

    def get_wait_time(self) -> float:
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                return 0.0
            return (1.0 - self._tokens) / self._refill_rate if self._refill_rate > 0 else 1.0

    def stats(self) -> dict[str, Any]:
        with self._lock:
            self._refill()
            return {
                "tokens": round(self._tokens, 2),
                "max_tokens": self._max_tokens,
                "total_requests": self._total_requests,
                "total_limited": self._total_limited,
            }


class ContentRateLimiter:
    """Rate limiter for content API operations.

    Supports per-endpoint and per-client rate limiting with
    configurable burst sizes and refill rates.
    """

    def __init__(self, default_config: Optional[RateLimitConfig] = None) -> None:
        self._default_config = default_config or RateLimitConfig()
        self._configs: dict[str, RateLimitConfig] = {}
        self._buckets: dict[str, _EndpointBucket] = {}
        self._lock = threading.Lock()

    def set_config(self, key: str, config: RateLimitConfig) -> None:
        """Set rate limit config for a specific key (endpoint/client).

        Args:
            key: Unique identifier (e.g., "api:extract" or "client:123").
            config: Rate limit configuration.
        """
        with self._lock:
            self._configs[key] = config
            self._buckets[key] = _EndpointBucket(config)

    def _get_bucket(self, key: str) -> _EndpointBucket:
        if key not in self._buckets:
            config = self._configs.get(key, self._default_config)
            self._buckets[key] = _EndpointBucket(config)
        return self._buckets[key]

    def check(self, key: str) -> RateLimitResult:
        """Check if a request is allowed under rate limits.

        Args:
            key: Rate limit key (endpoint, client, or composite).

        Returns:
            RateLimitResult with allowed status and metadata.
        """
        bucket = self._get_bucket(key)
        return bucket.try_acquire()

    def wait_if_needed(self, key: str, timeout: float = 30.0) -> bool:
        """Wait until a request can be made, or timeout.

        Args:
            key: Rate limit key.
            timeout: Maximum wait time in seconds.

        Returns:
            True if request was allowed, False if timed out.
        """
        bucket = self._get_bucket(key)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            result = bucket.try_acquire()
            if result.allowed:
                return True
            wait = bucket.get_wait_time()
            if wait > 0:
                time.sleep(min(wait, max(0, deadline - time.monotonic())))
        return False

    def get_wait_time(self, key: str) -> float:
        """Get wait time before next request can be made.

        Args:
            key: Rate limit key.

        Returns:
            Wait time in seconds (0.0 if no wait needed).
        """
        bucket = self._get_bucket(key)
        return bucket.get_wait_time()

    def reset(self, key: str) -> None:
        """Reset rate limit for a specific key.

        Args:
            key: Rate limit key to reset.
        """
        with self._lock:
            config = self._configs.get(key, self._default_config)
            self._buckets[key] = _EndpointBucket(config)

    def reset_all(self) -> None:
        """Reset all rate limits."""
        with self._lock:
            for key, config in self._configs.items():
                self._buckets[key] = _EndpointBucket(config)
            default_keys = set(self._buckets.keys()) - set(self._configs.keys())
            for key in default_keys:
                self._buckets[key] = _EndpointBucket(self._default_config)

    def stats(self, key: Optional[str] = None) -> dict[str, Any]:
        """Get rate limit statistics.

        Args:
            key: Optional specific key to get stats for.

        Returns:
            Statistics dictionary.
        """
        if key:
            bucket = self._buckets.get(key)
            if bucket:
                return {"key": key, **bucket.stats()}
            return {"key": key, "total_requests": 0, "total_limited": 0}

        return {
            "tracked_keys": len(self._buckets),
            "buckets": {k: v.stats() for k, v in self._buckets.items()},
        }
