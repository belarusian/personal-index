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
        """Calculate the cache hit rate.

        The hit rate is the fraction of lookups that were cache hits:
        hits / (hits + misses). When the total number of lookups
        (hits + misses) is ZERO, the rate is defined as 0.0 (the
        zero-total guard) rather than raising ZeroDivisionError.
        Otherwise the result is rounded to 10 decimal places
        (round(hits / total, 10)). The returned value is always a
        float in the range [0.0, 1.0], and whenever the total is
        non-zero, hit_rate + miss_rate == 1.0.

        Returns:
            Hit rate as a float between 0.0 and 1.0.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.hits / total, 10)

    @property
    def miss_rate(self) -> float:
        """Calculate the cache miss rate.

        The miss rate is the fraction of lookups that were cache
        misses: misses / (hits + misses). When the total number of
        lookups (hits + misses) is ZERO, the rate is defined as 0.0
        (the zero-total guard) rather than raising ZeroDivisionError.
        Otherwise the result is rounded to 10 decimal places
        (round(misses / total, 10)). The returned value is always a
        float in the range [0.0, 1.0], and whenever the total is
        non-zero, hit_rate + miss_rate == 1.0.

        Returns:
            Miss rate as a float between 0.0 and 1.0.
        """
        total = self.hits + self.misses
        if total == 0:
            return 0.0
        return round(self.misses / total, 10)

    def reset(self) -> None:
        """Reset all statistics to their initial zero values.

        Zeroes every tracked counter: hits, misses, sets, evictions,
        and current_size. After a call to reset(), hit_rate and
        miss_rate both return 0.0 (the zero-total guard).
        """
        self.hits = 0
        self.misses = 0
        self.sets = 0
        self.evictions = 0
        self.current_size = 0
