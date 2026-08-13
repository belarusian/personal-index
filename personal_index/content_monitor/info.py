"""Data classes for content monitoring metrics."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class DiskUsageInfo:
    """Disk usage information for an index directory.

    Attributes:
        total_bytes: Total size of all files in bytes.
        file_count: Number of files.
        dir_count: Number of directories.
        largest_files: List of (path, size_bytes) tuples sorted by size descending.
    """

    total_bytes: int = 0
    file_count: int = 0
    dir_count: int = 0
    largest_files: list[tuple[str, int]] = field(default_factory=list)

    @property
    def total_mb(self) -> float:
        """Total size in megabytes."""
        return self.total_bytes / (1024 * 1024)

    @property
    def total_gb(self) -> float:
        """Total size in gigabytes."""
        return self.total_bytes / (1024 * 1024 * 1024)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_bytes": self.total_bytes,
            "total_mb": self.total_mb,
            "total_gb": self.total_gb,
            "file_count": self.file_count,
            "dir_count": self.dir_count,
            "largest_files": [
                {"path": path, "size_bytes": size}
                for path, size in self.largest_files
            ],
        }


@dataclass
class SourceFreshness:
    """Freshness information for a content source.

    Attributes:
        source: Source identifier (e.g., domain name).
        last_crawled: Timestamp of the last successful crawl.
        crawl_count: Total number of crawls.
        last_error: Error message from the last failed crawl.
        last_error_time: Timestamp of the last error.
    """

    source: str = ""
    last_crawled: datetime | None = None
    crawl_count: int = 0
    last_error: str | None = None
    last_error_time: datetime | None = None

    @property
    def staleness_hours(self) -> float | None:
        """Hours since last crawl, or None if never crawled."""
        if self.last_crawled is None:
            return None
        now = datetime.now(timezone.utc)
        delta = now - self.last_crawled
        return delta.total_seconds() / 3600.0

    def is_stale(self, threshold_hours: float = 24.0) -> bool:
        """Check if the source is stale.

        Args:
            threshold_hours: Hours after which a source is considered stale.

        Returns:
            True if the source is stale.
        """
        if self.last_crawled is None:
            return True
        staleness = self.staleness_hours
        if staleness is None:
            return True
        return staleness > threshold_hours

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "source": self.source,
            "last_crawled": self.last_crawled.isoformat() if self.last_crawled else None,
            "crawl_count": self.crawl_count,
            "last_error": self.last_error,
            "last_error_time": self.last_error_time.isoformat() if self.last_error_time else None,
            "staleness_hours": self.staleness_hours,
            "is_stale": self.is_stale(),
        }


@dataclass
class ErrorRateInfo:
    """Error rate tracking for crawls.

    Attributes:
        total_crawls: Total number of crawls.
        successful_crawls: Number of successful crawls.
        failed_crawls: Number of failed crawls.
        error_rate: Ratio of failed to total crawls.
        recent_errors: List of recent error records (capped at 100).
    """

    total_crawls: int = 0
    successful_crawls: int = 0
    failed_crawls: int = 0
    error_rate: float = 0.0
    recent_errors: list[dict[str, Any]] = field(default_factory=list)

    @property
    def success_rate(self) -> float:
        """Ratio of successful to total crawls."""
        if self.total_crawls == 0:
            return 0.0
        return self.successful_crawls / self.total_crawls

    def record_crawl(
        self,
        source: str,
        success: bool,
        error_message: str | None = None,
    ) -> None:
        """Record a crawl result.

        Args:
            source: Source identifier.
            success: Whether the crawl succeeded.
            error_message: Error message if the crawl failed.
        """
        self.total_crawls += 1
        if success:
            self.successful_crawls += 1
        else:
            self.failed_crawls += 1
            if error_message is not None:
                self.recent_errors.append({
                    "source": source,
                    "error": error_message,
                })
                # Cap at 100
                if len(self.recent_errors) > 100:
                    self.recent_errors = self.recent_errors[-100:]

        # Recalculate error rate
        if self.total_crawls > 0:
            self.error_rate = self.failed_crawls / self.total_crawls

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "total_crawls": self.total_crawls,
            "successful_crawls": self.successful_crawls,
            "failed_crawls": self.failed_crawls,
            "error_rate": self.error_rate,
            "success_rate": self.success_rate,
            "recent_errors_count": len(self.recent_errors),
        }


@dataclass
class HealthReport:
    """Overall health report for content monitoring.

    Attributes:
        overall_status: Overall health status string.
        warnings: List of warning messages.
        critical_issues: List of critical issue messages.
        score: Health score from 0.0 to 1.0.
        disk_usage: Disk usage information.
        source_freshness: Source freshness data.
        error_rates: Error rate information.
    """

    overall_status: str = "unknown"
    warnings: list[str] = field(default_factory=list)
    critical_issues: list[str] = field(default_factory=list)
    score: float = 1.0
    disk_usage: DiskUsageInfo | None = None
    source_freshness: dict[str, SourceFreshness] = field(default_factory=dict)
    error_rates: ErrorRateInfo | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "overall_status": self.overall_status,
            "score": self.score,
            "warnings": self.warnings,
            "critical_issues": self.critical_issues,
        }
        if self.disk_usage is not None:
            result["disk_usage"] = self.disk_usage.to_dict()
        if self.source_freshness:
            result["source_freshness"] = {
                k: v.to_dict() for k, v in self.source_freshness.items()
            }
        if self.error_rates is not None:
            result["error_rates"] = self.error_rates.to_dict()
        return result

    def to_summary_string(self) -> str:
        """Generate a human-readable summary string."""
        lines = [
            "=" * 60, "Health Report", "=" * 60,
            f"Status: {self.overall_status}", f"Score: {self.score:.2f}", "",
        ]
        self._render_disk(lines)
        self._render_freshness(lines)
        self._render_errors(lines)
        self._render_warnings(lines)
        return "\n".join(lines)

    def _render_disk(self, lines: list[str]) -> None:
        """Render disk usage section."""
        if self.disk_usage is None:
            return
        lines.extend([
            "--- Disk Usage ---",
            f"Total: {self.disk_usage.total_mb:.2f} MB",
            f"Files: {self.disk_usage.file_count}",
            f"Directories: {self.disk_usage.dir_count}", "",
        ])

    def _render_freshness(self, lines: list[str]) -> None:
        """Render source freshness section."""
        if not self.source_freshness:
            return
        lines.append("--- Source Freshness ---")
        for source, f in self.source_freshness.items():
            status = "STALE" if f.is_stale() else "OK"
            s = f"{f.staleness_hours:.1f}h" if f.staleness_hours is not None else "never"
            lines.append(f"  {source}: {status} (last crawled: {s} ago)")
        lines.append("")

    def _render_errors(self, lines: list[str]) -> None:
        """Render error rates section."""
        if self.error_rates is None:
            return
        lines.extend([
            "--- Error Rates ---",
            f"Total crawls: {self.error_rates.total_crawls}",
            f"Success rate: {self.error_rates.success_rate:.1%}",
            f"Error rate: {self.error_rates.error_rate:.1%}", "",
        ])

    def _render_warnings(self, lines: list[str]) -> None:
        """Render warnings and critical issues."""
        if self.warnings:
            lines.append("--- Warnings ---")
            for w in self.warnings:
                lines.append(f"  - {w}")
            lines.append("")
        if self.critical_issues:
            lines.append("--- Critical Issues ---")
            for i in self.critical_issues:
                lines.append(f"  - {i}")
            lines.append("")
