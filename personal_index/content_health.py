"""Content health monitoring for personal index.

Provides a lightweight health check for the content subsystem,
returning status, timestamp, and a numeric score.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional


def check_health(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Run a health check on the content subsystem.

    Args:
        data_dir: Optional path to the data directory. Defaults to
            ~/.personal_index if not provided.

    Returns:
        A dict with keys:
            - status: "healthy", "degraded", or "unhealthy"
            - last_check: ISO 8601 timestamp of when the check ran
            - score: numeric score from 0.0 to 1.0
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


def get_health_report(data_dir: Optional[str] = None) -> Dict[str, Any]:
    """Get a detailed health report for the content subsystem.

    Args:
        data_dir: Optional path to the data directory. Defaults to
            ~/.personal_index if not provided.

    Returns:
        A dict with health status details including:
            - status: "healthy", "degraded", or "unhealthy"
            - last_check: ISO 8601 timestamp
            - score: numeric score from 0.0 to 1.0
            - checks: list of individual check results
    """
    if data_dir is None:
        data_dir = str(Path.home() / ".personal_index")

    data_path = Path(data_dir)
    checks: list[Dict[str, Any]] = []

    # Check 1: data directory exists
    checks.append({
        "name": "data_directory_exists",
        "passed": data_path.exists() and data_path.is_dir(),
        "description": "Data directory exists and is a directory",
    })

    # Check 2: readable
    checks.append({
        "name": "data_directory_readable",
        "passed": data_path.exists() and os.access(str(data_path), os.R_OK),
        "description": "Data directory is readable",
    })

    # Check 3: writable
    checks.append({
        "name": "data_directory_writable",
        "passed": data_path.exists() and os.access(str(data_path), os.W_OK),
        "description": "Data directory is writable",
    })

    # Check 4: storage database
    storage_path = data_path / "storage.db"
    checks.append({
        "name": "storage_database_exists",
        "passed": storage_path.exists(),
        "description": "Storage database file exists",
    })

    # Check 5: config file
    config_path = data_path / "config.yaml"
    checks.append({
        "name": "config_file_exists",
        "passed": config_path.exists(),
        "description": "Configuration file exists",
    })

    health = check_health(data_dir)

    return {
        "status": health["status"],
        "last_check": health["last_check"],
        "score": health["score"],
        "checks": checks,
    }
