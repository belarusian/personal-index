"""System metrics collection and reporting."""

from __future__ import annotations

import logging
import os
import platform
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class SystemMetrics:
    """Snapshot of system metrics."""

    timestamp: float = field(default_factory=time.time)
    cpu_percent: float = 0.0
    memory_used_mb: float = 0.0
    memory_total_mb: float = 0.0
    disk_used_mb: float = 0.0
    disk_total_mb: float = 0.0
    python_version: str = field(default_factory=platform.python_version)
    platform_info: str = field(default_factory=platform.platform)
    process_pid: int = field(default_factory=os.getpid)
    uptime_seconds: float = 0.0

    def to_dict(self) -> dict:
        """Serialize system metrics to a dictionary.

        Returns:
            Dictionary representation of the metrics.
        """
        return {
            "timestamp": self.timestamp,
            "cpu_percent": self.cpu_percent,
            "memory_used_mb": round(self.memory_used_mb, 2),
            "memory_total_mb": round(self.memory_total_mb, 2),
            "disk_used_mb": round(self.disk_used_mb, 2),
            "disk_total_mb": round(self.disk_total_mb, 2),
            "python_version": self.python_version,
            "platform": self.platform_info,
            "pid": self.process_pid,
            "uptime_seconds": round(self.uptime_seconds, 2),
        }


class MetricsCollector:
    """Collects and reports system and application metrics."""

    def __init__(self, start_time: Optional[float] = None):
        self._start_time = start_time or time.time()
        self._counters: dict[str, int] = {}
        self._gauges: dict[str, float] = {}
        self._histograms: dict[str, list[float]] = {}
        self._snapshots: list[SystemMetrics] = []

    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a named counter.

        Args:
            name: Counter name.
            value: Amount to increment by.
        """
        self._counters[name] = self._counters.get(name, 0) + value

    def set_gauge(self, name: str, value: float) -> None:
        """Set a named gauge to a value.

        Args:
            name: Gauge name.
            value: Current value.
        """
        self._gauges[name] = value

    def record_histogram(self, name: str, value: float) -> None:
        """Record a value in a named histogram.

        Args:
            name: Histogram name.
            value: Value to record.
        """
        if name not in self._histograms:
            self._histograms[name] = []
        self._histograms[name].append(value)

    def collect_system_metrics(self, target_path: str = "/") -> SystemMetrics:
        """Collect current system metrics.

        Args:
            target_path: Filesystem path to check disk usage for.

        Returns:
            A SystemMetrics snapshot.
        """
        metrics = SystemMetrics(uptime_seconds=time.time() - self._start_time)

        try:
            import resource
            usage = resource.getrusage(resource.RUSAGE_SELF)
            metrics.memory_used_mb = usage.ru_maxrss / 1024  # Convert KB to MB on macOS
        except ImportError:
            pass

        try:
            stat = os.statvfs(target_path)
            metrics.disk_total_mb = (stat.f_blocks * stat.f_frsize) / (1024 * 1024)
            metrics.disk_free_mb = (stat.f_bfree * stat.f_frsize) / (1024 * 1024)
            metrics.disk_used_mb = metrics.disk_total_mb - metrics.disk_free_mb
        except OSError:
            pass

        self._snapshots.append(metrics)
        return metrics

    def get_histogram_stats(self, name: str) -> Optional[dict]:
        """Get statistics for a named histogram.

        Args:
            name: Histogram name.

        Returns:
            Dictionary with count, min, max, mean, p50, p95, p99, or None.
        """
        values = self._histograms.get(name)
        if not values:
            return None
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        return {
            "count": n,
            "min": sorted_vals[0],
            "max": sorted_vals[-1],
            "mean": sum(sorted_vals) / n,
            "p50": sorted_vals[n // 2],
            "p95": sorted_vals[int(n * 0.95)] if n > 1 else sorted_vals[0],
            "p99": sorted_vals[int(n * 0.99)] if n > 1 else sorted_vals[0],
        }

    def get_report(self) -> dict:
        """Get a full metrics report.

        Returns:
            Dictionary with uptime, counters, gauges, histograms, and snapshot count.
        """
        return {
            "uptime_seconds": round(time.time() - self._start_time, 2),
            "counters": dict(self._counters),
            "gauges": dict(self._gauges),
            "histograms": {k: self.get_histogram_stats(k) for k in self._histograms},
            "snapshot_count": len(self._snapshots),
        }

    def reset(self) -> None:
        """Clear all collected metrics."""
        self._counters.clear()
        self._gauges.clear()
        self._histograms.clear()
        self._snapshots.clear()
