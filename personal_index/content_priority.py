"""Content priority scoring - score content importance."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Any, Dict, List

logger = logging.getLogger(__name__)


class PriorityLevel(str, Enum):
    """Priority levels for content."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"

    @property
    def numeric_value(self) -> int:
        """Numeric value for ordering."""
        return {
            "critical": 4,
            "high": 3,
            "medium": 2,
            "low": 1,
        }.get(self.value, 0)

    def __gt__(self, other: "PriorityLevel") -> bool:
        """Compare priority levels (greater than)."""
        return self.numeric_value > other.numeric_value

    def __lt__(self, other: "PriorityLevel") -> bool:
        """Compare priority levels (less than)."""
        return self.numeric_value < other.numeric_value

    @classmethod
    def from_score(cls, score: float) -> "PriorityLevel":
        """Convert a numeric score to a priority level."""
        if score >= 0.8:
            return cls.CRITICAL
        elif score >= 0.6:
            return cls.HIGH
        elif score >= 0.3:
            return cls.MEDIUM
        else:
            return cls.LOW


@dataclass
class PriorityScore:
    """Detailed priority score breakdown."""

    total: float
    relevance: float
    freshness: float
    authority: float
    engagement: float
    topical: float

    @property
    def level(self) -> PriorityLevel:
        """Get the priority level for this score."""
        return PriorityLevel.from_score(self.total)

    def __gt__(self, other: "PriorityScore") -> bool:
        """Compare priority levels (greater than)."""
        return self.total > other.total

    def __lt__(self, other: "PriorityScore") -> bool:
        """Compare priority levels (less than)."""
        return self.total < other.total

    def __ge__(self, other: "PriorityScore") -> bool:
        """Compare priority scores (greater or equal)."""
        return self.total >= other.total

    def __le__(self, other: "PriorityScore") -> bool:
        """Compare priority scores (less or equal)."""
        return self.total <= other.total


@dataclass
class ContentPriority:
    """A content item with its priority score."""

    score: PriorityScore
    url: str = ""
    title: str = ""
    metadata: dict = field(default_factory=dict, compare=False)

    def __gt__(self, other: "ContentPriority") -> bool:
        """Compare priority levels (greater than)."""
        return self.score.total > other.score.total

    def __lt__(self, other: "ContentPriority") -> bool:
        """Compare priority levels (less than)."""
        return self.score.total < other.score.total

    def __ge__(self, other: "ContentPriority") -> bool:
        """Compare priority scores (greater or equal)."""
        return self.score.total >= other.score.total

    def __le__(self, other: "ContentPriority") -> bool:
        """Compare priority scores (less or equal)."""
        return self.score.total <= other.score.total


@dataclass
class PriorityConfig:
    """Configuration for priority scoring weights."""

    relevance_weight: float = 0.3
    freshness_weight: float = 0.2
    authority_weight: float = 0.2
    engagement_weight: float = 0.15
    topical_weight: float = 0.15


