"""Content metrics tracking for personal-index.

Tracks word counts, reading times, and other content statistics.
"""

from __future__ import annotations

import statistics
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


@dataclass
class ContentMetricsSummary:
    """Aggregated summary of content metrics."""

    total_items: int = 0
    total_word_count: int = 0
    total_char_count: int = 0
    total_reading_time_seconds: int = 0
    avg_word_count: float = 0.0
    median_word_count: float = 0.0
    max_word_count: int = 0
    min_word_count: int = 0
    avg_reading_time_seconds: float = 0.0
    total_links: int = 0
    total_images: int = 0
    avg_readability_score: float = 0.0

    def to_dict(self) -> dict:
        """Convert summary to dictionary."""
        return {
            "total_items": self.total_items,
            "total_word_count": self.total_word_count,
            "total_char_count": self.total_char_count,
            "total_reading_time_seconds": self.total_reading_time_seconds,
            "avg_word_count": round(self.avg_word_count, 2),
            "median_word_count": round(self.median_word_count, 2),
            "max_word_count": self.max_word_count,
            "min_word_count": self.min_word_count,
            "avg_reading_time_seconds": round(self.avg_reading_time_seconds, 2),
            "total_links": self.total_links,
            "total_images": self.total_images,
            "avg_readability_score": round(self.avg_readability_score, 2),
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

    def summary(self) -> ContentMetricsSummary:
        """Generate an aggregated summary of all tracked metrics."""
        metrics_list = self.all()
        if not metrics_list:
            return ContentMetricsSummary()

        word_counts = [m.word_count for m in metrics_list]
        reading_times = [m.reading_time_seconds for m in metrics_list]
        readability_scores = [m.readability_score for m in metrics_list if m.readability_score > 0]

        return ContentMetricsSummary(
            total_items=len(metrics_list),
            total_word_count=sum(word_counts),
            total_char_count=sum(m.char_count for m in metrics_list),
            total_reading_time_seconds=sum(reading_times),
            avg_word_count=statistics.mean(word_counts),
            median_word_count=statistics.median(word_counts),
            max_word_count=max(word_counts),
            min_word_count=min(word_counts),
            avg_reading_time_seconds=statistics.mean(reading_times),
            total_links=sum(m.link_count for m in metrics_list),
            total_images=sum(m.image_count for m in metrics_list),
            avg_readability_score=statistics.mean(readability_scores) if readability_scores else 0.0,
        )
