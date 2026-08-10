"""Content health monitoring for personal index.

Provides a lightweight health check for the content subsystem,
returning status, timestamp, and a numeric score.

Also provides URL accessibility checking for saved content URLs.
And includes the HealthCheckResult/HealthReport/HealthChecker classes
from the original health.py module.
"""

from __future__ import annotations

import os
import platform
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
from urllib.parse import urlparse

import requests


# ---------------------------------------------------------------------------
# HealthCheckResult / HealthReport / HealthChecker from health.py (merged in)
# ---------------------------------------------------------------------------


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    check_name: str
    status: str  # "ok", "warning", "error"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "check": self.check_name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass
class HealthReport:
    """Complete health report."""

    timestamp: str = ""
    checks: List[HealthCheckResult] = field(default_factory=list)
    overall_status: str = "ok"

    def __post_init__(self) -> None:
        """Set timestamp and compute overall status after init."""
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self._compute_overall()

    def _compute_overall(self) -> None:
        """Compute overall status from individual check statuses."""
        statuses = [c.status for c in self.checks]
        if "error" in statuses:
            self.overall_status = "error"
        elif "warning" in statuses:
            self.overall_status = "warning"
        else:
            self.overall_status = "ok"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [f"Health Report: {self.overall_status.upper()}"]
        for c in self.checks:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗"}.get(c.status, "?")
            lines.append(f"  {icon} {c.check_name}: {c.message}")
        return "\n".join(lines)


