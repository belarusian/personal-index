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
