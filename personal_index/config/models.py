"""Configuration data models — re-exported from personal_index.models."""

from __future__ import annotations

from personal_index.models import (
    AppConfig,
    CrawlConfig,
    IndexConfig,
    Interest,
    MatchMode,
    SchedulerConfig,
)

# Re-export for backward compatibility
__all__ = [
    "AppConfig",
    "CrawlerConfig",
    "IndexConfig",
    "Interest",
    "MatchMode",
    "SchedulerConfig",
]

# Alias for backward compatibility
CrawlerConfig = CrawlConfig
