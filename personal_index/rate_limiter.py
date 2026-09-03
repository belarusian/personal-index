"""Rate limiting for web requests using token bucket algorithm."""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 10
    window_seconds: float = 60.0
    burst_size: int | None = None

    def __post_init__(self):
        if self.burst_size is None:
            self.burst_size = self.max_requests


@dataclass
class RateLimitStatus:
    """Current status of rate limiting."""
    remaining: int
    limit: int
    reset_at: float
    retry_after: float = 0.0


class TokenBucket:
    """Token bucket rate limiter for a single domain."""

    def __init__(self, config: RateLimitConfig):
        self._max_tokens = config.max_requests
        self._burst_size: int = config.burst_size if config.burst_size is not None else config.max_requests
        self._refill_rate = config.max_requests / config.window_seconds
        self._tokens = float(self._burst_size)
        self._last_refill = time.monotonic()
        self._lock = threading.RLock()

    def _refill(self):
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._burst_size,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    def acquire(self) -> bool:
        """Try to acquire a token. Returns True if successful."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def wait_time(self) -> float:
        """Get time to wait before next request can be made."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                return 0.0
            return (1.0 - self._tokens) / self._refill_rate

    def status(self) -> RateLimitStatus:
        """Get current rate limit status."""
        with self._lock:
            self._refill()
            remaining = int(self._tokens)
            reset_at = time.monotonic() + (self._burst_size - self._tokens) / self._refill_rate
            return RateLimitStatus(
                remaining=remaining,
                limit=self._burst_size,
                reset_at=reset_at,
                retry_after=self.wait_time(),
            )


class RateLimiter:
    """Rate limiter that manages limits per domain."""

    def __init__(self, default_config: RateLimitConfig | None = None):
        self._default_config = default_config or RateLimitConfig()
        self._buckets: dict[str, TokenBucket] = {}
        self._configs: dict[str, RateLimitConfig] = {}
        self._lock = threading.Lock()

    def set_domain_config(self, domain: str, config: RateLimitConfig):
        """Set rate limit config for a specific domain."""
        with self._lock:
            self._configs[domain] = config
            self._buckets[domain] = TokenBucket(config)

    def _get_bucket(self, domain: str) -> TokenBucket:
        """Get or create a token bucket for a domain."""
        if domain not in self._buckets:
            config = self._configs.get(domain, self._default_config)
            self._buckets[domain] = TokenBucket(config)
        return self._buckets[domain]

    def can_request(self, domain: str) -> bool:
        """Check if a request to the domain is allowed.

        Consumes one token from the domain's budget when the request is
        allowed (returns True); returns False without consuming a token
        when the budget is exhausted. This is not a side-effect-free
        probe: each successful call spends a token, so callers that only
        want to inspect the budget should use get_status()/get_wait_time().
        """
        bucket = self._get_bucket(domain)
        return bucket.acquire()

    def wait_for_request(self, domain: str, timeout: float = 30.0) -> bool:
        """Wait until a request can be made, or timeout."""
        bucket = self._get_bucket(domain)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if bucket.acquire():
                return True
            wait = bucket.wait_time()
            if wait > 0:
                time.sleep(min(wait, deadline - time.monotonic()))
        return False

    def get_status(self, domain: str) -> RateLimitStatus:
        """Get rate limit status for a domain."""
        bucket = self._get_bucket(domain)
        return bucket.status()

    def get_wait_time(self, domain: str) -> float:
        """Get wait time for a domain."""
        bucket = self._get_bucket(domain)
        return bucket.wait_time()

    def reset_domain(self, domain: str):
        """Reset rate limit for a domain."""
        with self._lock:
            config = self._configs.get(domain, self._default_config)
            self._buckets[domain] = TokenBucket(config)

    def reset_all(self):
        """Reset all rate limits."""
        with self._lock:
            for domain, config in self._configs.items():
                self._buckets[domain] = TokenBucket(config)
            # Reset default buckets
            default_domains = set(self._buckets.keys()) - set(self._configs.keys())
            for domain in default_domains:
                self._buckets[domain] = TokenBucket(self._default_config)

    def get_all_statuses(self) -> dict[str, RateLimitStatus]:
        """Get rate limit status for all tracked domains."""
        return {
            domain: bucket.status()
            for domain, bucket in self._buckets.items()
        }
