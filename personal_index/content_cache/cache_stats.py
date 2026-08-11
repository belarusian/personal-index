"""Cache statistics tracking."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CacheStats:
    """Statistics about cache performance.

    Attributes:
        hits: Number of cache hits.
        misses: Number of cache misses.
        sets: Number of cache sets.
        evictions: Number of evictions.
        current_size: Current number of entries.
    """

    hits: int = 0
    misses: int = 0
    sets: int = 0
    evictions: int = 0
    current_size: int = 0

    @property
    def hit_rate(self) -> float:
        """Calculate cache hit rate.

        Returns:
            Hit rate as a float between 0.0 and 1.0.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.hits / total, 10)

    @property
    def miss_rate(self) -> float:
        """Calculate cache miss rate.

        Returns:
            Miss rate as a float between 0.0 and 1.0.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.misses / total, 10)

    def reset(self) -> None:
        """Reset all statistics."""
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0
        self.current_size = 0
