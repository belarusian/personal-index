"""
Cache management for personal-index.

Provides an in-memory and file-based cache for crawled pages
to avoid redundant requests and speed up repeated crawls.
"""

import hashlib
import json
import time
import os
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    """A single cache entry."""
    url: str
    content: str
    content_type: str = "text/html"
    status_code: int = 200
    cached_at: float = 0.0
    expires_at: float = 0.0
    etag: str = ""
    last_modified: str = ""

    def is_expired(self) -> bool:
        """Check if the cache entry has expired."""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


class Cache:
    """Cache for crawled pages."""

    def __init__(
        self,
        cache_dir: Optional[str] = None,
        ttl: int = 3600,  # Default TTL: 1 hour
        max_size: int = 1000,  # Max entries
    ):
        self.ttl = ttl
        self.max_size = max_size
        self._memory_cache: dict[str, CacheEntry] = {}
        self._cache_dir = cache_dir
        self._hits = 0
        self._misses = 0

        if self._cache_dir is None:
            self._cache_dir = str(Path.home() / ".cache" / "personal-index")

        Path(self._cache_dir).mkdir(parents=True, exist_ok=True)
        self._load_from_disk()

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        if total == 0:
            return 0.0
        return self._hits / total

    def _url_to_key(self, url: str) -> str:
        """Convert URL to cache key."""
        return hashlib.md5(url.encode()).hexdigest()

    def _get_cache_file(self, key: str) -> str:
        """Get the cache file path for a key."""
        return os.path.join(self._cache_dir, f"{key}.json")

    def get(self, url: str) -> Optional[CacheEntry]:
        """Get a cached entry for a URL."""
        key = self._url_to_key(url)

        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            if not entry.is_expired():
                self._hits += 1
                return entry
            else:
                del self._memory_cache[key]

        # Check disk cache
        cache_file = self._get_cache_file(key)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                entry = CacheEntry.from_dict(data)
                if not entry.is_expired():
                    self._memory_cache[key] = entry
                    self._hits += 1
                    return entry
                else:
                    os.remove(cache_file)
            except (json.JSONDecodeError, KeyError, OSError):
                pass

        self._misses += 1
        return None

    def put(self, url: str, content: str, content_type: str = "text/html",
            status_code: int = 200, etag: str = "", last_modified: str = "") -> None:
        """Store a page in the cache."""
        key = self._url_to_key(url)
        now = time.time()

        entry = CacheEntry(
            url=url,
            content=content,
            content_type=content_type,
            status_code=status_code,
            cached_at=now,
            expires_at=now + self.ttl,
            etag=etag,
            last_modified=last_modified,
        )

        # Evict old entries if at capacity
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()

        self._memory_cache[key] = entry
        self._save_to_disk(key, entry)

    def invalidate(self, url: str) -> bool:
        """Invalidate a cache entry."""
        key = self._url_to_key(url)

        if key in self._memory_cache:
            del self._memory_cache[key]

        cache_file = self._get_cache_file(key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
            return True
        return key in self._memory_cache

    def clear(self) -> None:
        """Clear all cache entries."""
        self._memory_cache.clear()
        self._hits = 0
        self._misses = 0

        # Remove all cache files
        cache_dir = Path(self._cache_dir)
        if cache_dir.exists():
            for f in cache_dir.glob("*.json"):
                f.unlink()

    def stats(self) -> dict:
        """Get cache statistics."""
        return {
            "memory_entries": len(self._memory_cache),
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": self.hit_rate,
            "ttl": self.ttl,
            "max_size": self.max_size,
        }

    def _evict_oldest(self) -> None:
        """Evict the oldest cache entry."""
        if not self._memory_cache:
            return
        oldest_key = min(self._memory_cache, key=lambda k: self._memory_cache[k].cached_at)
        cache_file = self._get_cache_file(oldest_key)
        if os.path.exists(cache_file):
            os.remove(cache_file)
        del self._memory_cache[oldest_key]

    def _save_to_disk(self, key: str, entry: CacheEntry) -> None:
        """Save a cache entry to disk."""
        cache_file = self._get_cache_file(key)
        try:
            with open(cache_file, "w") as f:
                json.dump(entry.to_dict(), f)
        except OSError:
            pass

    def _load_from_disk(self) -> None:
        """Load cache entries from disk."""
        cache_dir = Path(self._cache_dir)
        if not cache_dir.exists():
            return
        for f in cache_dir.glob("*.json"):
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                entry = CacheEntry.from_dict(data)
                if not entry.is_expired():
                    key = self._url_to_key(entry.url)
                    self._memory_cache[key] = entry
            except (json.JSONDecodeError, KeyError):
                f.unlink()
