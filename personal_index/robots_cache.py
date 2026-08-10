"""Caching layer for robots.txt parsing results."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class RobotsCacheEntry:
    """Cached robots.txt parsing result."""

    domain: str
    allowed: dict[str, bool] = field(default_factory=dict)
    disallowed: dict[str, bool] = field(default_factory=dict)
    crawl_delay: float | None = None
    sitemap_urls: list[str] = field(default_factory=list)
    fetched_at: float = field(default_factory=time.time)
    raw_content: str = ""

    def is_expired(self, ttl: float) -> bool:
        """Check if this cache entry has exceeded its TTL.

        Args:
            ttl: Time-to-live in seconds.

        Returns:
            True if the entry is expired.
        """
        return (time.time() - self.fetched_at) > ttl

    def allows_agent(self, user_agent: str) -> bool:
        """Check if a user agent is allowed based on cached robots.txt rules.

        Args:
            user_agent: The user agent string to check.

        Returns:
            True if allowed (default allow if not explicitly listed).
        """
        if user_agent in self.allowed:
            return True
        return user_agent not in self.disallowed


class RobotsCache:
    """Thread-safe cache for robots.txt results."""

    def __init__(self, ttl: float = 3600, max_entries: int = 1000):
        self._cache: dict[str, RobotsCacheEntry] = {}
        self._ttl = ttl
        self._max_entries = max_entries

    def get(self, domain: str) -> RobotsCacheEntry | None:
        """Get a cached robots.txt entry for a domain.

        Args:
            domain: The domain to look up.

        Returns:
            The cache entry, or None if not found or expired.
        """
        entry = self._cache.get(domain)
        if entry is None:
            return None
        if entry.is_expired(self._ttl):
            del self._cache[domain]
            logger.debug(f"Cache expired for {domain}")
            return None
        return entry

    def put(self, entry: RobotsCacheEntry) -> None:
        """Store a robots.txt cache entry.

        Args:
            entry: The cache entry to store.
        """
        if len(self._cache) >= self._max_entries:
            self._evict_oldest()
        self._cache[entry.domain] = entry

    def invalidate(self, domain: str) -> bool:
        """Remove a domain from the cache.

        Args:
            domain: The domain to invalidate.

        Returns:
            True if the entry was found and removed.
        """
        if domain in self._cache:
            del self._cache[domain]
            return True
        return False

    def invalidate_all(self) -> None:
        """Clear all cached entries."""
        self._cache.clear()

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_domain = min(self._cache, key=lambda d: self._cache[d].fetched_at)
        del self._cache[oldest_domain]
        logger.debug(f"Evicted oldest cache entry: {oldest_domain}")

    @property
    def size(self) -> int:
        """Number of entries in the cache."""
        return len(self._cache)

    @property
    def domains(self) -> list[str]:
        """List of all cached domains."""
        return list(self._cache.keys())

    def get_stats(self) -> dict:
        """Get cache statistics.

        Returns:
            Dictionary with cache size, TTL, max entries, and domains.
        """
        return {
            "size": self.size,
            "ttl": self._ttl,
            "max_entries": self._max_entries,
            "domains": self.domains,
        }
