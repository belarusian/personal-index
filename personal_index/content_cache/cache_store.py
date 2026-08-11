"""In-memory cache store with TTL support."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any, TypeVar

T = TypeVar("T")


@dataclass
class _CacheEntry:
    """Internal cache entry with metadata."""

    value: Any
    created_at: float
    ttl: float | None
    access_count: int = 0
    last_accessed: float = 0.0

    @property
    def is_expired(self) -> bool:
        if self.ttl is None:
            return False
        return time.time() > self.created_at + self.ttl


@dataclass
class CacheStore:
    """Thread-safe in-memory cache store.

    Attributes:
        max_size: Maximum number of entries.
        default_ttl: Default TTL in seconds (None for no expiry).
    """

    max_size: int = 1000
    default_ttl: float | None = 3600.0
    _entries: dict[str, _CacheEntry] = field(default_factory=dict, repr=False)

    def get(self, key: str, default: T | None = None) -> T | None:
        """Get a value from the cache.

        Args:
            key: Cache key.
            default: Default value if key not found.

        Returns:
            Cached value or default.
        """
        entry = self._entries.get(key)
        if entry is None or entry.is_expired:
            if entry:
                del self._entries[key]
            return default

        entry.access_count += 1
        entry.last_accessed = time.time()
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds.
        """
        if ttl is None:
            ttl = self.default_ttl

        now = time.time()
        self._entries[key] = _CacheEntry(
            value=value,
            created_at=now,
            ttl=ttl,
            last_accessed=now,
        )

        # Evict if over max size
        if len(self._entries) > self.max_size:
            self._evict_lru()

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key.

        Returns:
            True if key was found and deleted.
        """
        if key in self._entries:
            del self._entries[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all cache entries."""
        self._entries.clear()

    def has(self, key: str) -> bool:
        """Check if a key exists and is not expired.

        Args:
            key: Cache key.

        Returns:
            True if key exists and is valid.
        """
        entry = self._entries.get(key)
        if entry is None or entry.is_expired:
            if entry:
                del self._entries[key]
            return False
        return True

    def keys(self) -> list[str]:
        """Get all non-expired cache keys.

        Returns:
            List of valid cache keys.
        """
        return [k for k, v in self._entries.items() if not v.is_expired]

    def size(self) -> int:
        """Get the number of valid entries.

        Returns:
            Number of non-expired entries.
        """
        return sum(1 for e in self._entries.values() if not e.is_expired)

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if not self._entries:
            return
        lru_key = min(self._entries, key=lambda k: self._entries[k].last_accessed)
        del self._entries[lru_key]
