"""Content cache for expensive operations in the personal index.

Provides caching with TTL, size limits, and per-operation tracking
for expensive content processing operations.
"""

from __future__ import annotations

import hashlib
import time
import threading
import logging
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Optional

logger = logging.getLogger(__name__)


@dataclass
class CacheEntry:
    """A single cached entry with metadata."""
    value: Any
    created_at: float = field(default_factory=time.monotonic)
    ttl: float = 3600.0
    access_count: int = 0
    last_accessed: float = field(default_factory=time.monotonic)
    operation: str = ""

    @property
    def is_expired(self) -> bool:
        return time.monotonic() > (self.created_at + self.ttl)

    @property
    def age(self) -> float:
        return time.monotonic() - self.created_at


class ContentCache:
    """Cache for expensive content operations.

    Supports TTL-based expiration, size limits, and per-operation
    statistics tracking.
    """

    def __init__(self, max_size: int = 1000, default_ttl: float = 3600.0) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0
        self._evictions = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get a cached value by key.

        Args:
            key: Cache key.
            default: Default value if key not found or expired.

        Returns:
            Cached value or default.
        """
        with self._lock:
            entry = self._cache.get(key)
            if entry is None or entry.is_expired:
                if entry is not None:
                    del self._cache[key]
                self._misses += 1
                return default
            self._cache.move_to_end(key)
            entry.access_count += 1
            entry.last_accessed = time.monotonic()
            self._hits += 1
            return entry.value

    def put(self, key: str, value: Any, ttl: float | None = None, operation: str = "") -> None:
        """Store a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (uses default if not specified).
            operation: Name of the operation being cached.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = CacheEntry(
                value=value,
                ttl=ttl if ttl is not None else self.default_ttl,
                operation=operation,
            )
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)
                self._evictions += 1

    def delete(self, key: str) -> bool:
        """Remove a key from the cache.

        Args:
            key: Cache key to remove.

        Returns:
            True if key was found and removed.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all entries from the cache."""
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        with self._lock:
            entry = self._cache.get(key)
            if entry and not entry.is_expired:
                return True
            if entry and entry.is_expired:
                del self._cache[key]
            return False

    def __len__(self) -> int:
        with self._lock:
            return len(self._cache)

    @property
    def size(self) -> int:
        """Current number of non-expired entries."""
        with self._lock:
            expired_keys = [k for k, v in self._cache.items() if v.is_expired]
            for k in expired_keys:
                del self._cache[k]
            return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        with self._lock:
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "default_ttl": self.default_ttl,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": self.hit_rate,
            }

    def get_or_compute(self, key: str, compute_fn, ttl: float | None = None, operation: str = "") -> Any:
        """Get cached value or compute and cache it.

        Args:
            key: Cache key.
            compute_fn: Callable to compute value if not cached.
            ttl: Optional TTL override.
            operation: Name of the operation.

        Returns:
            Cached or computed value.
        """
        value = self.get(key)
        if value is not None:
            return value
        value = compute_fn()
        self.put(key, value, ttl=ttl, operation=operation)
        return value

    def generate_key(self, operation: str, *args, **kwargs) -> str:
        """Generate a cache key from operation name and arguments.

        Args:
            operation: Name of the operation.
            *args: Positional arguments.
            **kwargs: Keyword arguments.

        Returns:
            Hash-based cache key string.
        """
        raw = f"{operation}:{args}:{sorted(kwargs.items())}"
        return hashlib.md5(raw.encode()).hexdigest()
