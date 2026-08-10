"""Real-time statistics for the admin dashboard."""

from __future__ import annotations

from personal_index.stats import StatsCollector  # noqa: E402

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class RealTimeStats:
    """Real-time operational statistics for the dashboard."""

    active_crawls: int = 0
    queue_depth: int = 0
    pages_per_minute: float = 0.0
    errors_last_hour: int = 0
    avg_response_time_ms: float = 0.0
    memory_usage_mb: float = 0.0
    uptime_seconds: float = 0.0
    last_crawl_at: Optional[str] = None
    recent_errors: List[Dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "active_crawls": self.active_crawls,
            "queue_depth": self.queue_depth,
            "pages_per_minute": round(self.pages_per_minute, 2),
            "errors_last_hour": self.errors_last_hour,
            "avg_response_time_ms": round(self.avg_response_time_ms, 1),
            "memory_usage_mb": round(self.memory_usage_mb, 1),
            "uptime_seconds": round(self.uptime_seconds, 0),
            "last_crawl_at": self.last_crawl_at,
            "recent_errors": self.recent_errors[:10],
        }


# Re-export StatsCollector for convenience
