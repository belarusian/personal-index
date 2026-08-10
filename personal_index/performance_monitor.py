"""Performance monitoring and metrics collection."""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class MetricSample:
    """A single metric data point."""

    name: str
    value: float
    timestamp: float = field(default_factory=time.time)
    tags: dict = field(default_factory=dict)


@dataclass
class MetricStats:
    """Aggregated statistics for a metric."""

    name: str
    count: int = 0
    total: float = 0.0
    min_val: float = float("inf")
    max_val: float = float("-inf")
    sum_sq: float = 0.0

    @property
    def mean(self) -> float:
        """Arithmetic mean of recorded values."""
        return self.total / self.count if self.count > 0 else 0.0

    @property
    def stddev(self) -> float:
        """Population standard deviation of recorded values."""
        if self.count < 2:
            return 0.0
        # Use population variance formula: E[X^2] - (E[X])^2
        # But need to handle the case where min_val/max_val weren't set
        # Use sum_sq for E[X^2] calculation
        mean = self.mean
        variance = (self.sum_sq / self.count) - (mean ** 2)
        # Clamp to avoid floating point issues
        return max(0.0, variance) ** 0.5

    @property
    def p50(self) -> float:
        """Approximate 50th percentile (mean)."""
        return self.mean  # Approximation

    @property
    def p95(self) -> float:
        """Approximate 95th percentile (mean * 1.5)."""
        return self.mean * 1.5  # Approximation

    @property
    def p99(self) -> float:
        """Approximate 99th percentile (mean * 2.0)."""
        return self.mean * 2.0  # Approximation


class PerformanceMonitor:
    """Monitors and tracks performance metrics."""

    def __init__(self, window_size: int = 1000):
        self._samples: dict[str, list[MetricSample]] = defaultdict(list)
        self._stats: dict[str, MetricStats] = {}
        self._window_size = window_size
        self._timers: dict[str, float] = {}

    def record(self, name: str, value: float, tags: Optional[dict] = None) -> None:
        """Record a metric value."""
        sample = MetricSample(name=name, value=value, tags=tags or {})
        samples = self._samples[name]
        samples.append(sample)
        if len(samples) > self._window_size:
            self._samples[name] = samples[-self._window_size :]

        if name not in self._stats:
            self._stats[name] = MetricStats(name=name)
        stats = self._stats[name]
        stats.count += 1
        stats.total += value
        stats.min_val = min(stats.min_val, value)
        stats.max_val = max(stats.max_val, value)
        stats.sum_sq += value * value

    def timer(self, name: str) -> TimerContext:
        """Create a timer context manager."""
        return TimerContext(self, name)

    def get_stats(self, name: str) -> Optional[MetricStats]:
        """Get aggregated stats for a metric."""
        return self._stats.get(name)

    def get_all_stats(self) -> dict[str, MetricStats]:
        """Get stats for all tracked metrics."""
        return dict(self._stats)

    def reset(self) -> None:
        """Reset all metrics."""
        self._samples.clear()
        self._stats.clear()
        self._timers.clear()

    def get_recent_samples(self, name: str, count: int = 10) -> list[MetricSample]:
        """Get recent samples for a metric."""
        return self._samples.get(name, [])[-count:]


class TimerContext:
    """Context manager for timing operations."""

    def __init__(self, monitor: PerformanceMonitor, name: str):
        self._monitor = monitor
        self._name = name
        self._start: Optional[float] = None

    def __enter__(self) -> TimerContext:
        self._start = time.time()
        return self

    def __exit__(self, *args) -> None:
        if self._start is not None:
            elapsed = time.time() - self._start
            self._monitor.record(self._name, elapsed)

    @property
    def elapsed(self) -> float:
        """Seconds elapsed since the timer started."""
        if self._start is None:
            return 0.0
        return time.time() - self._start
