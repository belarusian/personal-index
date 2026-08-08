"""HTTP response cache for personal-index."""

from __future__ import annotations

import json
import os
import time
import hashlib
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional


@dataclass
class CacheEntry:
    """A single cached HTTP response."""
    url: str
    content: str = ""
    cached_at: float = field(default_factory=time.time)
    expires_at: float = 0  # 0 means no expiry
    content_type: str = ""
    status_code: int = 200
    etag: str = ""

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        if self.expires_at == 0:
            return False
        return time.time() > self.expires_at

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**{k: v for k, v in data.items()
                      if k in cls.__dataclass_fields__})


class Cache:
    """In-memory and file-backed HTTP response cache."""

    def __init__(
        self,
        cache_dir: str = ".cache",
        ttl: int = 3600,
        max_size: int = 1000,
    ):
        self.cache_dir = Path(cache_dir)
        self.ttl = ttl
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        self._memory_cache: dict[str, CacheEntry] = {}
        self._load_from_disk()

    def _url_to_key(self, url: str) -> str:
        """Convert URL to a safe filename key."""
        return hashlib.sha256(url.encode()).hexdigest()

    def _entry_path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def _load_from_disk(self):
        """Load cache entries from disk."""
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        for f in self.cache_dir.glob("*.json"):
            try:
                with open(f, "r") as fh:
                    data = json.load(fh)
                entry = CacheEntry.from_dict(data)
                self._memory_cache[data["url"]] = entry
            except (json.JSONDecodeError, KeyError):
                pass

    def put(
        self,
        url: str,
        content: str,
        content_type: str = "",
        status_code: int = 200,
        etag: str = "",
    ):
        """Store a response in the cache."""
        now = time.time()
        entry = CacheEntry(
            url=url,
            content=content,
            cached_at=now,
            expires_at=now + self.ttl if self.ttl > 0 else 0,
            content_type=content_type,
            status_code=status_code,
            etag=etag,
        )
        # Evict oldest if at max size
        if len(self._memory_cache) >= self.max_size:
            self._evict_oldest()
        self._memory_cache[url] = entry
        self._save_entry(entry)

    def get(self, url: str) -> Optional[CacheEntry]:
        """Retrieve a cached response."""
        if url in self._memory_cache:
            entry = self._memory_cache[url]
            if entry.is_expired():
                self.invalidate(url)
                self.misses += 1
                return None
            self.hits += 1
            return entry
        self.misses += 1
        return None

    def invalidate(self, url: str):
        """Remove a specific entry from the cache."""
        if url in self._memory_cache:
            del self._memory_cache[url]
            key = self._url_to_key(url)
            path = self._entry_path(key)
            if path.exists():
                path.unlink()

    def clear(self):
        """Clear all cache entries."""
        self.hits = 0
        self.misses = 0
        for f in self.cache_dir.glob("*.json"):
            f.unlink()
        self._memory_cache.clear()

    def _evict_oldest(self):
        """Evict the oldest cache entry."""
        if not self._memory_cache:
            return
        oldest_url = min(
            self._memory_cache,
            key=lambda u: self._memory_cache[u].cached_at,
        )
        self.invalidate(oldest_url)

    def _save_entry(self, entry: CacheEntry):
        """Persist a single entry to disk."""
        key = self._url_to_key(entry.url)
        path = self._entry_path(key)
        with open(path, "w") as fh:
            json.dump(entry.to_dict(), fh)

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate."""
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return self.hits / total

    def stats(self) -> dict:
        """Return cache statistics."""
        return {
            "memory_entries": len(self._memory_cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hit_rate,
            "ttl": self.ttl,
            "max_size": self.max_size,
        }
