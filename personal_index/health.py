"""Health check and diagnostics for personal index."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from personal_index.storage import Storage


@dataclass
class HealthCheckResult:
    """Result of a single health check."""
    check_name: str
    status: str  # "ok", "warning", "error"
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
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

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(timezone.utc).isoformat()
        self._compute_overall()

    def _compute_overall(self):
        statuses = [c.status for c in self.checks]
        if "error" in statuses:
            self.overall_status = "error"
        elif "warning" in statuses:
            self.overall_status = "warning"
        else:
            self.overall_status = "ok"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "overall_status": self.overall_status,
            "checks": [c.to_dict() for c in self.checks],
        }

    def summary(self) -> str:
        lines = [f"Health Report: {self.overall_status.upper()}"]
        for c in self.checks:
            icon = {"ok": "✓", "warning": "⚠", "error": "✗"}.get(c.status, "?")
            lines.append(f"  {icon} {c.check_name}: {c.message}")
        return "\n".join(lines)


class HealthChecker:
    """Run health checks on the personal index system."""

    def __init__(self, data_dir: Optional[str] = None):
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
        """Check storage file integrity."""
        storage_path = Path(self.data_dir) / "storage.db"
        if not storage_path.exists():
            return HealthCheckResult(
                check_name="storage_integrity",
                status="warning",
                message="No storage database found",
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