class PriorityScorer:
    """Score content importance based on multiple factors.

    Evaluates content based on relevance (keyword matching),
    freshness (publication date), authority (domain trust),
    engagement (views, likes, shares), and topical relevance
    (user interest alignment).
    """

    def __init__(self, config: PriorityConfig | None = None) -> None:
        """Initialize PriorityScorer with optional config.

        Args:
            config: Priority scoring configuration.
        """
        self.config = config or PriorityConfig()

    def score(self, content: dict[str, Any]) -> PriorityScore:
        """Score a single content item.

        Args:
            content: Dict with content metadata.

        Returns:
            PriorityScore with total and breakdown.
        """
        relevance = self._score_relevance(content)
        freshness = self._score_freshness(content)
        authority = self._score_authority(content)
        engagement = self._score_engagement(content)
        topical = self._score_topical(content)

        total = (
            relevance * self.config.relevance_weight
            + freshness * self.config.freshness_weight
            + authority * self.config.authority_weight
            + engagement * self.config.engagement_weight
            + topical * self.config.topical_weight
        )

        return PriorityScore(
            total=round(total, 4),
            relevance=round(relevance, 4),
            freshness=round(freshness, 4),
            authority=round(authority, 4),
            engagement=round(engagement, 4),
            topical=round(topical, 4),
        )

    def score_batch(self, items: list[dict[str, Any]]) -> list[PriorityScore]:
        """Score multiple content items.

        Args:
            items: List of content dicts.

        Returns:
            List of PriorityScore objects.
        """
        return [self.score(item) for item in items]

    def rank(
        self, items: list[dict[str, Any]]
    ) -> list[ContentPriority]:
        """Score and rank content items by priority.

        Args:
            items: List of content dicts.

        Returns:
            List of ContentPriority sorted by score descending.
        """
        priorities: list[ContentPriority] = []
        for item in items:
            score = self.score(item)
            priorities.append(
                ContentPriority(
                    score=score,
                    url=item.get("url", ""),
                    title=item.get("title", ""),
                    metadata={k: v for k, v in item.items() if k not in ("url", "title")},
                )
            )
        priorities.sort(key=lambda p: p.score.total, reverse=True)
        return priorities

    def _score_relevance(self, content: dict[str, Any]) -> float:
        """Score based on keyword relevance (0-1)."""
        keywords = content.get("keywords", [])
        if not keywords:
            return 0.1

        text = (
            (content.get("title", "") or "")
            + " "
            + (content.get("content", "") or "")
        ).lower()

        if not text:
            return 0.0

        matches = sum(1 for kw in keywords if kw.lower() in text)
        return min(matches / max(len(keywords), 1), 1.0)

    def _score_freshness(self, content: dict[str, Any]) -> float:
        """Score based on content freshness (0-1).

        Recent content scores higher. Content older than 1 year
        gets minimal freshness score.
        """
        date_str = content.get("published_date")
        if not date_str:
            return 0.3  # Default for unknown dates

        try:
            if isinstance(date_str, str):
                published = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            else:
                published = date_str
        except (ValueError, TypeError):
            return 0.3

        now = datetime.now(timezone.utc)
        if published.tzinfo is None:
            published = published.replace(tzinfo=timezone.utc)

        age_days = (now - published).total_seconds() / 86400

        if age_days < 0:
            return 1.0  # Future-dated content

        # Exponential decay: half-life of 30 days
        freshness = max(0.0, 2 ** (-age_days / 30))
        return min(freshness, 1.0)

    def _score_authority(self, content: dict[str, Any]) -> float:
        """Score based on domain authority (0-1)."""
        authority = content.get("domain_authority")
        if authority is None:
            # Infer from URL patterns
            url = content.get("url", "")
            authority = self._estimate_domain_authority(url)

        return min(max(authority / 100, 0.0), 1.0)

    def _estimate_domain_authority(self, url: str) -> float:
        """Estimate domain authority from URL patterns."""
        known_high_authority = {
            "wikipedia.org", "github.com", "stackoverflow.com",
            "medium.com", "nytimes.com", "bbc.com", "reuters.com",
            "arxiv.org", "nature.com", "ieee.org",
        }
        known_medium = {
            "dev.to", "hashnode.com", "substack.com",
            "linkedin.com", "twitter.com",
        }

        domain = ""
        with suppress(IndexError):
            domain = url.split("//")[-1].split("/")[0].split(":")[0]

        if domain in known_high_authority:
            return 85
        elif domain in known_medium:
            return 60
        elif domain:
            return 30  # Default for unknown domains
        return 10

    def _score_engagement(self, content: dict[str, Any]) -> float:
        """Score based on engagement metrics (0-1)."""
        views = content.get("views", 0) or 0
        likes = content.get("likes", 0) or 0
        shares = content.get("shares", 0) or 0

        if views == 0 and likes == 0 and shares == 0:
            return 0.1  # Default for no engagement data

        # Normalize: log scale to handle wide ranges
        view_score = min(math.log1p(views) / math.log1p(10000), 1.0)
        like_score = min(math.log1p(likes) / math.log1p(1000), 1.0)
        share_score = min(math.log1p(shares) / math.log1p(500), 1.0)

        # Weighted average
        engagement = (
            view_score * 0.4
            + like_score * 0.35
            + share_score * 0.25
        )
        return min(engagement, 1.0)

    def _score_topical(self, content: dict[str, Any]) -> float:
        """Score based on topical relevance to user interests (0-1)."""
        user_interests = content.get("user_interests", [])
        if not user_interests:
            return 0.5  # Neutral when no interests defined

        tags = [t.lower() for t in (content.get("tags", []) or [])]
        title = (content.get("title", "") or "").lower()
        content_text = (content.get("content", "") or "").lower()

        interests_lower = [i.lower() for i in user_interests]
        matches: float = 0.0

        for interest in interests_lower:
            # Check tags
            if interest in tags:
                matches += 2  # Tags are strong signals
            # Check title
            elif interest in title:
                matches += 1.5
            # Check content
            elif interest in content_text:
                matches += 1

        if not interests_lower:
            return 0.5

        max_possible = len(interests_lower) * 2
        return min(matches / max(max_possible, 1), 1.0)