class HealthChecker:
    """Run health checks on the personal index system."""

    def __init__(self, data_dir: str | None = None) -> None:
        """Initialize HealthChecker.

        Args:
            data_dir: Path to the data directory.
        """
        self.data_dir = data_dir or str(Path.home() / ".personal_index")

    def run_all(self) -> HealthReport:
        """Run all health checks."""
        checks = [
            self.check_python_version(),
            self.check_data_directory(),
            self.check_disk_space(),
            self.check_storage_integrity(),
            self.check_config_file(),
            self.check_database(),
            self.check_permissions(),
            self.check_dependencies(),
        ]
        return HealthReport(checks=checks)

    def check_python_version(self) -> HealthCheckResult:
        """Check Python version compatibility."""
        version = sys.version_info
        status = "ok"
        message = f"Python {version.major}.{version.minor}.{version.micro}"

        if version.major < 3 or (version.major == 3 and version.minor < 9):
            status = "error"
            message = f"Python {version.major}.{version.minor} is below minimum 3.9"

        return HealthCheckResult(
            check_name="python_version",
            status=status,
            message=message,
            details={"version": platform.python_version()},
        )

    def check_data_directory(self) -> HealthCheckResult:
        """Check data directory exists and is accessible."""
        data_path = Path(self.data_dir)
        if not data_path.exists():
            return HealthCheckResult(
                check_name="data_directory",
                status="warning",
                message=f"Data directory does not exist: {self.data_dir}",
                details={"path": self.data_dir},
            )
        return HealthCheckResult(
            check_name="data_directory",
            status="ok",
            message=f"Data directory exists: {self.data_dir}",
            details={"path": self.data_dir},
        )

    def check_disk_space(self, min_bytes: int = 100 * 1024 * 1024) -> HealthCheckResult:
        """Check available disk space."""
        try:
            usage = shutil.disk_usage(self.data_dir)
            available_mb = usage.free / (1024 * 1024)
            status = "ok"
            if usage.free < min_bytes:
                status = "warning"
            elif usage.free < min_bytes / 10:
                status = "error"

            return HealthCheckResult(
                check_name="disk_space",
                status=status,
                message=f"{available_mb:.0f} MB available",
                details={
                    "total_mb": usage.total / (1024 * 1024),
                    "used_mb": usage.used / (1024 * 1024),
                    "free_mb": available_mb,
                },
            )
        except OSError as e:
            return HealthCheckResult(
                check_name="disk_space",
                status="error",
                message=f"Cannot check disk space: {e}",
            )

    def check_storage_integrity(self) -> HealthCheckResult:
        """Check storage database integrity."""
        storage_path = Path(self.data_dir) / "storage.db"
        if not storage_path.exists():
            return HealthCheckResult(
                check_name="storage_integrity",
                status="warning",
                message="Storage database not found",
                details={"path": str(storage_path)},
            )
        try:
            size = storage_path.stat().st_size
            return HealthCheckResult(
                check_name="storage_integrity",
                status="ok",
                message=f"Storage database exists ({size} bytes)",
                details={"path": str(storage_path), "size": size},
            )
        except OSError as e:
            return HealthCheckResult(
                check_name="storage_integrity",
                status="error",
                message=f"Cannot access storage: {e}",
            )

    def check_config_file(self) -> HealthCheckResult:
        """Check configuration file."""
        config_path = Path(self.data_dir) / "config.yaml"
        if not config_path.exists():
            return HealthCheckResult(
                check_name="config_file",
                status="warning",
                message="No configuration file found",
                details={"path": str(config_path)},
            )

        try:
            content = config_path.read_text()
            if not content.strip():
                return HealthCheckResult(
                    check_name="config_file",
                    status="warning",
                    message="Configuration file is empty",
                )
            return HealthCheckResult(
                check_name="config_file",
                status="ok",
                message="Configuration file exists and is valid",
                details={"path": str(config_path), "size": len(content)},
            )
        except OSError as e:
            return HealthCheckResult(
                check_name="config_file",
                status="error",
                message=f"Cannot read config: {e}",
            )

    def check_database(self) -> HealthCheckResult:
        """Check SQLite database integrity."""
        storage_path = Path(self.data_dir) / "storage.db"
        if not storage_path.exists():
            return HealthCheckResult(
                check_name="database",
                status="warning",
                message="No database found",
            )

        try:
            import sqlite3
            conn = sqlite3.connect(str(storage_path))
            cursor = conn.execute("PRAGMA integrity_check")
            result = cursor.fetchone()[0]
            conn.close()

            if result == "ok":
                return HealthCheckResult(
                    check_name="database",
                    status="ok",
                    message="Database integrity check passed",
                )
            else:
                return HealthCheckResult(
                    check_name="database",
                    status="error",
                    message=f"Database integrity check failed: {result}",
                )
        except Exception as e:
            return HealthCheckResult(
                check_name="database",
                status="error",
                message=f"Database check failed: {e}",
            )

    def check_permissions(self) -> HealthCheckResult:
        """Check file permissions on data directory."""
        data_path = Path(self.data_dir)
        if not data_path.exists():
            return HealthCheckResult(
                check_name="permissions",
                status="warning",
                message="Data directory does not exist",
            )

        readable = os.access(str(data_path), os.R_OK)
        writable = os.access(str(data_path), os.W_OK)

        if readable and writable:
            return HealthCheckResult(
                check_name="permissions",
                status="ok",
                message="Data directory is readable and writable",
                details={"readable": readable, "writable": writable},
            )
        elif readable:
            return HealthCheckResult(
                check_name="permissions",
                status="warning",
                message="Data directory is read-only",
                details={"readable": readable, "writable": writable},
            )
        else:
            return HealthCheckResult(
                check_name="permissions",
                status="error",
                message="Data directory is not accessible",
                details={"readable": readable, "writable": writable},
            )

    def check_dependencies(self) -> HealthCheckResult:
        """Check that required dependencies are installed."""
        required = ["sqlite3", "json", "hashlib", "urllib"]
        missing = []
        for dep in required:
            try:
                __import__(dep)
            except ImportError:
                missing.append(dep)

        if missing:
            return HealthCheckResult(
                check_name="dependencies",
                status="error",
                message=f"Missing dependencies: {', '.join(missing)}",
                details={"missing": missing},
            )
        return HealthCheckResult(
            check_name="dependencies",
            status="ok",
            message="All required dependencies available",
            details={"checked": required},
        )


# ---------------------------------------------------------------------------
# Original content_health.py functions (unchanged)
# ---------------------------------------------------------------------------


