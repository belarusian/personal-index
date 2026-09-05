"""Content scoring and ranking engine for personal-index.

Provides algorithms to score content items based on multiple factors
including recency, relevance, user engagement, and content quality.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ScoreFactor(Enum):
    """Factors that contribute to content scoring."""

    RECENCY = "recency"
    RELEVANCE = "relevance"
    ENGAGEMENT = "engagement"
    QUALITY = "quality"
    AUTHORITY = "authority"
    FRESHNESS = "freshness"


@dataclass
class ScoreWeights:
    """Configurable weights for each scoring factor.

    Attributes:
        recency: Weight for how recent the content is (0.0-1.0).
        relevance: Weight for keyword/topic relevance (0.0-1.0).
        engagement: Weight for user engagement signals (0.0-1.0).
        quality: Weight for content quality signals (0.0-1.0).
        authority: Weight for source authority (0.0-1.0).
        freshness: Weight for content freshness (0.0-1.0).
    """

    recency: float = 0.2
    relevance: float = 0.25
    engagement: float = 0.15
    quality: float = 0.15
    authority: float = 0.1
    freshness: float = 0.15

    def normalize(self) -> ScoreWeights:
        """Normalize weights so they sum to 1.0."""
        total = sum([
            self.recency, self.relevance, self.engagement,
            self.quality, self.authority, self.freshness,
        ])
        if total == 0:
            return ScoreWeights()
        return ScoreWeights(
            recency=self.recency / total,
            relevance=self.relevance / total,
            engagement=self.engagement / total,
            quality=self.quality / total,
            authority=self.authority / total,
            freshness=self.freshness / total,
        )


@dataclass
class ContentScore:
    """Result of scoring a content item.

    Attributes:
        total: Overall composite score (0.0-1.0).
        recency: Score for recency factor.
        relevance: Score for relevance factor.
        engagement: Score for engagement factor.
        quality: Score for quality factor.
        authority: Score for authority factor.
        freshness: Score for freshness factor.
        factors: Dict mapping factor names to individual scores.
    """

    total: float = 0.0
    recency: float = 0.0
    relevance: float = 0.0
    engagement: float = 0.0
    quality: float = 0.0
    authority: float = 0.0
    freshness: float = 0.0
    factors: dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert score to dictionary representation."""
        return {
            "total": round(self.total, 4),
            "recency": round(self.recency, 4),
            "relevance": round(self.relevance, 4),
            "engagement": round(self.engagement, 4),
            "quality": round(self.quality, 4),
            "authority": round(self.authority, 4),
            "freshness": round(self.freshness, 4),
            "factors": self.factors,
        }