class PriorityFilter:
    """Filter and sort content by priority level."""

    def __init__(self, scorer: PriorityScorer | None = None) -> None:
        """Initialize PriorityScorer with optional config.

        Args:
            config: Priority scoring configuration.
        """
        self.scorer = scorer or PriorityScorer()

    def filter_by_level(
        self,
        items: list[dict[str, Any]],
        min_level: PriorityLevel,
    ) -> list[ContentPriority]:
        """Filter items to only those meeting minimum priority level.

        Args:
            items: List of content dicts.
            min_level: Minimum priority level to include.

        Returns:
            List of ContentPriority items meeting the threshold.
        """
        ranked = self.scorer.rank(items)
        return [
            p for p in ranked
            if p.score.level.numeric_value >= min_level.numeric_value
        ]

    def get_top_n(
        self,
        items: list[dict[str, Any]],
        n: int = 10,
    ) -> list[ContentPriority]:
        """Get top N highest priority content items.

        Args:
            items: List of content dicts.
            n: Number of items to return.

        Returns:
            List of top N ContentPriority items.
        """
        ranked = self.scorer.rank(items)
        return ranked[:n]

    def group_by_level(
        self, items: list[dict[str, Any]]
    ) -> dict[PriorityLevel, list[ContentPriority]]:
        """Group items by their priority level.

        Args:
            items: List of content dicts.

        Returns:
            Dict mapping PriorityLevel to list of ContentPriority items.
        """
        ranked = self.scorer.rank(items)
        groups: dict[PriorityLevel, list[ContentPriority]] = {
            level: [] for level in PriorityLevel
        }
        for item in ranked:
            groups[item.score.level].append(item)
        return groups
# Convenience functions for backward compatibility


def calculate_priority(item_id: str, content_text: str | None = None) -> float:
    """Calculate priority score for an item.

    Args:
        item_id: ID of the item.
        content_text: Optional content text to analyze.

    Returns:
        Priority score as a float.
    """
    scorer = PriorityScorer()
    content_data = {"url": item_id, "title": item_id}
    if content_text:
        content_data["content"] = content_text
    score = scorer.score(content_data)
    return score.total


def sort_by_priority(items: List[str], scores: Dict[str, float] | None = None) -> List[str]:
    """Sort items by priority score.

    Args:
        items: List of item IDs to sort.
        scores: Optional dict mapping item IDs to scores.

    Returns:
        Items sorted by priority (highest first).
    """
    if scores is None:
        scorer = PriorityScorer()
        scores = {}
        for item in items:
            content_data = {"url": item, "title": item}
            score_obj = scorer.score(content_data)
            scores[item] = score_obj.total
    
    return sorted(items, key=lambda x: scores.get(x, 0.0), reverse=True)
