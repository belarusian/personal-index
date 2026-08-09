"""Content metrics tracking for personal-index.

Tracks word counts, reading times, and other content statistics.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ContentMetrics:
    """Metrics for a single piece of content."""

    url: str
    title: str = ""
    word_count: int = 0
    char_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    link_count: int = 0
    image_count: int = 0
    code_block_count: int = 0
    reading_time_seconds: int = 0
    reading_speed_wpm: float = 200.0
    avg_word_length: float = 0.0
    unique_word_ratio: float = 0.0
    readability_score: float = 0.0
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self) -> None:
        """Calculate reading time from word count if not set."""
        if self.reading_time_seconds == 0 and self.word_count > 0:
            self.reading_time_seconds = int(
                self.word_count / self.reading_speed_wpm * 60
            )

    def reading_time_minutes(self) -> float:
        """Return reading time in minutes."""
        return self.reading_time_seconds / 60.0

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "url": self.url,
            "title": self.title,
            "word_count": self.word_count,
            "char_count": self.char_count,
            "sentence_count": self.sentence_count,
            "paragraph_count": self.paragraph_count,
            "link_count": self.link_count,
            "image_count": self.image_count,
            "code_block_count": self.code_block_count,
            "reading_time_seconds": self.reading_time_seconds,
            "reading_speed_wpm": self.reading_speed_wpm,
            "avg_word_length": self.avg_word_length,
            "unique_word_ratio": self.unique_word_ratio,
            "readability_score": self.readability_score,
            "timestamp": self.timestamp,
        }


class ContentMetricsTracker:
    """Tracks content metrics across multiple items."""

    def __init__(self) -> None:
        self._metrics: dict[str, ContentMetrics] = {}

    def record(self, metrics: ContentMetrics) -> None:
        """Record or update metrics for a URL."""
        self._metrics[metrics.url] = metrics

    def get(self, url: str) -> Optional[ContentMetrics]:
        """Get metrics for a URL."""
        return self._metrics.get(url)

    def all(self) -> list[ContentMetrics]:
        """Get all recorded metrics."""
        return list(self._metrics.values())

    def remove(self, url: str) -> None:
        """Remove metrics for a URL."""
        self._metrics.pop(url, None)

    def clear(self) -> None:
        """Clear all recorded metrics."""
        self._metrics.clear()

    def count(self) -> int:
        """Return the number of tracked items."""
        return len(self._metrics)
