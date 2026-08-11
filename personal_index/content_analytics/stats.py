"""Content statistics calculator."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ContentStats:
    """Statistics about content items.

    Attributes:
        total_items: Total number of content items.
        total_tags: Total unique tags.
        avg_score: Average content score.
        items_by_type: Count of items per type.
        items_by_tag: Count of items per tag.
        oldest_item: Timestamp of oldest item.
        newest_item: Timestamp of newest item.
    """

    total_items: int = 0
    total_tags: int = 0
    avg_score: float = 0.0
    items_by_type: dict[str, int] = field(default_factory=dict)
    items_by_tag: dict[str, int] = field(default_factory=dict)
    oldest_item: datetime | None = None
    newest_item: datetime | None = None

    @classmethod
    def compute(cls, items: list[dict[str, Any]]) -> ContentStats:
        """Compute statistics from a list of content items.

        Args:
            items: List of content item dictionaries.

        Returns:
            ContentStats instance with computed values.
        """
        if not items:
            return cls()

        stats = cls(total_items=len(items))

        # Compute scores
        scores = [item.get("score", 0.0) for item in items if "score" in item]
        if scores:
            stats.avg_score = round(sum(scores) / len(scores), 4)

        # Count by type
        for item in items:
            item_type = item.get("type", "unknown")
            stats.items_by_type[item_type] = stats.items_by_type.get(item_type, 0) + 1

        # Count by tag
        all_tags: set[str] = set()
        for item in items:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                for tag in tags:
                    stats.items_by_tag[tag] = stats.items_by_tag.get(tag, 0) + 1
                    all_tags.add(tag)
        stats.total_tags = len(all_tags)

        # Date range
        dates = []
        for item in items:
            for key in ("created_at", "updated_at", "published_at"):
                val = item.get(key)
                if isinstance(val, datetime):
                    dates.append(val)
        if dates:
            stats.oldest_item = min(dates)
            stats.newest_item = max(dates)

        return stats
