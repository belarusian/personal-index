"""Comprehensive health report generation for personal-index."""

from __future__ import annotations

import os
import platform
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: str  # "healthy", "degraded", "unhealthy"
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class HealthReport:
    """Complete system health report."""

    timestamp: str = ""
    version: str = ""
    checks: list[HealthCheckResult] = field(default_factory=list)
    summary: str = ""

    @property
    def is_healthy(self) -> bool:
        """True if all checks are healthy."""
        return all(c.status == "healthy" for c in self.checks)

    @property
    def is_degraded(self) -> bool:
        """True if any check is degraded but none unhealthy."""
        return any(c.status == "degraded" for c in self.checks) and self.is_healthy or (
            not any(c.status == "unhealthy" for c in self.checks)
            and not self.is_healthy
        )

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary."""
        return {
            "timestamp": self.timestamp,
            "version": self.version,
            "is_healthy": self.is_healthy,
            "is_degraded": self.is_degraded,
            "checks": [
                {
                    "name": c.name,
                    "status": c.status,
                    "message": c.message,
                    "details": c.details,
                }
                for c in self.checks
            ],
            "summary": self.summary,
        }


class HealthReporter:
    """Generates comprehensive health reports for the system."""

    def __init__(self, version: str = "unknown") -> None:
        self.version = version

    def generate_report(self, extra_checks: list[callable] | None = None) -> HealthReport:
        """Generate a full health report.

        Args:
            extra_checks: Optional list of callables returning HealthCheckResult.

        Returns:
            Complete HealthReport instance.
        """
        checks: list[HealthCheckResult] = []

        # Built-in checks
        checks.append(self._check_python_version())
        checks.append(self._check_disk_space())
        checks.append(self._check_memory())
        checks.append(self._check_timezone())
        checks.append(self._check_writable_home())

        # Extra user-provided checks
        if extra_checks:
            for check_fn in extra_checks:
                try:
                    result = check_fn()
                    if isinstance(result, HealthCheckResult):
                        checks.append(result)
                except Exception as e:
                    checks.append(HealthCheckResult(
                        name=check_fn.__name__,
                        status="unhealthy",
                        message=str(e),
                    ))

        healthy_count = sum(1 for c in checks if c.status == "healthy")
        degraded_count = sum(1 for c in checks if c.status == "degraded")
        unhealthy_count = sum(1 for c in checks if c.status == "unhealthy")

        report = HealthReport(
            timestamp=datetime.now(timezone.utc).isoformat(),
            version=self.version,
            checks=checks,
            summary=f"{healthy_count} healthy, {degraded_count} degraded, {unhealthy_count} unhealthy",
        )
        return report

    def _check_python_version(self) -> HealthCheckResult:
        """Check Python version compatibility."""
        version = sys.version_info
        if version.major < 3:
            return HealthCheckResult(
                name="python_version",
                status="unhealthy",
                message=f"Python {version.major}.{version.minor} is not supported",
            )
        if version.major == 3 and version.minor < 9:
            return HealthCheckResult(
                name="python_version",
                status="degraded",
                message=f"Python {version.major}.{version.minor} may have limited support",
                details={"version": f"{version.major}.{version.minor}.{version.micro}"},
            )
        return HealthCheckResult(
            name="python_version",
            status="healthy",
            message=f"Python {version.major}.{version.minor}.{version.micro}",
            details={"version": f"{version.major}.{version.minor}.{version.micro}"},
        )

    def _check_disk_space(self) -> HealthCheckResult:
        """Check available disk space."""
        try:
            stat = os.statvfs("/")
            available = stat.f_frsize * stat.f_bavail
            total = stat.f_frsize * stat.f_blocks
            pct_free = (available / total * 100) if total > 0 else 0

            if pct_free < 5:
                status = "unhealthy"
            elif pct_free < 15:
                status = "degraded"
            else:
                status = "healthy"

            return HealthCheckResult(
                name="disk_space",
                status=status,
                message=f"{pct_free:.1f}% free ({available / 1024**3:.1f} GB)",
                details={"available_bytes": available, "total_bytes": total, "pct_free": pct_free},
            )
        except Exception as e:
            return HealthCheckResult(
                name="disk_space",
                status="unhealthy",
                message=f"Cannot check disk space: {e}",
            )

    def _check_memory(self) -> HealthCheckResult:
        """Check available memory if possible."""
        try:
            import psutil
            mem = psutil.virtual_memory()
            pct_avail = mem.available / mem.total * 100
            status = "healthy" if pct_avail > 10 else ("degraded" if pct_avail > 5 else "unhealthy")
            return HealthCheckResult(
                name="memory",
                status=status,
                message=f"{pct_avail:.1f}% available ({mem.available / 1024**2:.1f} MB)",
                details={"total_mb": mem.total / 1024**2, "available_mb": mem.available / 1024**2},
            )
        except ImportError:
            return HealthCheckResult(
                name="memory",
                status="healthy",
                message="psutil not installed, skipping memory check",
            )
        except Exception as e:
            return HealthCheckResult(
                name="memory",
                status="degraded",
                message=f"Cannot check memory: {e}",
            )

    def _check_timezone(self) -> HealthCheckResult:
        """Check timezone configuration."""
        try:
            tz = time.tzname
            return HealthCheckResult(
                name="timezone",
                status="healthy",
                message=f"Timezone: {tz}",
                details={"tzname": list(tz)},
            )
        except Exception as e:
            return HealthCheckResult(
                name="timezone",
                status="degraded",
                message=f"Cannot determine timezone: {e}",
            )

    def _check_writable_home(self) -> HealthCheckResult:
        """Check if home directory is writable."""
        home = Path.home()
        test_file = home / ".personal_index_health_check"
        try:
            test_file.touch()
            test_file.unlink()
            return HealthCheckResult(
                name="writable_home",
                status="healthy",
                message=f"Home directory {home} is writable",
            )
        except Exception as e:
            return HealthCheckResult(
                name="writable_home",
                status="unhealthy",
                message=f"Home directory {home} is not writable: {e}",
            )
