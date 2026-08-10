from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import ClassVar

from personal_index.text_utils import (
    count_words,
    extract_keywords,
    read_time_minutes,
    tokenize,
)


@dataclass
class EnrichedContent:
    """Content with enriched metadata."""
    title: str
    text: str
    word_count: int = 0
    reading_time: float = 0.0
    keywords: list[str] = field(default_factory=list)
    language: str = "en"
    has_code: bool = False
    has_links: bool = False
    has_images: bool = False
    sentiment_score: float = 0.0
    complexity_score: float = 0.0
    enriched_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "title": self.title,
            "text": self.text,
            "word_count": self.word_count,
            "reading_time": self.reading_time,
            "keywords": self.keywords,
            "language": self.language,
            "has_code": self.has_code,
            "has_links": self.has_links,
            "has_images": self.has_images,
            "sentiment_score": self.sentiment_score,
            "complexity_score": self.complexity_score,
            "enriched_at": self.enriched_at.isoformat(),
        }


class ContentEnricher:
    """Enrich content with computed metadata and analysis."""

    # Simple positive/negative word lists for basic sentiment
    POSITIVE_WORDS: ClassVar[set[str]] = {
        "good", "great", "excellent", "amazing", "wonderful", "fantastic",
        "awesome", "best", "love", "like", "beautiful", "perfect", "happy",
        "success", "win", "positive", "brilliant", "outstanding", "superb",
        "impressive", "remarkable", "exceptional", "enjoy", "pleased",
        "satisfied", "recommend", "benefit", "advantage", "improve",
    }

    NEGATIVE_WORDS: ClassVar[set[str]] = {
        "bad", "terrible", "awful", "horrible", "worst", "hate", "poor",
        "fail", "failure", "negative", "ugly", "broken", "error", "bug",
        "problem", "issue", "difficult", "hard", "slow", "wrong",
        "disappointing", "frustrating", "annoying", "useless", "waste",
        "dangerous", "risky", "flaw", "limitation", "drawback",
    }

    def __init__(self, top_n_keywords: int = 10):
        """Initialize the content enricher.

        Args:
            top_n_keywords: Number of top keywords to extract.
        """
        self.top_n_keywords = top_n_keywords

    def enrich(self, title: str, text: str, html: str | None = None) -> EnrichedContent:
        """Enrich content with computed metadata.

        Args:
            title: Content title.
            text: Plain text content.
            html: Optional HTML source for additional analysis.

        Returns:
            EnrichedContent with computed metadata.
        """
        enriched = EnrichedContent(
            title=title,
            text=text,
        )

        # Basic metrics
        enriched.word_count = count_words(text)
        enriched.reading_time = read_time_minutes(text)

        # Keywords
        keywords = extract_keywords(text, top_n=self.top_n_keywords, min_freq=1)
        enriched.keywords = [kw[0] for kw in keywords]

        # Content type detection from HTML
        if html:
            enriched.has_code = self._detect_code(html)
            enriched.has_links = self._detect_links(html)
            enriched.has_images = self._detect_images(html)

        # Sentiment analysis
        enriched.sentiment_score = self._compute_sentiment(text)

        # Complexity score
        enriched.complexity_score = self._compute_complexity(text)

        return enriched

    def _detect_code(self, html: str) -> bool:
        """Detect if HTML contains code blocks."""
        code_patterns = [
            r"<pre[^>]*>.*?</pre>",
            r"<code[^>]*>.*?</code>",
            r"<script[^>]*>.*?</script>",
        ]
        return any(re.search(pattern, html, re.DOTALL | re.IGNORECASE) for pattern in code_patterns)

    def _detect_links(self, html: str) -> bool:
        """Detect if HTML contains anchor links."""
        return bool(re.search(r"<a\s+[^>]*href=", html, re.IGNORECASE))

    def _detect_images(self, html: str) -> bool:
        """Detect if HTML contains images."""
        return bool(re.search(r"<img\s+[^>]*src=", html, re.IGNORECASE))

    def _compute_sentiment(self, text: str) -> float:
        """Compute basic sentiment score from -1.0 to 1.0.

        Uses simple positive/negative word counting.

        Args:
            text: Input text.

        Returns:
            Sentiment score between -1.0 and 1.0.
        """
        words = set(tokenize(text))
        positive_count = len(words & self.POSITIVE_WORDS)
        negative_count = len(words & self.NEGATIVE_WORDS)
        total = positive_count + negative_count
        if total == 0:
            return 0.0
        return (positive_count - negative_count) / total

    def _compute_complexity(self, text: str) -> float:
        """Compute text complexity score from 0.0 to 1.0.

        Based on average word length and unique word ratio.

        Args:
            text: Input text.

        Returns:
            Complexity score between 0.0 and 1.0.
        """
        tokens = tokenize(text)
        if not tokens:
            return 0.0

        # Average word length (normalized to 0-1, assuming max ~15 chars)
        avg_length = sum(len(t) for t in tokens) / len(tokens)
        length_score = min(avg_length / 15.0, 1.0)

        # Unique word ratio (higher = more complex vocabulary)
        unique_ratio = len(set(tokens)) / len(tokens)

        # Combine scores
        return round((length_score * 0.4 + unique_ratio * 0.6), 4)

    def batch_enrich(self, items: list[tuple[str, str]]) -> list[EnrichedContent]:
        """Enrich multiple content items.

        Args:
            items: List of (title, text) tuples.

        Returns:
            List of EnrichedContent objects.
        """
        return [self.enrich(title, text) for title, text in items]

"""Content enrichment module for enhancing indexed content with metadata."""

