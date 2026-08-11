"""Content analytics module for personal-index.

Provides analytics and insights about content collections,
including trends, distributions, and performance metrics.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ContentAnalytics:
    """Analytics report for a content collection.

    Attributes:
        total_items: Total number of content items.
        unique_domains: Number of unique source domains.
        unique_tags: Number of unique tags.
        avg_score: Average content score.
        avg_word_count: Average word count.
        bookmarked_count: Number of bookmarked items.
        tagged_count: Number of tagged items.
        top_domains: Most common source domains.
        top_tags: Most common tags.
        score_distribution: Score distribution buckets.
        daily_counts: Items per day.
        oldest_item: Date of oldest item.
        newest_item: Date of newest item.
    """

    total_items: int = 0
    unique_domains: int = 0
    unique_tags: int = 0
    avg_score: float = 0.0
    avg_word_count: float = 0.0
    bookmarked_count: int = 0
    tagged_count: int = 0
    top_domains: list[tuple[str, int]] = field(default_factory=list)
    top_tags: list[tuple[str, int]] = field(default_factory=list)
    score_distribution: dict[str, int] = field(default_factory=dict)
    daily_counts: dict[str, int] = field(default_factory=dict)
    oldest_item: datetime | None = None
    newest_item: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_items": self.total_items,
            "unique_domains": self.unique_domains,
            "unique_tags": self.unique_tags,
            "avg_score": round(self.avg_score, 4),
            "avg_word_count": round(self.avg_word_count, 1),
            "bookmarked_count": self.bookmarked_count,
            "tagged_count": self.tagged_count,
            "top_domains": self.top_domains,
            "top_tags": self.top_tags,
            "score_distribution": self.score_distribution,
            "daily_counts": self.daily_counts,
            "oldest_item": self.oldest_item.isoformat() if self.oldest_item else None,
            "newest_item": self.newest_item.isoformat() if self.newest_item else None,
        }


class AnalyticsEngine:
    """Computes analytics from content collections.

    Analyzes content items to produce insights about
    distributions, trends, and quality metrics.
    """

    def analyze(
        self,
        items: list[dict[str, Any]],
        top_n: int = 10,
    ) -> ContentAnalytics:
        """Analyze a collection of content items.

        Args:
            items: List of content item dictionaries.
            top_n: Number of top items to include.

        Returns:
            ContentAnalytics report.
        """
        if not items:
            return ContentAnalytics()

        analytics = ContentAnalytics()
        analytics.total_items = len(items)

        # Domain analysis
        domains = Counter()
        for item in items:
            url = item.get("url", "")
            if "://" in url:
                domain = url.split("://")[1].split("/")[0]
                domains[domain] += 1

        analytics.unique_domains = len(domains)
        analytics.top_domains = domains.most_common(top_n)

        # Tag analysis
        tags = Counter()
        tagged_count = 0
        for item in items:
            item_tags = item.get("tags", [])
            if item_tags:
                tagged_count += 1
                for tag in item_tags:
                    tags[tag] += 1

        analytics.unique_tags = len(tags)
        analytics.tagged_count = tagged_count
        analytics.top_tags = tags.most_common(top_n)

        # Score analysis
        scores = [item.get("score", 0.0) for item in items if "score" in item]
        if scores:
            analytics.avg_score = sum(scores) / len(scores)
            analytics.score_distribution = self._score_buckets(scores)

        # Word count analysis
        word_counts = [
            item.get("word_count", 0)
            for item in items
            if "word_count" in item
        ]
        if word_counts:
            analytics.avg_word_count = sum(word_counts) / len(word_counts)

        # Bookmark analysis
        analytics.bookmarked_count = sum(
            1 for item in items if item.get("bookmarked")
        )

        # Date analysis
        dates = []
        for item in items:
            pub = item.get("published_at")
            if pub:
                if isinstance(pub, str):
                    pub = datetime.fromisoformat(pub)
                dates.append(pub)

        if dates:
            analytics.oldest_item = min(dates)
            analytics.newest_item = max(dates)
            analytics.daily_counts = self._daily_counts(dates)

        return analytics

    def _score_buckets(
        self,
        scores: list[float],
    ) -> dict[str, int]:
        """Categorize scores into buckets."""
        buckets = {
            "excellent (0.8-1.0)": 0,
            "good (0.6-0.8)": 0,
            "average (0.4-0.6)": 0,
            "below_avg (0.2-0.4)": 0,
            "poor (0.0-0.2)": 0,
        }
        for score in scores:
            if score >= 0.8:
                buckets["excellent (0.8-1.0)"] += 1
            elif score >= 0.6:
                buckets["good (0.6-0.8)"] += 1
            elif score >= 0.4:
                buckets["average (0.4-0.6)"] += 1
            elif score >= 0.2:
                buckets["below_avg (0.2-0.4)"] += 1
            else:
                buckets["poor (0.0-0.2)"] += 1
        return buckets

    def _daily_counts(
        self,
        dates: list[datetime],
    ) -> dict[str, int]:
        """Count items per day."""
        counts: dict[str, int] = defaultdict(int)
        for date in dates:
            key = date.strftime("%Y-%m-%d")
            counts[key] += 1
        return dict(counts)

    def compare_periods(
        self,
        items: list[dict[str, Any]],
        period1_start: datetime,
        period1_end: datetime,
        period2_start: datetime,
        period2_end: datetime,
    ) -> dict[str, Any]:
        """Compare analytics between two time periods.

        Args:
            items: List of content items.
            period1_start: Start of first period.
            period1_end: End of first period.
            period2_start: Start of second period.
            period2_end: End of second period.

        Returns:
            Comparison dictionary with both periods and changes.
        """
        period1_items = [
            item for item in items
            if self._in_period(item, period1_start, period1_end)
        ]
        period2_items = [
            item for item in items
            if self._in_period(item, period2_start, period2_end)
        ]

        analytics1 = self.analyze(period1_items)
        analytics2 = self.analyze(period2_items)

        return {
            "period1": analytics1.to_dict(),
            "period2": analytics2.to_dict(),
            "changes": {
                "item_count": analytics2.total_items - analytics1.total_items,
                "avg_score": round(
                    analytics2.avg_score - analytics1.avg_score, 4,
                ),
                "unique_domains": analytics2.unique_domains - analytics1.unique_domains,
                "unique_tags": analytics2.unique_tags - analytics1.unique_tags,
            },
        }

    def _in_period(
        self,
        item: dict[str, Any],
        start: datetime,
        end: datetime,
    ) -> bool:
        """Check if an item falls within a time period."""
        pub = item.get("published_at")
        if pub is None:
            return False
        if isinstance(pub, str):
            pub = datetime.fromisoformat(pub)
        return start <= pub <= end
