"""Caching utilities with LRU and TTL strategies."""

from __future__ import annotations

import time
import threading
from collections import OrderedDict
from typing import Any, TypeVar

T = TypeVar("T")


class LRUCache:
    """Thread-safe LRU cache with optional size limit.

    Uses OrderedDict for O(1) get/put operations.
    """

    def __init__(self, max_size: int = 128) -> None:
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key, moving it to end (most recently used).

        Args:
            key: Cache key.
            default: Value to return if key not found.

        Returns:
            Cached value or default.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default
            self._cache.move_to_end(key)
            self._hits += 1
            return self._cache[key]

    def put(self, key: str, value: Any) -> None:
        """Store value in cache, evicting LRU item if at capacity.

        Args:
            key: Cache key.
            value: Value to store.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            while len(self._cache) > self.max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Remove key from cache.

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
        """Remove all items from cache."""
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        return key in self._cache

    def __len__(self) -> int:
        return len(self._cache)

    @property
    def size(self) -> int:
        """Current number of items in cache."""
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction (0.0 to 1.0)."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": self.size,
            "max_size": self.max_size,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


class TTLCache:
    """Cache with time-to-live expiration.

    Each entry expires after the specified TTL in seconds.
    """

    def __init__(self, ttl: float = 300.0, max_size: int = 1000) -> None:
        """Initialize TTL cache.

        Args:
            ttl: Time-to-live in seconds for each entry.
            max_size: Maximum number of entries before eviction.
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get value if not expired.

        Args:
            key: Cache key.
            default: Value to return if key not found or expired.

        Returns:
            Cached value or default.
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return default
            value, expiry = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                self._misses += 1
                return default
            self._hits += 1
            return value

    def put(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Store value with expiration.

        Args:
            key: Cache key.
            value: Value to store.
            ttl: Optional per-entry TTL override.
        """
        with self._lock:
            effective_ttl = ttl if ttl is not None else self.ttl
            expiry = time.monotonic() + effective_ttl
            self._cache[key] = (value, expiry)
            # Evict expired entries if over capacity
            if len(self._cache) > self.max_size:
                self._evict_expired()
                if len(self._cache) > self.max_size:
                    # Remove oldest entries
                    oldest_keys = sorted(
                        self._cache.keys(),
                        key=lambda k: self._cache[k][1],
                    )[: len(self._cache) - self.max_size]
                    for k in oldest_keys:
                        del self._cache[k]

    def delete(self, key: str) -> bool:
        """Remove key from cache.

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
        """Remove all items from cache."""
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        with self._lock:
            if key not in self._cache:
                return False
            _, expiry = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                return False
            return True

    def __len__(self) -> int:
        return len(self._cache)

    @property
    def size(self) -> int:
        """Current number of non-expired items."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(self._cache)

    def _evict_expired(self) -> int:
        """Remove expired entries. Returns count of evicted items."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction."""
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics."""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "ttl": self.ttl,
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
        }


class CacheDecorator:
    """Decorator that wraps a function with caching.

    Usage:
        @CacheDecorator(lru_size=100)
        def expensive_func(x):
            return x * x
    """

    def __init__(self, lru_size: int = 128, ttl: float | None = None) -> None:
        self.lru_size = lru_size
        self.ttl = ttl

    def __call__(self, func):
        if self.ttl is not None:
            cache = TTLCache(ttl=self.ttl, max_size=self.lru_size)
        else:
            cache = LRUCache(max_size=self.lru_size)

        def wrapper(*args, **kwargs):
            """Cache wrapper that stores and retrieves function results."""
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            result = cache.get(key)
            if result is not None:
                return result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result

        wrapper.cache = cache
        wrapper.__wrapped__ = func
        return wrapper
