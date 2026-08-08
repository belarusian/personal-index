"""Rate limiting for web crawling operations."""

from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass
class RateLimitConfig:
    """Configuration for rate limiting."""
    max_requests: int = 10
    time_window: float = 60.0  # seconds
    per_domain: bool = True


class RateLimiter:
    """Track and enforce rate limits for URL requests."""

    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.config = config or RateLimitConfig()
        self._request_times: Dict[str, List[float]] = defaultdict(list)
        self._global_times: List[float] = []

    def can_request(self, url: str) -> bool:
        """Check if a request to the given URL is allowed."""
        if self.config.per_domain:
            domain = self._extract_domain(url)
            return self._check_domain_limit(domain)
        return self._check_global_limit()

    def record_request(self, url: str) -> None:
        """Record that a request was made to the given URL."""
        now = time.time()
        if self.config.per_domain:
            domain = self._extract_domain(url)
            self._request_times[domain].append(now)
            self._cleanup(domain, self._request_times[domain])
        self._global_times.append(now)
        self._cleanup(None, self._global_times)

    def wait_time(self, url: str) -> float:
        """Get the time to wait before the next request is allowed."""
        if self.can_request(url):
            return 0.0
        if self.config.per_domain:
            domain = self._extract_domain(url)
            times = self._request_times.get(domain, [])
            if not times:
                return 0.0
            oldest = times[0]
            window_end = oldest + self.config.time_window
            return max(0.0, window_end - time.time())
        return 0.0

    def _check_domain_limit(self, domain: str) -> bool:
        """Check if domain-specific rate limit allows request."""
        times = self._request_times.get(domain, [])
        self._cleanup(domain, times)
        return len(times) < self.config.max_requests

    def _check_global_limit(self) -> bool:
        """Check if global rate limit allows request."""
        self._cleanup(None, self._global_times)
        return len(self._global_times) < self.config.max_requests

    def _cleanup(self, domain: Optional[str], times: List[float]) -> None:
        """Remove expired timestamps."""
        cutoff = time.time() - self.config.time_window
        while times and times[0] < cutoff:
            times.pop(0)

    @staticmethod
    def _extract_domain(url: str) -> str:
        """Extract domain from URL."""
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.hostname or url
        except Exception:
            return url

    def get_stats(self) -> Dict[str, int]:
        """Get current rate limit statistics."""
        return {
            "domains_tracked": len(self._request_times),
            "global_requests": len(self._global_times),
        }

    def reset(self) -> None:
        """Reset all rate limit tracking."""
        self._request_times.clear()
        self._global_times.clear()