class ContentScorer:
    """Scores content items based on configurable factors.

    Uses a weighted combination of multiple scoring factors to produce
    a composite score for each content item.
    """

    def __init__(self, weights: ScoreWeights | None = None) -> None:
        self.weights = (weights or ScoreWeights()).normalize()

    def _compute_total(
        self, recency: float, relevance: float, engagement: float,
        quality: float, authority: float, freshness: float,
    ) -> float:
        return (
            self.weights.recency * recency
            + self.weights.relevance * relevance
            + self.weights.engagement * engagement
            + self.weights.quality * quality
            + self.weights.authority * authority
            + self.weights.freshness * freshness
        )

    def _build_score(
        self, total: float, recency: float, relevance: float,
        engagement: float, quality: float, authority: float, freshness: float,
    ) -> ContentScore:
        return ContentScore(
            total=round(total, 4),
            recency=round(recency, 4),
            relevance=round(relevance, 4),
            engagement=round(engagement, 4),
            quality=round(quality, 4),
            authority=round(authority, 4),
            freshness=round(freshness, 4),
            factors={
                "recency": recency, "relevance": relevance,
                "engagement": engagement, "quality": quality,
                "authority": authority, "freshness": freshness,
            },
        )

    def score(
        self,
        *,
        published_at: datetime | None = None,
        updated_at: datetime | None = None,
        keyword_matches: int = 0,
        total_keywords: int = 1,
        view_count: int = 0,
        bookmark_count: int = 0,
        share_count: int = 0,
        word_count: int = 0,
        has_images: bool = False,
        has_code: bool = False,
        domain_authority: float = 0.5,
        is_verified_source: bool = False,
        last_crawled: datetime | None = None,
        change_frequency: str = "monthly",
    ) -> ContentScore:
        """Calculate the composite score for a content item.

        Computes six factor scores, each via a dedicated helper:
          recency   = _score_recency(published_at, updated_at) - exponential
                      decay with a 30-day half-life; naive datetimes are made
                      UTC-aware; the reference date is updated_at or
                      published_at or now.
          relevance = _score_relevance(keyword_matches, total_keywords) - 0.0
                      when total_keywords == 0, else min(1.0, matches/total).
          engagement= _score_engagement(view_count, bookmark_count, share_count)
                      - log1p weighted 0.4/0.4/0.2, capped at log1p(1000).
          quality   = _score_quality(word_count, has_images, has_code) - log1p
                      length scaled to log1p(3000) + 0.1 image bonus + 0.05 code
                      bonus, capped at 1.0.
          authority = _score_authority(domain_authority, is_verified_source) -
                      domain_authority + 0.1 only when verified, capped at 1.0.
          freshness = _score_freshness(last_crawled, change_frequency,
                      updated_at) - 0.5 when last_crawled is None; 1.0 when the
                      frequency is "never"; else 1.0 - 0.5 * age_hours / expected,
                      clamped to [0.0, 1.0].

        total = _compute_total(...) is the weighted sum of the six factors
        using self.weights (normalized in __init__).

        Returns a ContentScore whose total/recency/relevance/engagement/quality/
        authority/freshness are each rounded to 4 places, plus a factors dict
        mapping each factor name to its unrounded value.
        """
        recency = self._score_recency(published_at, updated_at)
        relevance = self._score_relevance(keyword_matches, total_keywords)
        engagement = self._score_engagement(view_count, bookmark_count, share_count)
        quality = self._score_quality(word_count, has_images, has_code)
        authority = self._score_authority(domain_authority, is_verified_source)
        freshness = self._score_freshness(last_crawled, change_frequency, updated_at)
        total = self._compute_total(recency, relevance, engagement, quality, authority, freshness)
        return self._build_score(total, recency, relevance, engagement, quality, authority, freshness)

    def _score_recency(
        self,
        published_at: datetime | None,
        updated_at: datetime | None,
    ) -> float:
        """Score based on how recent the content is.

        Uses exponential decay: newer content scores higher.
        """
        now = datetime.now(timezone.utc)
        date = updated_at or published_at or now
        # Handle naive datetimes by making them UTC-aware
        if date.tzinfo is None:
            date = date.replace(tzinfo=timezone.utc)
        age_days = max(0, (now - date).days)
        # Exponential decay: half-life of 30 days
        return round(math.exp(-math.log(2) * age_days / 30), 4)

    def _score_relevance(
        self,
        keyword_matches: int,
        total_keywords: int,
    ) -> float:
        """Score based on keyword relevance."""
        if total_keywords == 0:
            return 0.0
        return round(min(1.0, keyword_matches / total_keywords), 4)

    def _score_engagement(
        self,
        view_count: int,
        bookmark_count: int,
        share_count: int,
    ) -> float:
        """Score based on engagement signals.

        Uses logarithmic scaling to prevent high-volume items from
        dominating.
        """
        engagement = (
            math.log1p(view_count) * 0.4
            + math.log1p(bookmark_count) * 0.4
            + math.log1p(share_count) * 0.2
        )
        # Normalize to 0-1 range (cap at log1p(1000) ~ 6.9)
        max_engagement = math.log1p(1000)
        return round(min(1.0, engagement / max_engagement), 4)

    def _score_quality(
        self,
        word_count: int,
        has_images: bool,
        has_code: bool,
    ) -> float:
        """Score based on content quality signals."""
        # Longer content tends to be higher quality (diminishing returns)
        length_score = min(1.0, math.log1p(word_count) / math.log1p(3000))
        # Bonus for rich media
        media_bonus = 0.1 if has_images else 0.0
        code_bonus = 0.05 if has_code else 0.0
        return round(min(1.0, length_score + media_bonus + code_bonus), 4)

    def _score_authority(
        self,
        domain_authority: float,
        is_verified_source: bool,
    ) -> float:
        """Score based on source authority.

        Returns ``domain_authority`` unchanged, plus a +0.1 bonus only
        when ``is_verified_source`` is true, capped at 1.0 and rounded
        to 4 places.
        """
        score = domain_authority
        if is_verified_source:
            score = min(1.0, score + 0.1)
        return round(score, 4)

    def _score_freshness(
        self,
        last_crawled: datetime | None,
        change_frequency: str,
        updated_at: datetime | None,
    ) -> float:
        """Score based on content freshness."""
        now = datetime.now(timezone.utc)
        if last_crawled is None:
            return 0.5
        if last_crawled.tzinfo is None:
            last_crawled = last_crawled.replace(tzinfo=timezone.utc)

        age_hours = max(0, (now - last_crawled).total_seconds() / 3600)

        # Expected update intervals by frequency
        frequency_hours: dict[str, float] = {
            "hourly": 1,
            "daily": 24,
            "weekly": 168,
            "monthly": 720,
            "yearly": 8760,
            "never": float("inf"),
        }
        expected = frequency_hours.get(change_frequency, 720)

        if expected == float("inf"):
            return 1.0

        # Score decreases as we exceed expected update interval
        ratio = age_hours / expected
        return round(max(0.0, min(1.0, 1.0 - ratio * 0.5)), 4)

    def score_page(
        self,
        page: Any,
        interest_store: Any = None,
    ) -> ContentScore:
        """Score a CrawledPage using interest matching.

        Reads from the page object (via getattr with defaults):
          content = page.content or "" (empty string when missing),
          word_count = page.word_count or len(content.split()),
          domain_authority = page.domain_authority or 0.5,
          last_crawled = page.crawled_at or None.

        Interest matching (relevance): only when ``interest_store`` is
        truthy, iterates ``interest_store.list_all()`` and, for each
        interest, counts a keyword match for every keyword (str, case-
        insensitive substring of content), every topic (case-insensitive
        substring) and, when ``interest.value`` is non-empty, the value
        itself; each counted candidate increments ``total_keywords`` and
        a match increments ``keyword_matches``.

        Guard path: when ``interest_store`` is falsy the loop is skipped
        entirely, so ``keyword_matches`` stays 0 and ``total_keywords``
        stays 0 (floored to 1 below) -> relevance 0.0.

        Also detects has_code (regex ``<code>``/triple-backtick/def/
        class/import) and has_images (regex ``<img``/png/jpg/gif) from
        the content, then delegates to ``self.score(...)`` with
        ``total_keywords=max(total_keywords, 1)`` so relevance is
        matches/total (0.0 when no matches). Returns the resulting
        ContentScore.
        """
        content = getattr(page, "content", "") or ""
        word_count = getattr(page, "word_count", 0) or len(content.split())
        keyword_matches = 0
        total_keywords = 0
        if interest_store:
            for interest in interest_store.list_all():
                for kw in getattr(interest, "keywords", []):
                    total_keywords += 1
                    if isinstance(kw, str) and kw.lower() in content.lower():
                        keyword_matches += 1
                for topic in getattr(interest, "topics", []):
                    total_keywords += 1
                    if topic.lower() in content.lower():
                        keyword_matches += 1
                if getattr(interest, "value", ""):
                    total_keywords += 1
                    if interest.value.lower() in content.lower():
                        keyword_matches += 1
        has_code = bool(re.search(r"<code>|\`\`\`|def |class |import ", content))
        has_images = bool(re.search(r"<img|\.png|\.jpg|\.gif", content))
        return self.score(
            keyword_matches=keyword_matches,
            total_keywords=max(total_keywords, 1),
            word_count=word_count,
            has_images=has_images,
            has_code=has_code,
            domain_authority=getattr(page, "domain_authority", 0.5),
            last_crawled=getattr(page, "crawled_at", None),
        )

    def rank(
        self,
        items: list[dict[str, Any]],
        *,
        limit: int = 10,
    ) -> list[tuple[dict[str, Any], ContentScore]]:
        """Rank a list of content items by score.

        Args:
            items: List of content item dicts with scoring fields.
            limit: Maximum number of items to return.

        Returns:
            List of (item, score) tuples sorted by score descending.
        """
        scored = []
        for item in items:
            score = self.score(**item)
            scored.append((item, score))
        scored.sort(key=lambda x: x[1].total, reverse=True)
        return scored[:limit]
