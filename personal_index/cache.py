"""Caching utilities with LRU and TTL strategies."""

from __future__ import annotations

import threading
import time
from collections import OrderedDict
from typing import Any, TypeVar

T = TypeVar("T")


class LRUCache:
    """Thread-safe LRU cache with optional size limit.

    Uses OrderedDict for O(1) get/put operations.
    """

    def __init__(self, max_size: int = 128) -> None:
        """Initialize an empty LRU cache.

        No guard path: always constructs.

        Returns ``None``. Side effects: sets ``self.max_size = max_size``,
        an empty ``self._cache`` (OrderedDict), a fresh ``self._lock``, and
        ``self._hits = self._misses = 0``.
        """
        self.max_size = max_size
        self._cache: OrderedDict[str, Any] = OrderedDict()
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get value by key, moving it to end (most recently used).

        Guard path: if ``key`` is not in the cache, returns ``default``
        unchanged and increments ``self._misses`` by 1 (no move, no hit).

        For a present ``key`` the returned value is ``self._cache[key]``;
        the entry is moved to the most-recently-used end and
        ``self._hits`` is incremented by 1.

        Side effects: mutates the LRU order of ``self._cache`` on a hit and
        increments exactly one of ``self._hits`` / ``self._misses``.
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

        No guard path: always stores.

        Returns ``None``. Side effects: sets ``self._cache[key] = value``;
        if ``key`` was already present it is first moved to the
        most-recently-used end; while ``len(self._cache) > max_size`` the
        least-recently-used entry (the front of the OrderedDict) is popped,
        so the cache never exceeds ``self.max_size`` entries. A negative
        ``max_size`` is clamped to 0 (matching the zero behaviour: evict to
        empty, never crash); ``max_size >= 0`` is unchanged.
        """
        with self._lock:
            if key in self._cache:
                self._cache.move_to_end(key)
            self._cache[key] = value
            max_size = max(0, self.max_size)
            while len(self._cache) > max_size:
                self._cache.popitem(last=False)

    def delete(self, key: str) -> bool:
        """Remove key from cache.

        Guard path: if ``key`` is not in the cache, returns ``False`` and
        leaves the cache unchanged.

        For a present ``key`` the returned value is ``True``.

        Side effects: on the normal path deletes ``self._cache[key]``; on
        the guard path no mutation occurs.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all items from cache.

        No guard path: always clears.

        Returns ``None``. Side effects: empties ``self._cache``; the
        ``self._hits`` / ``self._misses`` counters are left unchanged.
        """
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        """Report whether ``key`` is present in the cache.

        Guard path: if ``key`` is not in the cache, returns ``False``.

        For a present ``key`` the returned value is ``True``.

        No side effects.
        """
        return key in self._cache

    def __len__(self) -> int:
        """Return the number of entries currently stored.

        No guard path: always computes.

        Returns ``len(self._cache)``. No side effects.
        """
        return len(self._cache)

    @property
    def size(self) -> int:
        """Current number of items in cache.

        No guard path: always computes.

        Returns ``len(self._cache)``. No side effects.
        """
        return len(self._cache)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction (0.0 to 1.0).

        Guard path: if ``self._hits + self._misses == 0`` (no lookups yet),
        returns ``0.0``.

        Otherwise the returned value is ``self._hits / (self._hits +
        self._misses)``.

        No side effects.
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        No guard path: always computes.

        Returns a dict with exactly these keys: ``"size"`` (``self.size`` =
        ``len(self._cache)``), ``"max_size"`` (``self.max_size``), ``"hits"``
        (``self._hits``), ``"misses"`` (``self._misses``) and ``"hit_rate"``
        (``self.hit_rate``). No side effects.
        """
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
        """Initialize an empty TTL cache.

        No guard path: always constructs.

        Returns ``None``. Side effects: sets ``self.ttl = ttl``,
        ``self.max_size = max_size``, an empty ``self._cache`` (dict of
        ``key -> (value, expiry)``), a fresh ``self._lock``, and
        ``self._hits = self._misses = 0``.
        """
        self.ttl = ttl
        self.max_size = max_size
        self._cache: dict[str, tuple[Any, float]] = {}
        self._lock = threading.Lock()
        self._hits = 0
        self._misses = 0

    def get(self, key: str, default: Any = None) -> Any:
        """Get value if not expired.

        Guard path (two branches, both return ``default`` and increment
        ``self._misses`` by 1): (a) if ``key`` is not in the cache, returns
        ``default`` with no mutation; (b) if ``key`` is present but its
        stored expiry is in the past (``time.monotonic() > expiry``), the
        entry is deleted from ``self._cache`` and ``default`` is returned.

        For a present, non-expired ``key`` the returned value is the stored
        value; ``self._hits`` is incremented by 1.

        Side effects: on the expired branch deletes ``self._cache[key]``;
        every call increments exactly one of ``self._hits`` /
        ``self._misses``.
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

        No guard path: always stores.

        Returns ``None``. Side effects: sets ``self._cache[key] = (value,
        time.monotonic() + effective_ttl)`` where ``effective_ttl`` is
        ``ttl`` when ``ttl is not None`` else ``self.ttl``; if
        ``len(self._cache) > self.max_size`` it first removes every expired
        entry and, if still over capacity, deletes the entries with the
        earliest expiry until ``len(self._cache) <= self.max_size``.
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

        Guard path: if ``key`` is not in the cache, returns ``False`` and
        leaves the cache unchanged.

        For a present ``key`` the returned value is ``True``.

        Side effects: on the normal path deletes ``self._cache[key]``; on
        the guard path no mutation occurs.
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Remove all items from cache.

        No guard path: always clears.

        Returns ``None``. Side effects: empties ``self._cache``; the
        ``self._hits`` / ``self._misses`` counters are left unchanged.
        """
        with self._lock:
            self._cache.clear()

    def __contains__(self, key: str) -> bool:
        """Report whether ``key`` is present and not expired.

        Guard path (two branches, both return ``False``): (a) if ``key`` is
        not in the cache, returns ``False`` with no mutation; (b) if ``key``
        is present but its stored expiry is in the past
        (``time.monotonic() > expiry``), the entry is deleted from
        ``self._cache`` and ``False`` is returned.

        For a present, non-expired ``key`` the returned value is ``True``.

        Side effects: on the expired branch deletes ``self._cache[key]``.
        """
        with self._lock:
            if key not in self._cache:
                return False
            _, expiry = self._cache[key]
            if time.monotonic() > expiry:
                del self._cache[key]
                return False
            return True

    def __len__(self) -> int:
        """Return the number of entries currently stored.

        No guard path: always computes.

        Returns ``len(self._cache)`` (expired-but-not-yet-evicted entries
        are still counted). No side effects.
        """
        return len(self._cache)

    @property
    def size(self) -> int:
        """Current number of non-expired items.

        No guard path: always computes.

        Returns ``len(self._cache)`` after first deleting every entry whose
        stored expiry is in the past (``time.monotonic() > expiry``).

        Side effects: deletes all currently-expired entries from
        ``self._cache`` before measuring.
        """
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(self._cache)

    def _evict_expired(self) -> int:
        """Remove expired entries. Returns count of evicted items.

        No guard path: always computes (returns ``0`` when nothing is
        expired).

        Returns the number of entries whose stored expiry is in the past
        (``time.monotonic() > expiry``) that were removed.

        Side effects: deletes every currently-expired entry from
        ``self._cache``.
        """
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._cache.items() if now > exp]
        for k in expired:
            del self._cache[k]
        return len(expired)

    @property
    def hit_rate(self) -> float:
        """Cache hit rate as a fraction.

        Guard path: if ``self._hits + self._misses == 0`` (no lookups yet),
        returns ``0.0``.

        Otherwise the returned value is ``self._hits / (self._hits +
        self._misses)``.

        No side effects.
        """
        total = self._hits + self._misses
        return self._hits / total if total > 0 else 0.0

    def stats(self) -> dict[str, Any]:
        """Return cache statistics.

        No guard path: always computes.

        Returns a dict with exactly these keys: ``"size"`` (``len(self._cache)``),
        ``"max_size"`` (``self.max_size``), ``"ttl"`` (``self.ttl``),
        ``"hits"`` (``self._hits``), ``"misses"`` (``self._misses``) and
        ``"hit_rate"`` (``self.hit_rate``). No side effects.
        """
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
            return x * 2
    """

    def __init__(self, lru_size: int = 128, ttl: float | None = None) -> None:
        """Initialize the decorator.

        No guard path: always constructs.

        Returns ``None``. Side effects: sets ``self.lru_size = lru_size``
        and ``self.ttl = ttl``.
        """
        self.lru_size = lru_size
        self.ttl = ttl

    def __call__(self, func):
        """Wrap ``func`` in a caching wrapper.

        No guard path: always wraps.

        Returns a ``wrapper`` callable. Side effects: constructs a backing
        cache — a ``TTLCache(ttl=self.ttl, max_size=self.lru_size)`` when
        ``self.ttl is not None`` else an ``LRUCache(max_size=self.lru_size)``
        — and attaches it as ``wrapper.cache`` and the original as
        ``wrapper.__wrapped__``.

        Calling ``wrapper(*args, **kwargs)``: the cache key is the string
        ``f"{func.__name__}:{args}:{sorted(kwargs.items())}"``; on a cache
        hit the stored result is returned without calling ``func``; on a
        miss ``func(*args, **kwargs)`` is called, its result stored under
        the key, and returned.
        """
        if self.ttl is not None:
            cache = TTLCache(ttl=self.ttl, max_size=self.lru_size)
        else:
            cache = LRUCache(max_size=self.lru_size)

        _missing = object()

        def wrapper(*args, **kwargs):
            """Cache wrapper that stores and retrieves function results."""
            key = f"{func.__name__}:{args}:{sorted(kwargs.items())}"
            result = cache.get(key, default=_missing)
            if result is not _missing:
                return result
            result = func(*args, **kwargs)
            cache.put(key, result)
            return result

        wrapper.cache = cache
        wrapper.__wrapped__ = func
        return wrapper
