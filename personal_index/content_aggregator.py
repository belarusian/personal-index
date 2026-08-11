"""
Content Aggregator Module
Aggregates content from multiple sources.
"""

from __future__ import annotations

from typing import Any


class ContentAggregator:
    """Aggregates content from multiple sources."""

    def __init__(self):
        self._sources: dict[str, list[dict[str, Any]]] = {}
        self._merged: list[dict[str, Any]] = []

    def add_source(self, name: str, items: list[dict[str, Any]]) -> None:
        """Add a content source."""
        self._sources[name] = list(items)

    def get_source(self, name: str) -> list[dict[str, Any]]:
        """Get items from a specific source."""
        return self._sources.get(name, [])

    def merge_all(self, deduplicate: bool = True) -> list[dict[str, Any]]:
        """Merge all sources into a single list."""
        merged = []
        for items in self._sources.values():
            merged.extend(items)
        if deduplicate:
            seen = set()
            unique = []
            for item in merged:
                key = str(item.get("id") or item.get("title"))
                if key not in seen:
                    seen.add(key)
                    unique.append(item)
            return unique
        return merged

    def filter_by_source(self, source_name: str) -> list[dict[str, Any]]:
        """Get items from a specific source."""
        return self._sources.get(source_name, [])

    def get_source_names(self) -> list[str]:
        """Get all source names."""
        return list(self._sources.keys())

    def clear_source(self, name: str) -> bool:
        """Clear a specific source."""
        if name in self._sources:
            del self._sources[name]
            return True
        return False

    def clear_all(self) -> None:
        """Clear all sources."""
        self._sources.clear()

    @property
    def total_items(self) -> int:
        """Total items across all sources (before merge)."""
        return sum(len(items) for items in self._sources.values())

    @property
    def source_count(self) -> int:
        """Number of sources."""
        return len(self._sources)
