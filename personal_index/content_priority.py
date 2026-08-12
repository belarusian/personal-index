"""Content priority scoring for personal-index.

Assigns priority levels to content based on multiple factors
including recency, score, interest match, and user engagement.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class PriorityLevel(Enum):
    """Priority level for content items."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    ARCHIVE = "archive"


@dataclass
class PriorityConfig:
    """Configuration for priority scoring."""
    recency_weight: float = 0.2
    score_weight: float = 0.3
    interest_weight: float = 0.3
    engagement_weight: float = 0.2
    critical_threshold: float = 0.8
    high_threshold: float = 0.6
    medium_threshold: float = 0.4
    low_threshold: float = 0.2


@dataclass
class PriorityResult:
    """Result of priority calculation."""
    url: str
    title: str
    priority: PriorityLevel
    score: float
    breakdown: dict[str, float] = field(default_factory=dict)
    factors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "priority": self.priority.value,
            "score": round(self.score, 4),
            "breakdown": {k: round(v, 4) for k, v in self.breakdown.items()},
            "factors": self.factors,
        }


class PriorityCalculator:
    """Calculates content priority based on multiple factors.

    Considers recency, content score, interest match, and
    engagement metrics to determine priority level.
    """

    def __init__(self, config: PriorityConfig | None = None):
        self.config = config or PriorityConfig()

    def calculate(
        self,
        url: str,
        title: str,
        content_score: float = 0.0,
        interest_matches: list[str] | None = None,
        view_count: int = 0,
        days_since_indexed: float = 0.0,
        tags: list[str] | None = None,
    ) -> PriorityResult:
        """Calculate priority for a content item.

        Args:
            url: Content URL.
            title: Content title.
            content_score: Base content score (0-10).
            interest_matches: List of matched interest names.
            view_count: Number of times content has been viewed.
            days_since_indexed: Days since content was indexed.
            tags: Content tags.

        Returns:
            PriorityResult with calculated priority and breakdown.
        """
        factors = []
        breakdown: dict[str, float] = {}

        # Factor 1: Recency score (newer = higher)
        recency_score = self._recency_score(days_since_indexed)
        breakdown["recency"] = recency_score
        if recency_score > 0.7:
            factors.append("recently indexed")

        # Factor 2: Content score (normalized to 0-1)
        score_normalized = min(content_score / 10.0, 1.0)
        breakdown["content_score"] = score_normalized
        if score_normalized > 0.7:
            factors.append("high content score")

        # Factor 3: Interest match
        interest_score = self._interest_score(interest_matches or [])
        breakdown["interest_match"] = interest_score
        if interest_matches:
            factors.append(f"matches interests: {', '.join(interest_matches[:3])}")

        # Factor 4: Engagement
        engagement_score = self._engagement_score(view_count)
        breakdown["engagement"] = engagement_score
        if view_count > 10:
            factors.append(f"high engagement ({view_count} views)")

        # Weighted combination
        total = (
            recency_score * self.config.recency_weight
            + score_normalized * self.config.score_weight
            + interest_score * self.config.interest_weight
            + engagement_score * self.config.engagement_weight
        )

        # Determine priority level
        priority = self._level_for_score(total)

        return PriorityResult(
            url=url,
            title=title,
            priority=priority,
            score=total,
            breakdown=breakdown,
            factors=factors,
        )

    def _recency_score(self, days_since_indexed: float) -> float:
        """Calculate recency score (0-1, higher = more recent).

        Uses exponential decay: score = e^(-days/30)
        """
        import math
        return math.exp(-days_since_indexed / 30.0)

    def _interest_score(self, matches: list[str]) -> float:
        """Calculate interest match score (0-1).

        Score increases with number of matches, capped at 1.0.
        """
        if not matches:
            return 0.0
        # Each match adds 0.25, capped at 1.0
        return min(len(matches) * 0.25, 1.0)

    def _engagement_score(self, view_count: int) -> float:
        """Calculate engagement score (0-1).

        Uses logarithmic scaling: score = log(1 + views) / log(101)
        """
        import math
        if view_count <= 0:
            return 0.0
        return math.log(1 + view_count) / math.log(101)

    def _level_for_score(self, score: float) -> PriorityLevel:
        """Determine priority level from score."""
        if score >= self.config.critical_threshold:
            return PriorityLevel.CRITICAL
        elif score >= self.config.high_threshold:
            return PriorityLevel.HIGH
        elif score >= self.config.medium_threshold:
            return PriorityLevel.MEDIUM
        elif score >= self.config.low_threshold:
            return PriorityLevel.LOW
        else:
            return PriorityLevel.ARCHIVE

    def batch_calculate(
        self,
        items: list[dict[str, Any]],
    ) -> list[PriorityResult]:
        """Calculate priority for multiple items.

        Args:
            items: List of item dicts with keys:
                url, title, content_score, interest_matches,
                view_count, days_since_indexed, tags.

        Returns:
            List of PriorityResult objects sorted by score descending.
        """
        results = []
        for item in items:
            result = self.calculate(
                url=item.get("url", ""),
                title=item.get("title", ""),
                content_score=item.get("content_score", 0.0),
                interest_matches=item.get("interest_matches", []),
                view_count=item.get("view_count", 0),
                days_since_indexed=item.get("days_since_indexed", 0.0),
                tags=item.get("tags", []),
            )
            results.append(result)

        results.sort(key=lambda r: r.score, reverse=True)
        return results

    def get_summary(
        self,
        results: list[PriorityResult],
    ) -> dict[str, int]:
        """Get a summary of priority distribution.

        Args:
            results: List of PriorityResult objects.

        Returns:
            Dict mapping priority level names to counts.
        """
        summary: dict[str, int] = {}
        for result in results:
            level = result.priority.value
            summary[level] = summary.get(level, 0) + 1
        return summary
