"""Cache eviction policies."""

from __future__ import annotations

from enum import Enum
from typing import Any


class EvictionPolicy(Enum):
    """Cache eviction policy types."""

    LRU = "lru"  # Least Recently Used
    LFU = "lfu"  # Least Frequently Used
    FIFO = "fifo"  # First In First Out
    TTL = "ttl"  # Time To Live


@dataclass
class CachePolicy:
    """Configuration for cache behavior.

    Attributes:
        eviction_policy: Policy for evicting entries.
        max_size: Maximum cache size.
        default_ttl: Default TTL in seconds.
        enable_stats: Whether to track cache statistics.
    """

    eviction_policy: EvictionPolicy = EvictionPolicy.LRU
    max_size: int = 1000
    default_ttl: float | None = 3600.0
    enable_stats: bool = True
