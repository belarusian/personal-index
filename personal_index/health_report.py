"""Health report generation for the personal index system."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    name: str
    status: HealthStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 2),
            "timestamp": self.timestamp,
        }


@dataclass
class HealthReport:
    """Complete health report."""

    overall_status: HealthStatus = HealthStatus.HEALTHY
    checks: list[HealthCheckResult] = field(default_factory=list)
    generated_at: float = field(default_factory=time.time)
    version: str = "0.1.0"
    hostname: str = ""

    @property
    def check_count(self) -> int:
        return len(self.checks)

    @property
    def healthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.HEALTHY)

    @property
    def degraded_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.DEGRADED)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for c in self.checks if c.status == HealthStatus.UNHEALTHY)

    @property
    def total_duration_ms(self) -> float:
        return sum(c.duration_ms for c in self.checks)

    def is_healthy(self) -> bool:
        return self.overall_status == HealthStatus.HEALTHY

    def to_dict(self) -> dict:
        return {
            "overall_status": self.overall_status.value,
            "check_count": self.check_count,
            "healthy": self.healthy_count,
            "degraded": self.degraded_count,
            "unhealthy": self.unhealthy_count,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "generated_at": self.generated_at,
            "version": self.version,
            "hostname": self.hostname,
            "checks": [c.to_dict() for c in self.checks],
        }

    def to_summary(self) -> str:
        lines = [
            f"Health Report - Status: {self.overall_status.value.upper()}",
            f"Checks: {self.check_count} total, {self.healthy_count} healthy, "
            f"{self.degraded_count} degraded, {self.unhealthy_count} unhealthy",
            f"Duration: {self.total_duration_ms:.1f}ms",
        ]
        for check in self.checks:
            status_icon = "✓" if check.status == HealthStatus.HEALTHY else "✗"
            lines.append(f"  {status_icon} {check.name}: {check.status.value} - {check.message}")
        return "\n".join(lines)


class HealthReporter:
    """Generates health reports by running health checks."""

    def __init__(self, version: str = "0.1.0"):
        self._checks: list[tuple[str, callable]] = []
        self._version = version

    def register_check(self, name: str, check_fn: callable) -> None:
        self._checks.append((name, check_fn))

    def generate_report(self) -> HealthReport:
        report = HealthReport(version=self._version)
        start = time.time()

        for name, check_fn in self._checks:
            check_start = time.time()
            try:
                result = check_fn()
                if isinstance(result, HealthCheckResult):
                    result.duration_ms = (time.time() - check_start) * 1000
                    report.checks.append(result)
                elif isinstance(result, tuple) and len(result) >= 2:
                    status, message = result[0], result[1]
                    if isinstance(status, HealthStatus):
                        report.checks.append(HealthCheckResult(
                            name=name,
                            status=status,
                            message=message,
                            duration_ms=(time.time() - check_start) * 1000,
                        ))
            except Exception as e:
                report.checks.append(HealthCheckResult(
                    name=name,
                    status=HealthStatus.UNHEALTHY,
                    message=str(e),
                    duration_ms=(time.time() - check_start) * 1000,
                ))

        report.overall_status = self._compute_overall_status(report.checks)
        report.generated_at = time.time()
        return report

    def _compute_overall_status(self, checks: list[HealthCheckResult]) -> HealthStatus:
        if not checks:
            return HealthStatus.UNKNOWN
        if any(c.status == HealthStatus.UNHEALTHY for c in checks):
            return HealthStatus.UNHEALTHY
        if any(c.status == HealthStatus.DEGRADED for c in checks):
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
