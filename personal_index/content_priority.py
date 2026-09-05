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

    @classmethod
    def from_score(cls, score: float) -> PriorityLevel:
        """Determine priority level from a normalized score (0-1)."""
        if score >= 0.8:
            return cls.CRITICAL
        elif score >= 0.6:
            return cls.HIGH
        elif score >= 0.4:
            return cls.MEDIUM
        elif score > 0:
            return cls.LOW
        else:
            return cls.ARCHIVE


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

    def _add_factor(self, factors: list[str], breakdown: dict[str, float], name: str, value: float, label: str, threshold: float = 0.7) -> None:
        breakdown[name] = value
        if value > threshold:
            factors.append(label)

    def _weighted_total(self, r: float, s: float, i: float, e: float) -> float:
        return (r * self.config.recency_weight + s * self.config.score_weight +
                i * self.config.interest_weight + e * self.config.engagement_weight)

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

        Computes four sub-factors, each recorded in ``breakdown``:

        - ``recency``: ``_recency_score(days_since_indexed)`` = e^(-days/30);
          added to ``factors`` as "recently indexed" when > 0.7.
        - ``content_score``: ``content_score / 10.0`` clamped to [0, 1];
          added to ``factors`` as "high content score" when > 0.7.
        - ``interest_match``: ``_interest_score(interest_matches or [])``;
          when ``interest_matches`` is non-empty, a "matches interests: ..."
          factor (first 3) is appended.
        - ``engagement``: ``_engagement_score(view_count)``; a "high
          engagement (N views)" factor is appended when ``view_count > 10``.

        The weighted total is ``_weighted_total(recency, content_score,
        interest_match, engagement)`` using the ``PriorityConfig`` weights
        (recency 0.2, score 0.3, interest 0.3, engagement 0.2).

        Returns:
            A ``PriorityResult`` with ``url``, ``title``, ``priority``
            (``_level_for_score(total)`` against the config thresholds),
            ``score`` (the weighted total), ``breakdown`` and ``factors``.
        """
        factors: list[str] = []
        breakdown: dict[str, float] = {}

        recency = self._recency_score(days_since_indexed)
        self._add_factor(factors, breakdown, "recency", recency, "recently indexed")

        score_n = min(max(content_score / 10.0, 0.0), 1.0)
        self._add_factor(factors, breakdown, "content_score", score_n, "high content score")

        interest = self._interest_score(interest_matches or [])
        breakdown["interest_match"] = interest
        if interest_matches:
            factors.append(f"matches interests: {', '.join(interest_matches[:3])}")

        engagement = self._engagement_score(view_count)
        breakdown["engagement"] = engagement
        if view_count > 10:
            factors.append(f"high engagement ({view_count} views)")

        total = self._weighted_total(recency, score_n, interest, engagement)

        return PriorityResult(
            url=url, title=title, priority=self._level_for_score(total),
            score=total, breakdown=breakdown, factors=factors,
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

        Uses logarithmic scaling: score = log(1 + views) / log(101),
        capped at 1.0 so the score saturates at 100+ views and stays
        within the documented 0-1 range (matching _interest_score).
        """
        import math
        if view_count <= 0:
            return 0.0
        return min(1.0, math.log(1 + view_count) / math.log(101))

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
            A dict mapping each ``PriorityLevel.value`` that is PRESENT in
            ``results`` to the number of results at that level. Levels with no
            matching result are OMITTED (not present as a zero-valued key), and
            an empty ``results`` list returns ``{}``.
        """
        summary: dict[str, int] = {}
        for result in results:
            level = result.priority.value
            summary[level] = summary.get(level, 0) + 1
        return summary
