"""Content scoring module for ranking indexed items by relevance and quality."""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any


@dataclass
class ScoreFactors:
    """Factors used to compute a content score."""

    text_length: int = 0
    keyword_density: float = 0.0
    tag_count: int = 0
    bookmark_count: int = 0
    visit_count: int = 0
    freshness_days: float = 0.0
    domain_reputation: float = 0.5
    content_type_score: float = 0.5
    link_count: int = 0
    image_count: int = 0
    has_summary: bool = False
    has_tags: bool = False


@dataclass
class ContentScore:
    """Result of scoring a piece of content."""

    total_score: float = 0.0
    text_quality: float = 0.0
    engagement: float = 0.0
    freshness: float = 0.0
    authority: float = 0.0
    completeness: float = 0.0
    factors: ScoreFactors = field(default_factory=ScoreFactors)

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_score": round(self.total_score, 4),
            "text_quality": round(self.text_quality, 4),
            "engagement": round(self.engagement, 4),
            "freshness": round(self.freshness, 4),
            "authority": round(self.authority, 4),
            "completeness": round(self.completeness, 4),
        }


class ContentScorer:
    """Scores content items based on multiple quality and relevance factors."""

    # Weights for each scoring dimension
    WEIGHT_TEXT_QUALITY = 0.25
    WEIGHT_ENGAGEMENT = 0.25
    WEIGHT_FRESHNESS = 0.15
    WEIGHT_AUTHORITY = 0.20
    WEIGHT_COMPLETENESS = 0.15

    # Text quality thresholds
    MIN_GOOD_LENGTH = 100
    OPTIMAL_LENGTH = 1000
    MAX_LENGTH = 50000

    def __init__(self, weights: dict[str, float] | None = None):
        if weights:
            self.WEIGHT_TEXT_QUALITY = weights.get("text_quality", self.WEIGHT_TEXT_QUALITY)
            self.WEIGHT_ENGAGEMENT = weights.get("engagement", self.WEIGHT_ENGAGEMENT)
            self.WEIGHT_FRESHNESS = weights.get("freshness", self.WEIGHT_FRESHNESS)
            self.WEIGHT_AUTHORITY = weights.get("authority", self.WEIGHT_AUTHORITY)
            self.WEIGHT_COMPLETENESS = weights.get("completeness", self.WEIGHT_COMPLETENESS)

    def score(self, factors: ScoreFactors) -> ContentScore:
        """Compute a content score from the given factors."""
        text_quality = self._score_text_quality(factors)
        engagement = self._score_engagement(factors)
        freshness = self._score_freshness(factors)
        authority = self._score_authority(factors)
        completeness = self._score_completeness(factors)

        total = (
            text_quality * self.WEIGHT_TEXT_QUALITY
            + engagement * self.WEIGHT_ENGAGEMENT
            + freshness * self.WEIGHT_FRESHNESS
            + authority * self.WEIGHT_AUTHORITY
            + completeness * self.WEIGHT_COMPLETENESS
        )

        return ContentScore(
            total_score=total,
            text_quality=text_quality,
            engagement=engagement,
            freshness=freshness,
            authority=authority,
            completeness=completeness,
            factors=factors,
        )

    def _score_text_quality(self, factors: ScoreFactors) -> float:
        """Score based on text length and keyword density."""
        length_score = self._sigmoid_length(factors.text_length)
        density_score = min(factors.keyword_density * 10, 1.0)
        return 0.7 * length_score + 0.3 * density_score

    def _sigmoid_length(self, length: int) -> float:
        """Sigmoid scoring for text length."""
        if length <= 0:
            return 0.0
        k = math.log(2) / self.OPTIMAL_LENGTH
        return 1.0 / (1.0 + math.exp(-k * (length - self.OPTIMAL_LENGTH)))

    def _score_engagement(self, factors: ScoreFactors) -> float:
        """Score based on bookmarks, visits, and tags."""
        bookmark_score = min(factors.bookmark_count / 5, 1.0)
        visit_score = min(math.log1p(factors.visit_count) / 3, 1.0)
        tag_score = min(factors.tag_count / 10, 1.0)
        return 0.4 * bookmark_score + 0.35 * visit_score + 0.25 * tag_score

    def _score_freshness(self, factors: ScoreFactors) -> float:
        """Score based on content age."""
        if factors.freshness_days <= 0:
            return 1.0
        # Exponential decay: half-life of 30 days
        half_life = 30.0
        return math.exp(-math.log(2) * factors.freshness_days / half_life)

    def _score_authority(self, factors: ScoreFactors) -> float:
        """Score based on domain reputation and content type."""
        return 0.6 * factors.domain_reputation + 0.4 * factors.content_type_score

    def _score_completeness(self, factors: ScoreFactors) -> float:
        """Score based on how complete the indexed item is."""
        has_summary = 1.0 if factors.has_summary else 0.0
        has_tags = 1.0 if factors.has_tags else 0.0
        link_bonus = min(factors.link_count / 20, 0.5)
        image_bonus = min(factors.image_count / 10, 0.3)
        return 0.3 * has_summary + 0.3 * has_tags + 0.2 * link_bonus + 0.2 * image_bonus

    def score_batch(self, factors_list: list[ScoreFactors]) -> list[ContentScore]:
        """Score multiple content items."""
        return [self.score(f) for f in factors_list]

    def rank(self, scores: list[ContentScore], descending: bool = True) -> list[tuple[int, ContentScore]]:
        """Rank scored items, returning (original_index, score) tuples."""
        indexed = list(enumerate(scores))
        indexed.sort(key=lambda x: x[1].total_score, reverse=descending)
        return indexed
