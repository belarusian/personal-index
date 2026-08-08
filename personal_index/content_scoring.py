"""Content scoring and ranking utilities."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ScoreBreakdown:
    """Detailed breakdown of a content score."""

    total_score: float = 0.0
    content_length_score: float = 0.0
    keyword_density_score: float = 0.0
    heading_score: float = 0.0
    link_score: float = 0.0
    image_score: float = 0.0
    readability_score: float = 0.0
    freshness_score: float = 0.0


class ContentScorer:
    """Scores and ranks content based on multiple factors."""

    def __init__(self, weights: Optional[dict[str, float]] = None):
        self.weights = weights or {
            "content_length": 0.25,
            "keyword_density": 0.20,
            "headings": 0.15,
            "links": 0.10,
            "images": 0.10,
            "readability": 0.15,
            "freshness": 0.05,
        }

    def score(self, content: dict) -> tuple[float, ScoreBreakdown]:
        """Score a content item based on multiple factors."""
        breakdown = ScoreBreakdown()

        breakdown.content_length_score = self._score_content_length(content)
        breakdown.keyword_density_score = self._score_keyword_density(content)
        breakdown.heading_score = self._score_headings(content)
        breakdown.link_score = self._score_links(content)
        breakdown.image_score = self._score_images(content)
        breakdown.readability_score = self._score_readability(content)
        breakdown.freshness_score = self._score_freshness(content)

        # Weighted sum
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

    def _score_content_length(self, content: dict) -> float:
        """Score based on content length (0-1)."""
        text = content.get("text", "") or content.get("content", "")
        word_count = len(text.split()) if text else 0
        # Optimal: 300-2000 words
        if word_count < 100:
            return min(word_count / 100, 0.5)
        elif word_count < 300:
            return 0.5 + (word_count - 100) / 400
        elif word_count <= 2000:
            return 1.0
        else:
            return max(0.5, 1.0 - (word_count - 2000) / 5000)

    def _score_keyword_density(self, content: dict) -> float:
        """Score based on keyword density (0-1)."""
        keywords = content.get("keywords", [])
        if not keywords:
            return 0.5  # Neutral score
        text = (content.get("text", "") or content.get("content", "")).lower()
        if not text:
            return 0.0
        word_count = len(text.split())
        if word_count == 0:
            return 0.0
        matches = sum(1 for kw in keywords if kw.lower() in text)
        return min(matches / max(len(keywords), 1), 1.0)

    def _score_headings(self, content: dict) -> float:
        """Score based on heading structure (0-1)."""
        headings = content.get("headings", [])
        if not headings:
            return 0.0
        # Score based on number and hierarchy of headings
        score = min(len(headings) / 5, 1.0)
        # Bonus for having h1
        has_h1 = any(h.startswith("h1") for h in headings)
        if has_h1:
            score = min(score + 0.2, 1.0)
        return score

    def _score_links(self, content: dict) -> float:
        """Score based on link quality (0-1)."""
        links = content.get("links", [])
        if not links:
            return 0.3  # Some content doesn't need links
        # Penalize too many links (spam indicator)
        if len(links) > 100:
            return 0.2
        # Reward moderate number of links
        return min(len(links) / 20, 1.0)

    def _score_images(self, content: dict) -> float:
        """Score based on image presence and alt text (0-1)."""
        images = content.get("images", [])
        if not images:
            return 0.3
        with_alt = sum(1 for img in images if img.get("alt", "").strip())
        return min(with_alt / max(len(images), 1), 1.0)

    def _score_readability(self, content: dict) -> float:
        """Score based on text readability (0-1)."""
        text = content.get("text", "") or content.get("content", "")
        if not text:
            return 0.0
        words = text.split()
        if len(words) < 10:
            return 0.5
        # Average word length
        avg_word_len = sum(len(w) for w in words) / len(words)
        # Optimal word length: 4-7 characters
        if 4 <= avg_word_len <= 7:
            return 1.0
        elif avg_word_len < 4:
            return 0.7
        else:
            return max(0.3, 1.0 - (avg_word_len - 7) / 5)

    def _score_freshness(self, content: dict) -> float:
        """Score based on content freshness (0-1)."""
        # Placeholder - would use actual date in real implementation
        return content.get("freshness_score", 0.5)

    def rank(self, items: list[dict]) -> list[tuple[int, float, ScoreBreakdown]]:
        """Rank a list of content items by score."""
        scored = []
        for i, item in enumerate(items):
            score, breakdown = self.score(item)
            scored.append((i, score, breakdown))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
