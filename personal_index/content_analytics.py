"""Content analytics for personal-index.

Provides engagement scoring, categorization, and analytics reports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class EngagementScore:
    """Engagement score for a piece of content."""

    view_count: int = 0
    bookmark_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    avg_time_on_page: float = 0.0
    total_score: float = 0.0

    def __post_init__(self) -> None:
        """Calculate total engagement score from weighted components."""
        self.total_score = (
            self.view_count * 0.1
            + self.bookmark_count * 0.3
            + self.share_count * 0.5
            + self.comment_count * 0.4
            + self.avg_time_on_page * 0.01
        )

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_score": round(self.total_score, 2),
            "view_count": self.view_count,
            "bookmark_count": self.bookmark_count,
            "share_count": self.share_count,
            "comment_count": self.comment_count,
            "avg_time_on_page": round(self.avg_time_on_page, 2),
        }


@dataclass
class ContentCategory:
    """A category of content with count and percentage."""

    name: str
    count: int
    total: int = 0
    percentage: float = 0.0

    def __post_init__(self) -> None:
        if self.total > 0:
            self.percentage = (self.count / self.total) * 100

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "count": self.count,
            "total": self.total,
            "percentage": round(self.percentage, 2),
        }


@dataclass
class AnalyticsReport:
    """Complete analytics report for content."""

    total_items: int = 0
    total_views: int = 0
    total_bookmarks: int = 0
    total_shares: int = 0
    avg_engagement_score: float = 0.0
    top_categories: list[ContentCategory] = field(default_factory=list)
    top_engaged: list[dict] = field(default_factory=list)
    engagement_distribution: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "total_items": self.total_items,
            "total_views": self.total_views,
            "total_bookmarks": self.total_bookmarks,
            "total_shares": self.total_shares,
            "avg_engagement_score": round(self.avg_engagement_score, 2),
            "top_categories": [c.to_dict() for c in self.top_categories],
            "top_engaged": self.top_engaged,
            "engagement_distribution": self.engagement_distribution,
        }


class ContentAnalytics:
    """Analyzes content engagement and categorization."""

    def __init__(self) -> None:
        self._items: list[dict] = []

    def add_item(self, item: dict) -> None:
        """Add a content item for analysis."""
        self._items.append(item)

    def analyze_engagement(self) -> list[EngagementScore]:
        """Calculate engagement scores for all items."""
        scores = []
        for item in self._items:
            score = EngagementScore(
                view_count=item.get("view_count", 0),
                bookmark_count=item.get("bookmark_count", 0),
                share_count=item.get("share_count", 0),
                comment_count=item.get("comment_count", 0),
                avg_time_on_page=item.get("avg_time_on_page", 0),
            )
            scores.append(score)
        return scores

    def categorize(self) -> list[ContentCategory]:
        """Categorize content items."""
        categories: dict[str, int] = {}
        for item in self._items:
            cat = item.get("category", "Uncategorized")
            categories[cat] = categories.get(cat, 0) + 1

        total = len(self._items)
        result = []
        for name, count in sorted(categories.items(), key=lambda x: -x[1]):
            result.append(ContentCategory(name=name, count=count, total=total))
        return result

    def generate_report(self, top_n: int = 10) -> AnalyticsReport:
        """Generate a full analytics report."""
        if not self._items:
            return AnalyticsReport()

        scores = self.analyze_engagement()
        categories = self.categorize()

        # Build engagement distribution
        distribution = {"low": 0, "medium": 0, "high": 0}
        for score in scores:
            if score.total_score < 5:
                distribution["low"] += 1
            elif score.total_score < 20:
                distribution["medium"] += 1
            else:
                distribution["high"] += 1

        # Top engaged items
        scored_items = []
        for item, score in zip(self._items, scores):
            scored_items.append({
                "url": item.get("url", ""),
                "title": item.get("title", ""),
                "engagement_score": round(score.total_score, 2),
            })
        scored_items.sort(key=lambda x: -x["engagement_score"])
        top_engaged = scored_items[:top_n]

        total_views = sum(item.get("view_count", 0) for item in self._items)
        total_bookmarks = sum(item.get("bookmark_count", 0) for item in self._items)
        total_shares = sum(item.get("share_count", 0) for item in self._items)
        avg_score = sum(s.total_score for s in scores) / len(scores) if scores else 0

        return AnalyticsReport(
            total_items=len(self._items),
            total_views=total_views,
            total_bookmarks=total_bookmarks,
            total_shares=total_shares,
            avg_engagement_score=avg_score,
            top_categories=categories[:5],
            top_engaged=top_engaged,
            engagement_distribution=distribution,
        )
