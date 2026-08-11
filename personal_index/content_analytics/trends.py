"""Trend analysis for content items."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class TrendPoint:
    """A single point in a trend line.

    Attributes:
        timestamp: Time of this data point.
        value: Numeric value at this time.
        label: Optional label for this point.
    """

    timestamp: datetime
    value: float
    label: str = ""


@dataclass
class TrendAnalyzer:
    """Analyzes trends in content data over time.

    Attributes:
        window_days: Number of days for trend window.
        granularity: Granularity of trend points in hours.
    """

    window_days: int = 30
    granularity: int = 24

    def analyze_volume_trend(
        self,
        items: list[dict[str, Any]],
        date_field: str = "created_at",
    ) -> list[TrendPoint]:
        """Analyze content volume trend over time.

        Args:
            items: List of content items with timestamps.
            date_field: Field name for the timestamp.

        Returns:
            List of TrendPoint objects showing volume over time.
        """
        if not items:
            return []

        # Group items by time bucket
        buckets: dict[str, int] = {}
        for item in items:
            ts = item.get(date_field)
            if isinstance(ts, datetime):
                bucket = ts.strftime("%Y-%m-%d")
                buckets[bucket] = buckets.get(bucket, 0) + 1

        # Sort and create trend points
        sorted_buckets = sorted(buckets.items())
        return [
            TrendPoint(
                timestamp=datetime.strptime(date_str, "%Y-%m-%d"),
                value=count,
                label=date_str,
            )
            for date_str, count in sorted_buckets
        ]

    def analyze_score_trend(
        self,
        items: list[dict[str, Any]],
        date_field: str = "created_at",
    ) -> list[TrendPoint]:
        """Analyze average score trend over time.

        Args:
            items: List of content items with scores and timestamps.
            date_field: Field name for the timestamp.

        Returns:
            List of TrendPoint objects showing average score over time.
        """
        if not items:
            return []

        # Group scores by time bucket
        buckets: dict[str, list[float]] = {}
        for item in items:
            ts = item.get(date_field)
            score = item.get("score")
            if isinstance(ts, datetime) and isinstance(score, (int, float)):
                bucket = ts.strftime("%Y-%m-%d")
                buckets.setdefault(bucket, []).append(score)

        sorted_buckets = sorted(buckets.items())
        return [
            TrendPoint(
                timestamp=datetime.strptime(date_str, "%Y-%m-%d"),
                value=round(sum(scores) / len(scores), 4),
                label=date_str,
            )
            for date_str, scores in sorted_buckets
        ]

    def detect_anomalies(
        self,
        trend: list[TrendPoint],
        threshold: float = 2.0,
    ) -> list[TrendPoint]:
        """Detect anomalous points in a trend.

        Args:
            trend: List of trend points.
            threshold: Standard deviation multiplier for anomaly detection.

        Returns:
            List of TrendPoint objects that are anomalies.
        """
        if len(trend) < 3:
            return []

        values = [p.value for p in trend]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std_dev = variance ** 0.5

        if std_dev == 0:
            return []

        return [
            p for p in trend
            if abs(p.value - mean) > threshold * std_dev
        ]
