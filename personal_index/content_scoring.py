"""Content scoring module for ranking indexed content by quality."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of content quality scores."""

    total_score: float = 0.0
    content_length_score: float = 0.0
    keyword_density_score: float = 0.0
    heading_score: float = 0.0
    link_score: float = 0.0
    image_score: float = 0.0
    readability_score: float = 0.0
    freshness_score: float = 0.0


class ContentScorer:
    """Multi-factor content quality scorer.

    Evaluates content based on length, keyword density, heading structure,
    link quality, image presence, readability, and freshness.
    """

    DEFAULT_WEIGHTS = {
        "content_length": 0.25,
        "keyword_density": 0.20,
        "headings": 0.15,
        "links": 0.10,
        "images": 0.10,
        "readability": 0.15,
        "freshness": 0.05,
    }

    def __init__(self, weights: dict[str, float] | None = None) -> None:
        """Initialize scorer with optional custom weights.

        Args:
            weights: Override default scoring weights. Must sum to ~1.0.
        """
        self.weights = dict(weights) if weights else dict(self.DEFAULT_WEIGHTS)

    def score(self, content: dict[str, Any]) -> tuple[float, ScoreBreakdown]:
        """Score a content item based on multiple factors.

        Args:
            content: Dict with keys like 'text', 'keywords', 'headings',
                     'links', 'images', 'freshness_score'.

        Returns:
            Tuple of (total_score, ScoreBreakdown).
        """
        breakdown = ScoreBreakdown()

        breakdown.content_length_score = self._score_content_length(content)
        breakdown.keyword_density_score = self._score_keyword_density(content)
        breakdown.heading_score = self._score_headings(content)
        breakdown.link_score = self._score_links(content)
        breakdown.image_score = self._score_images(content)
        breakdown.readability_score = self._score_readability(content)
        breakdown.freshness_score = self._score_freshness(content)

        breakdown.total_score = (
            breakdown.content_length_score * self.weights["content_length"]
            + breakdown.keyword_density_score * self.weights["keyword_density"]
            + breakdown.heading_score * self.weights["headings"]
            + breakdown.link_score * self.weights["links"]
            + breakdown.image_score * self.weights["images"]
            + breakdown.readability_score * self.weights["readability"]
            + breakdown.freshness_score * self.weights["freshness"]
        )

        return breakdown.total_score, breakdown

    def _score_content_length(self, content: dict[str, Any]) -> float:
        """Score based on content length (0-1).

        Optimal range: 300-2000 words. Penalizes very short and very long content.
        """
        text = content.get("text", "") or content.get("content", "")
        word_count = len(text.split()) if text else 0
        if word_count < 100:
            return min(word_count / 100, 0.5)
        elif word_count < 300:
            return 0.5 + (word_count - 100) / 400
        elif word_count <= 2000:
            return 1.0
        else:
            return max(0.5, 1.0 - (word_count - 2000) / 5000)

    def _score_keyword_density(self, content: dict[str, Any]) -> float:
        """Score based on keyword density (0-1).

        Higher score when more provided keywords appear in the text.
        """
        keywords = content.get("keywords", [])
        if not keywords:
            return 0.5
        text = (content.get("text", "") or content.get("content", "")).lower()
        if not text:
            return 0.0
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return min(matches / max(len(keywords), 1), 1.0)

    def _score_headings(self, content: dict[str, Any]) -> float:
        """Score based on heading structure (0-1).

        Rewards well-structured content with heading hierarchy.
        """
        headings = content.get("headings", [])
        if not headings:
            return 0.0
        score = min(len(headings) / 5, 1.0)
        has_h1 = any(h.startswith("h1") for h in headings)
        if has_h1:
            score = min(score + 0.2, 1.0)
        return score

    def _score_links(self, content: dict[str, Any]) -> float:
        """Score based on link quality (0-1).

        Penalizes pages with too many links (potential spam).
        """
        links = content.get("links", [])
        if not links:
            return 0.3
        if len(links) > 100:
            return 0.2
        return min(len(links) / 20, 1.0)

    def _score_images(self, content: dict[str, Any]) -> float:
        """Score based on image presence and alt text (0-1).

        Rewards images with descriptive alt text.
        """
        images = content.get("images", [])
        if not images:
            return 0.3
        with_alt = sum(1 for img in images if img.get("alt", "").strip())
        return min(with_alt / max(len(images), 1), 1.0)

    def _score_readability(self, content: dict[str, Any]) -> float:
        """Score based on text readability (0-1).

        Uses average word length as a proxy. Optimal: 4-7 chars per word.
        Short texts (< 5 words) get a neutral score.
        """
        text = content.get("text", "") or content.get("content", "")
        if not text:
            return 0.0
        words = text.split()
        if len(words) < 5:
            return 0.5
        avg_word_len = sum(len(w) for w in words) / len(words)
        if 4 <= avg_word_len <= 7:
            return 1.0
        elif avg_word_len < 4:
            return 0.7
        else:
            return max(0.3, 1.0 - (avg_word_len - 7) / 5)

    def _score_freshness(self, content: dict[str, Any]) -> float:
        """Score based on content freshness (0-1).

        Currently reads from content dict; can be extended with date logic.
        """
        return content.get("freshness_score", 0.5)

    def rank(
        self, items: list[dict[str, Any]]
    ) -> list[tuple[int, float, ScoreBreakdown]]:
        """Rank a list of content items by score (highest first).

        Args:
            items: List of content dicts to score and rank.

        Returns:
            List of (original_index, score, breakdown) sorted by score desc.
        """
        scored = []
        for i, item in enumerate(items):
            score, breakdown = self.score(item)
            scored.append((i, score, breakdown))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
