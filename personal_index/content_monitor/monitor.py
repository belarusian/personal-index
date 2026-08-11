"""Content monitor for tracking changes and health."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from personal_index.content_monitor.info import (
    DiskUsageInfo,
    ErrorRateInfo,
    HealthReport,
    SourceFreshness,
)


@dataclass
class ContentMonitor:
    """Monitors content sources for freshness, errors, and disk usage.

    Attributes:
        index_dir: Directory to monitor for disk usage.
        max_staleness_hours: Hours after which a source is considered stale.
        max_error_rate: Maximum acceptable error rate before warning status.
        max_disk_mb: Maximum acceptable disk usage in MB before critical status.
        source_freshness: Per-source freshness tracking.
        error_rates: Aggregate error rate tracking.
    """

    index_dir: Path | None = None
    max_staleness_hours: float = 24.0
    max_error_rate: float = 0.1
    max_disk_mb: float = 1024.0
    source_freshness: dict[str, SourceFreshness] = field(default_factory=dict)
    error_rates: ErrorRateInfo = field(default_factory=ErrorRateInfo)

    def __post_init__(self) -> None:
        if self.index_dir is not None and not isinstance(self.index_dir, Path):
            self.index_dir = Path(self.index_dir)

    def get_disk_usage(self, top_n: int = 10) -> DiskUsageInfo:
        """Calculate disk usage for the index directory.

        Args:
            top_n: Number of largest files to include.

        Returns:
            DiskUsageInfo with usage statistics.
        """
        if self.index_dir is None or not self.index_dir.exists():
            return DiskUsageInfo()

        total_bytes = 0
        file_count = 0
        dir_count = 0
        all_files: list[tuple[str, int]] = []

        for root, dirs, files in os.walk(self.index_dir):
            dir_count += len(dirs)
            for fname in files:
                fpath = os.path.join(root, fname)
                try:
                    size = os.path.getsize(fpath)
                except OSError:
                    continue
                total_bytes += size
                file_count += 1
                all_files.append((fpath, size))

        # Sort by size descending and take top_n
        all_files.sort(key=lambda x: x[1], reverse=True)
        largest_files = all_files[:top_n]

        return DiskUsageInfo(
            total_bytes=total_bytes,
            file_count=file_count,
            dir_count=dir_count,
            largest_files=largest_files,
        )

    def record_crawl(
        self,
        source: str,
        success: bool,
        error_message: str | None = None,
        timestamp: datetime | None = None,
    ) -> None:
        """Record a crawl result for a source.

        Args:
            source: Source identifier.
            success: Whether the crawl succeeded.
            error_message: Error message if the crawl failed.
            timestamp: When the crawl occurred.
        """
        if timestamp is None:
            timestamp = datetime.now(timezone.utc)

        if source not in self.source_freshness:
            self.source_freshness[source] = SourceFreshness(source=source)

        sf = self.source_freshness[source]
        sf.crawl_count += 1

        if success:
            sf.last_crawled = timestamp
            sf.last_error = None
            sf.last_error_time = None
        else:
            if error_message is not None:
                sf.last_error = error_message
                sf.last_error_time = timestamp

        # Record in error rates
        self.error_rates.record_crawl(source, success, error_message)

    def get_source_freshness(
        self,
        source: str | None = None,
    ) -> dict[str, SourceFreshness]:
        """Get source freshness data.

        Args:
            source: Specific source to get, or None for all.

        Returns:
            Dictionary of source freshness data.
        """
        if source is not None:
            if source in self.source_freshness:
                return {source: self.source_freshness[source]}
            return {}
        return dict(self.source_freshness)

    def get_stale_sources(
        self,
        threshold_hours: float | None = None,
    ) -> list[SourceFreshness]:
        """Get sources that are stale.

        Args:
            threshold_hours: Hours threshold for staleness.

        Returns:
            List of stale SourceFreshness objects.
        """
        if threshold_hours is None:
            threshold_hours = self.max_staleness_hours
        return [
            sf for sf in self.source_freshness.values()
            if sf.is_stale(threshold_hours=threshold_hours)
        ]

    def get_error_rates(self) -> ErrorRateInfo:
        """Get current error rate information.

        Returns:
            ErrorRateInfo with current statistics.
        """
        return self.error_rates

    def generate_health_report(self) -> HealthReport:
        """Generate a comprehensive health report.

        Returns:
            HealthReport with current health status.
        """
        warnings: list[str] = []
        critical_issues: list[str] = []
        score = 1.0

        # Check if we have any data at all
        has_source_data = bool(self.source_freshness)
        has_error_data = self.error_rates.total_crawls > 0
        has_disk_data = self.index_dir is not None and self.index_dir.exists()

        if not has_source_data and not has_error_data and not has_disk_data:
            return HealthReport(
                overall_status="no_data",
                score=1.0,
            )

        # Check disk usage
        disk_usage = self.get_disk_usage()
        if has_disk_data and disk_usage.total_mb > self.max_disk_mb:
            critical_issues.append(
                f"Disk usage {disk_usage.total_mb:.2f} MB exceeds limit {self.max_disk_mb:.2f} MB"
            )
            score -= 0.3
        elif has_disk_data and disk_usage.total_mb > self.max_disk_mb * 0.8:
            warnings.append(
                f"Disk usage {disk_usage.total_mb:.2f} MB approaching limit {self.max_disk_mb:.2f} MB"
            )
            score -= 0.1

        # Check error rates — two-tier threshold
        # Warning when above max_error_rate, critical when >= 5x max_error_rate
        if has_error_data:
            if self.error_rates.error_rate >= 5 * self.max_error_rate:
                critical_issues.append(
                    f"Error rate {self.error_rates.error_rate:.1%} exceeds threshold {self.max_error_rate:.1%}"
                )
                score -= 0.3
            elif self.error_rates.error_rate > self.max_error_rate:
                warnings.append(
                    f"Error rate {self.error_rates.error_rate:.1%} approaching threshold {self.max_error_rate:.1%}"
                )
                score -= 0.1

        # Check source freshness
        stale_sources = self.get_stale_sources()
        total_sources = len(self.source_freshness)
        if total_sources > 0:
            stale_ratio = len(stale_sources) / total_sources
            if stale_ratio > 0.5 and len(stale_sources) > 1:
                critical_issues.append(
                    f"Majority of sources stale ({len(stale_sources)}/{total_sources})"
                )
                score -= 0.3
            elif stale_sources:
                warnings.append(
                    f"{len(stale_sources)} of {total_sources} sources are stale"
                )
                score -= 0.1

        # Clamp score
        score = max(0.0, min(1.0, score))

        # Determine overall status
        if critical_issues:
            overall_status = "critical"
        elif warnings:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return HealthReport(
            overall_status=overall_status,
            warnings=warnings,
            critical_issues=critical_issues,
            score=score,
            disk_usage=disk_usage,
            source_freshness=dict(self.source_freshness),
            error_rates=self.error_rates,
        )

    def reset(self) -> None:
        """Reset all monitoring data."""
        self.source_freshness = {}
        self.error_rates = ErrorRateInfo()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of monitoring data.

        Returns:
            Dictionary with monitoring summary.
        """
        disk_usage = self.get_disk_usage()
        stale_sources = self.get_stale_sources()

        return {
            "disk_usage_mb": disk_usage.total_mb,
            "file_count": disk_usage.file_count,
            "dir_count": disk_usage.dir_count,
            "total_sources": len(self.source_freshness),
            "total_crawls": self.error_rates.total_crawls,
            "error_rate": self.error_rates.error_rate,
            "success_rate": self.error_rates.success_rate,
            "stale_sources": len(stale_sources),
            "stale_source_names": [sf.source for sf in stale_sources],
        }
