"""Caching layer for robots.txt parsing results."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


@dataclass
class RobotsCacheEntry:
    """Cached robots.txt parsing result."""

    domain: str
    allowed: dict[str, bool] = field(default_factory=dict)
    disallowed: dict[str, bool] = field(default_factory=dict)
    crawl_delay: Optional[float] = None
    sitemap_urls: list[str] = field(default_factory=list)
    fetched_at: float = field(default_factory=time.time)
    raw_content: str = ""

    def is_expired(self, ttl: float) -> bool:
        return (time.time() - self.fetched_at) > ttl

    def allows_agent(self, user_agent: str) -> bool:
        if user_agent in self.allowed:
            return True
        if user_agent in self.disallowed:
            return False
        return True  # Default allow


class RobotsCache:
    """Thread-safe cache for robots.txt results."""

    def __init__(self, ttl: float = 3600, max_entries: int = 1000):
        self._cache: dict[str, RobotsCacheEntry] = {}
        self._ttl = ttl
        self._max_entries = max_entries

    def get(self, domain: str) -> Optional[RobotsCacheEntry]:
        entry = self._cache.get(domain)
        if entry is None:
            return None
        if entry.is_expired(self._ttl):
            del self._cache[domain]
            logger.debug(f"Cache expired for {domain}")
            return None
        return entry

    def put(self, entry: RobotsCacheEntry) -> None:
        if len(self._cache) >= self._max_entries:
            self._evict_oldest()
        self._cache[entry.domain] = entry

    def invalidate(self, domain: str) -> bool:
        if domain in self._cache:
            del self._cache[domain]
            return True
        return False

    def invalidate_all(self) -> None:
        self._cache.clear()

    def _evict_oldest(self) -> None:
        if not self._cache:
            return
        oldest_domain = min(self._cache, key=lambda d: self._cache[d].fetched_at)
        del self._cache[oldest_domain]
        logger.debug(f"Evicted oldest cache entry: {oldest_domain}")

    @property
    def size(self) -> int:
        return len(self._cache)

    @property
    def domains(self) -> list[str]:
        return list(self._cache.keys())

    def get_stats(self) -> dict:
        return {
            "size": self.size,
            "ttl": self._ttl,
            "max_entries": self._max_entries,
            "domains": self.domains,
        }
