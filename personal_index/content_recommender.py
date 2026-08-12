"""Content recommendation engine for personal-index.

Recommends related content based on keyword overlap, tag similarity,
and interest matching scores.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Recommendation:
    """A content recommendation with score and reason."""
    url: str
    title: str
    score: float
    reason: str
    matching_keywords: list[str] = field(default_factory=list)
    matching_tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "score": round(self.score, 4),
            "reason": self.reason,
            "matching_keywords": self.matching_keywords,
            "matching_tags": self.matching_tags,
        }


def _extract_keywords(text: str) -> set[str]:
    """Extract keywords from text."""
    if not text:
        return set()
    words = re.findall(r'[a-z0-9]+', text.lower())
    stopwords = frozenset({
        "a", "an", "the", "and", "or", "but", "in", "on", "at", "to",
        "for", "of", "with", "by", "is", "it", "as", "be", "are", "was",
        "were", "this", "that", "from", "not", "no", "do", "does", "did",
        "has", "have", "had", "will", "would", "could", "should", "may",
        "might", "can", "shall", "its", "he", "she", "we", "they", "i",
        "me", "my", "our", "your", "his", "her", "their", "what", "which",
        "who", "when", "where", "how", "all", "each", "every", "both",
        "few", "more", "most", "other", "some", "such", "than", "too",
        "very", "just", "about", "above", "after", "again", "also", "any",
    })
    return {w for w in words if w not in stopwords and len(w) > 2}


@dataclass
class ContentItem:
    """A content item for recommendation purposes."""
    url: str
    title: str
    content: str = ""
    keywords: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    score: float = 0.0

    @property
    def all_keywords(self) -> set[str]:
        """Get all keywords including those extracted from content."""
        kw = set(self.keywords)
        kw.update(_extract_keywords(self.content))
        kw.update(_extract_keywords(self.title))
        return kw


class Recommender:
    """Content recommendation engine.

    Recommends content items based on keyword overlap, tag similarity,
    and existing scores.
    """

    def __init__(self, min_score: float = 0.1):
        self.min_score = min_score
        self._items: list[ContentItem] = []

    def add_item(self, item: ContentItem) -> None:
        """Add a content item to the recommendation pool."""
        self._items.append(item)

    def add_items(self, items: list[ContentItem]) -> None:
        """Add multiple content items."""
        self._items.extend(items)

    def _keyword_overlap_score(self, a: ContentItem, b: ContentItem) -> tuple[float, list[str]]:
        """Calculate keyword overlap between two items."""
        keywords_a = a.all_keywords
        keywords_b = b.all_keywords
        if not keywords_a or not keywords_b:
            return 0.0, []
        common = keywords_a & keywords_b
        # Jaccard-like similarity
        union = keywords_a | keywords_b
        score = len(common) / len(union) if union else 0.0
        return score, sorted(common)

    def _tag_similarity_score(self, a: ContentItem, b: ContentItem) -> tuple[float, list[str]]:
        """Calculate tag similarity between two items."""
        tags_a = set(a.tags)
        tags_b = set(b.tags)
        if not tags_a or not tags_b:
            return 0.0, []
        common = tags_a & tags_b
        union = tags_a | tags_b
        score = len(common) / len(union) if union else 0.0
        return score, sorted(common)

    def recommend(
        self,
        seed: ContentItem,
        top_n: int = 5,
        keyword_weight: float = 0.6,
        tag_weight: float = 0.3,
        score_weight: float = 0.1,
    ) -> list[Recommendation]:
        """Generate recommendations based on a seed content item.

        Args:
            seed: The content item to find recommendations for.
            top_n: Number of recommendations to return.
            keyword_weight: Weight for keyword overlap scoring.
            tag_weight: Weight for tag similarity scoring.
            score_weight: Weight for existing content score.

        Returns:
            List of Recommendation objects sorted by score.
        """
        if not self._items:
            return []

        candidates: list[Recommendation] = []
        for item in self._items:
            if item.url == seed.url:
                continue

            kw_score, kw_common = self._keyword_overlap_score(seed, item)
            tag_score, tag_common = self._tag_similarity_score(seed, item)

            # Normalize existing score to 0-1 range
            norm_score = min(item.score / 10.0, 1.0) if item.score > 0 else 0.0

            combined = (
                kw_score * keyword_weight
                + tag_score * tag_weight
                + norm_score * score_weight
            )

            if combined >= self.min_score:
                reasons = []
                if kw_common:
                    reasons.append(f"keywords: {', '.join(kw_common[:5])}")
                if tag_common:
                    reasons.append(f"tags: {', '.join(tag_common)}")
                if not reasons:
                    reasons.append("score-based")

                candidates.append(Recommendation(
                    url=item.url,
                    title=item.title,
                    score=combined,
                    reason="; ".join(reasons),
                    matching_keywords=kw_common,
                    matching_tags=tag_common,
                ))

        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:top_n]

    def recommend_for_keywords(
        self,
        keywords: list[str],
        top_n: int = 5,
    ) -> list[Recommendation]:
        """Recommend content items matching given keywords.

        Args:
            keywords: Keywords to match against.
            top_n: Number of recommendations to return.

        Returns:
            List of Recommendation objects.
        """
        keyword_set = set(kw.lower() for kw in keywords if kw)
        if not keyword_set:
            return []

        candidates: list[Recommendation] = []
        for item in self._items:
            item_keywords = item.all_keywords
            common = keyword_set & item_keywords
            if common:
                # Score based on fraction of query keywords matched
                score = len(common) / len(keyword_set)
                if score >= self.min_score:
                    candidates.append(Recommendation(
                        url=item.url,
                        title=item.title,
                        score=score,
                        reason=f"matched keywords: {', '.join(sorted(common))}",
                        matching_keywords=sorted(common),
                    ))

        candidates.sort(key=lambda r: r.score, reverse=True)
        return candidates[:top_n]

    def clear(self) -> None:
        """Clear all items from the recommendation pool."""
        self._items.clear()

    @property
    def item_count(self) -> int:
        """Number of items in the recommendation pool."""
        return len(self._items)
