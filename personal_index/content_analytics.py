"""
Content Analytics Module
Analytics and statistics for content items.
"""

from __future__ import annotations

from collections import Counter
from typing import Any


class ContentAnalytics:
    """Computes analytics from content items."""

    def __init__(self):
        self._items: list[dict[str, Any]] = []

    def add_items(self, items: list[dict[str, Any]]) -> None:
        """Add items for analysis."""
        self._items.extend(items)

    @property
    def total_items(self) -> int:
        return len(self._items)

    def get_tag_counts(self) -> dict[str, int]:
        """Count occurrences of each tag."""
        counter = Counter()
        for item in self._items:
            tags = item.get("tags", [])
            if isinstance(tags, list):
                counter.update(tags)
        return dict(counter)

    def get_title_lengths(self) -> list[int]:
        """Get lengths of all titles."""
        return [len(str(item.get("title", ""))) for item in self._items]

    def get_avg_title_length(self) -> float:
        """Average title length."""
        lengths = self.get_title_lengths()
        if not lengths:
            return 0.0
        return sum(lengths) / len(lengths)

    def get_description_lengths(self) -> list[int]:
        """Get lengths of all descriptions."""
        return [len(str(item.get("description", ""))) for item in self._items]

    def get_avg_description_length(self) -> float:
        """Average description length."""
        lengths = self.get_description_lengths()
        if not lengths:
            return 0.0
        return sum(lengths) / len(lengths)

    def get_items_with_links(self) -> list[dict[str, Any]]:
        """Get items that have a link."""
        return [item for item in self._items if item.get("link")]

    def get_link_ratio(self) -> float:
        """Ratio of items with links."""
        if not self._items:
            return 0.0
        return len(self.get_items_with_links()) / len(self._items)

    def get_tag_distribution(self) -> dict[str, float]:
        """Get tag distribution as percentages."""
        total = sum(self.get_tag_counts().values())
        if total == 0:
            return {}
        return {tag: count / total * 100 for tag, count in self.get_tag_counts().items()}

    def get_items_by_tag(self, tag: str) -> list[dict[str, Any]]:
        """Get items with a specific tag."""
        return [item for item in self._items if tag in (item.get("tags") or [])]

    def get_unique_tags_count(self) -> int:
        """Count unique tags."""
        return len(self.get_tag_counts())

    def clear(self) -> None:
        """Clear all items."""
        self._items.clear()