def check_health(data_dir: str | None = None) -> Dict[str, Any]:
    """Check overall content health status.

    Args:
        data_dir: Path to data directory.

    Returns:
        Dict with health status, score, and details.
    """
    if data_dir is None:
        data_dir = str(Path.home() / ".personal_index")

    score = 1.0
    issues: list[str] = []

    # Check 1: data directory exists
    data_path = Path(data_dir)
    if not data_path.exists():
        score -= 0.3
        issues.append("data directory missing")
    elif not data_path.is_dir():
        score -= 0.3
        issues.append("data path is not a directory")

    # Check 2: data directory is readable
    if data_path.exists() and not os.access(str(data_path), os.R_OK):
        score -= 0.2
        issues.append("data directory not readable")

    # Check 3: data directory is writable
    if data_path.exists() and not os.access(str(data_path), os.W_OK):
        score -= 0.2
        issues.append("data directory not writable")

    # Check 4: storage database exists
    storage_path = data_path / "storage.db"
    if data_path.exists() and not storage_path.exists():
        score -= 0.15
        issues.append("storage database missing")

    # Check 5: config file exists
    config_path = data_path / "config.yaml"
    if data_path.exists() and not config_path.exists():
        score -= 0.1
        issues.append("config file missing")

    # Clamp score to [0.0, 1.0]
    score = max(0.0, min(1.0, score))

    # Determine status from score
    if score >= 0.8:
        status = "healthy"
    elif score >= 0.5:
        status = "degraded"
    else:
        status = "unhealthy"

    last_check = datetime.now(timezone.utc).isoformat()

    return {
        "status": status,
        "last_check": last_check,
        "score": score,
    }


def get_health_report(data_dir: str | None = None) -> Dict[str, Any]:
    """Get a comprehensive health report as a dictionary.

    Args:
        data_dir: Path to data directory.

    Returns:
        Dict with health report data.
    """
    checker = HealthChecker(data_dir=data_dir)
    report = checker.run_all()
    return report.to_dict()


# ---------------------------------------------------------------------------
# URL accessibility health check
# ---------------------------------------------------------------------------


@dataclass
class UrlHealthResult:
    """Result of URL health check."""

    url: str
    status_code: int | None
    is_accessible: bool
    error: str | None
    checked_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "url": self.url,
            "status_code": self.status_code,
            "is_accessible": self.is_accessible,
            "error": self.error,
            "checked_at": self.checked_at,
        }


def _is_valid_http_url(url: str) -> bool:
    """Validate if URL is a proper HTTP/HTTPS URL.

    Args:
        url: URL string to validate.

    Returns:
        True if valid HTTP URL.
    """
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False


def check_url_accessibility(
    url: str,
    timeout: int = 5,
) -> UrlHealthResult:
    """Check if a URL is accessible.

    Args:
        url: URL to check.
        timeout: Request timeout in seconds.

    Returns:
        UrlHealthResult with status info.
    """
    if not _is_valid_http_url(url):
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error="Invalid URL",
        )

    try:
        # Try HEAD first (lighter weight)
        resp = requests.head(url, timeout=timeout, allow_redirects=True)

        # If server doesn't support HEAD, fall back to GET
        if resp.status_code == 405:
            resp = requests.get(url, timeout=timeout, allow_redirects=True)

        is_accessible = resp.status_code < 400
        error = None if is_accessible else f"HTTP {resp.status_code}"

        return UrlHealthResult(
            url=url,
            status_code=resp.status_code,
            is_accessible=is_accessible,
            error=error,
        )

    except requests.Timeout:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error="Request timed out",
        )
    except requests.ConnectionError as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Connection error: {exc}",
        )
    except requests.RequestException as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Request failed: {exc}",
        )
    except Exception as exc:
        return UrlHealthResult(
            url=url,
            status_code=None,
            is_accessible=False,
            error=f"Unexpected error: {exc}",
        )


def check_content_urls(
    storage: Any,
    timeout: int = 5,
) -> List[UrlHealthResult]:
    """Check accessibility of multiple content URLs.

    Args:
        storage: A storage object with a ``get_pages()`` method.
        timeout: Request timeout in seconds per URL.

    Returns:
        List of UrlHealthResult objects.
    """
    pages = storage.get_pages()
    results: List[UrlHealthResult] = []
    for page in pages:
        result = check_url_accessibility(page.url, timeout=timeout)
        results.append(result)
    return results
