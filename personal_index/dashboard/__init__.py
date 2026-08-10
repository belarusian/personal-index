"""Admin dashboard module for personal-index."""

from personal_index.dashboard.aggregator import (
    DashboardAggregator,
    AggregatedStats,
    TimeSeriesPoint,
)
from personal_index.dashboard.export import (
    DashboardExporter,
    ExportFormat,
)
from personal_index.dashboard.stats import RealTimeStats
from personal_index.stats import StatsCollector

__all__ = [
    "DashboardAggregator",
    "AggregatedStats",
    "TimeSeriesPoint",
    "DashboardExporter",
    "ExportFormat",
    "RealTimeStats",
    "StatsCollector",
]
