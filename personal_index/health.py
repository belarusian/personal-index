"""Health check and diagnostics - backward compatibility shim.

This module re-exports from content_health to maintain backward compatibility.
New code should import from personal_index.content_health directly.
"""

from __future__ import annotations

from personal_index.content_health import (
    HealthCheckResult,
    HealthChecker,
    HealthReport,
)

__all__ = [
    "HealthCheckResult",
    "HealthChecker",
    "HealthReport",
]
