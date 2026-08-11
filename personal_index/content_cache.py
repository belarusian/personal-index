"""Content caching layer for personal-index.

Provides in-memory and file-based caching for content items,
search results, and computed scores to improve performance.
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class CacheEntry:
    """A single cache entry with metadata.

    Attributes:
        key: Cache key.
        value: Cached value.
        created_at: When the entry was created.
        expires_at: When the entry expires (None for no expiry).
        access_count: Number of times the entry was accessed.
        size_bytes: Approximate size in bytes.
    """

    key: str
    value: Any
    created_at: float
    expires_at: float | None = None
    access_count: int = 0
    size_bytes: int = 0


@dataclass
class CacheStats:
    """Statistics about cache performance.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        evictions: Number of entries evicted.
        size: Current number of entries.
        hit_rate: Cache hit rate (0.0-1.0).
    """

    hits: int = 0
    misses: int = 0
    evictions: int = 0
    size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate hit rate."""
        total = self.hits + self.misses
        return self.hits / total if total > 0 else 0.0


class MemoryCache:
    """In-memory LRU cache with TTL support.

    Provides fast caching with configurable maximum size
    and time-to-live for entries.
    """

    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: float | None = None,
    ) -> None:
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._store: OrderedDict[str, CacheEntry] = OrderedDict()
        self._stats = CacheStats()

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the cache.

        Args:
            key: Cache key.
            default: Default value if key not found.

        Returns:
            Cached value or default.
        """
        entry = self._store.get(key)
        if entry is None:
            self._stats.misses += 1
            return default

        # Check expiry
        if entry.expires_at and time.time() > entry.expires_at:
            del self._store[key]
            self._stats.misses += 1
            return default

        # Move to end (most recently used)
        self._store.move_to_end(key)
        entry.access_count += 1
        self._stats.hits += 1
        return entry.value

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the cache.

        Args:
            key: Cache key.
            value: Value to cache.
            ttl: Time-to-live in seconds (None uses default).
        """
        if key in self._store:
            del self._store[key]

        # Evict if at capacity
        while len(self._store) >= self.max_size:
            self._evict_lru()

        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        entry = CacheEntry(
            key=key,
            value=value,
            created_at=time.time(),
            expires_at=expires_at,
            size_bytes=self._estimate_size(value),
        )
        self._store[key] = entry

    def delete(self, key: str) -> bool:
        """Delete a key from the cache.

        Args:
            key: Cache key to delete.

        Returns:
            True if the key was found and deleted.
        """
        if key in self._store:
            del self._store[key]
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._store.clear()

    def has(self, key: str) -> bool:
        """Check if a key exists in the cache."""
        entry = self._store.get(key)
        if entry is None:
            return False
        if entry.expires_at and time.time() > entry.expires_at:
            del self._store[key]
            return False
        return True

    def keys(self) -> list[str]:
        """Get all non-expired keys."""
        expired = [
            k for k, v in self._store.items()
            if v.expires_at and time.time() > v.expires_at
        ]
        for k in expired:
            del self._store[k]
        return list(self._store.keys())

    def size(self) -> int:
        """Get current number of entries."""
        return len(self._store)

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        self._stats.size = len(self._store)
        return self._stats

    def _evict_lru(self) -> None:
        """Evict the least recently used entry."""
        if self._store:
            self._store.popitem(last=False)
            self._stats.evictions += 1

    def _estimate_size(self, value: Any) -> int:
        """Estimate the size of a value in bytes."""
        try:
            return len(json.dumps(value, default=str))
        except (TypeError, ValueError):
            return len(str(value))


class FileCache:
    """File-based cache for persisting cached data.

    Stores cache entries as JSON files on disk with
    automatic cleanup of expired entries.
    """

    def __init__(
        self,
        cache_dir: str | Path,
        default_ttl: float | None = 3600,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.default_ttl = default_ttl
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a value from the file cache."""
        filepath = self._get_filepath(key)
        if not filepath.exists():
            return default

        try:
            data = json.loads(filepath.read_text())
            if data.get("expires_at") and time.time() > data["expires_at"]:
                filepath.unlink()
                return default
            return data["value"]
        except (json.JSONDecodeError, KeyError):
            return default

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        """Set a value in the file cache."""
        filepath = self._get_filepath(key)
        effective_ttl = ttl if ttl is not None else self.default_ttl
        expires_at = time.time() + effective_ttl if effective_ttl else None

        data = {
            "value": value,
            "created_at": time.time(),
            "expires_at": expires_at,
        }
        filepath.write_text(json.dumps(data, default=str), encoding="utf-8")

    def delete(self, key: str) -> bool:
        """Delete a key from the file cache."""
        filepath = self._get_filepath(key)
        if filepath.exists():
            filepath.unlink()
            return True
        return False

    def clear(self) -> None:
        """Clear all entries from the file cache."""
        for filepath in self.cache_dir.glob("*.json"):
            filepath.unlink()

    def cleanup_expired(self) -> int:
        """Remove expired entries. Returns count of removed entries."""
        removed = 0
        for filepath in self.cache_dir.glob("*.json"):
            try:
                data = json.loads(filepath.read_text())
                if data.get("expires_at") and time.time() > data["expires_at"]:
                    filepath.unlink()
                    removed += 1
            except (json.JSONDecodeError, KeyError):
                filepath.unlink()
                removed += 1
        return removed

    def _get_filepath(self, key: str) -> Path:
        """Get the file path for a cache key."""
        hash_key = hashlib.sha256(key.encode()).hexdigest()[:16]
        return self.cache_dir / f"{hash_key}.json"
