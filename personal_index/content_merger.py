"""Content merging utilities for personal-index.

Provides functionality to merge content from multiple sources,
deduplicate entries, and resolve conflicts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class MergeResult:
    """Result of a content merge operation.

    Attributes:
        total_input: Total items across all sources.
        merged_count: Number of items in merged output.
        duplicates_removed: Number of duplicates removed.
        conflicts_resolved: Number of conflicts resolved.
        source_counts: Items per source.
        merge_time_ms: Time taken to merge.
    """

    total_input: int = 0
    merged_count: int = 0
    duplicates_removed: int = 0
    conflicts_resolved: int = 0
    source_counts: dict[str, int] = field(default_factory=dict)
    merge_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "total_input": self.total_input,
            "merged_count": self.merged_count,
            "duplicates_removed": self.duplicates_removed,
            "conflicts_resolved": self.conflicts_resolved,
            "source_counts": self.source_counts,
            "merge_time_ms": round(self.merge_time_ms, 2),
        }


class ContentMerger:
    """Merges content from multiple sources with deduplication.

    Supports merging by URL, by ID, or by content hash,
    with configurable conflict resolution strategies.
    """

    def __init__(
        self,
        dedup_key: str = "url",
        conflict_strategy: str = "newest",
    ) -> None:
        self.dedup_key = dedup_key
        self.conflict_strategy = conflict_strategy

    def merge(
        self,
        sources: dict[str, list[dict[str, Any]]],
    ) -> tuple[list[dict[str, Any]], MergeResult]:
        """Merge content from multiple sources.

        Args:
            sources: Dict mapping source names to item lists.
            conflict_strategy: How to resolve conflicts.

        Returns:
            Tuple of (merged items, MergeResult).
        """
        import time

        start = time.time()
        result = MergeResult()
        result.source_counts = {
            name: len(items) for name, items in sources.items()
        }
        result.total_input = sum(result.source_counts.values())

        merged: dict[str, dict[str, Any]] = {}
        conflicts = 0

        for source_name, items in sources.items():
            for item in items:
                key = item.get(self.dedup_key, "")
                if not key:
                    # No dedup key, just add
                    item_id = item.get("id", f"merged-{len(merged)}")
                    merged[item_id] = {**item, "_source": source_name}
                    continue

                if key not in merged:
                    merged[key] = {**item, "_source": source_name}
                else:
                    conflicts += 1
                    existing = merged[key]
                    winner = self._resolve_conflict(
                        existing, item, source_name,
                    )
                    merged[key] = winner

        result.conflicts_resolved = conflicts
        result.merged_count = len(merged)
        result.duplicates_removed = result.total_input - result.merged_count
        result.merge_time_ms = (time.time() - start) * 1000

        return list(merged.values()), result

    def merge_with_priority(
        self,
        sources: dict[str, list[dict[str, Any]]],
        priority_order: list[str] | None = None,
    ) -> tuple[list[dict[str, Any]], MergeResult]:
        """Merge sources with priority ordering.

        Higher priority sources win conflicts.

        Args:
            sources: Dict mapping source names to item lists.
            priority_order: List of source names in priority order.

        Returns:
            Tuple of (merged items, MergeResult).
        """
        if priority_order is None:
            priority_order = list(sources.keys())

        # Process sources in reverse priority order
        # so higher priority sources overwrite
        ordered_sources = {}
        for name in reversed(priority_order):
            if name in sources:
                ordered_sources[name] = sources[name]

        # Add any sources not in priority order
        for name, items in sources.items():
            if name not in ordered_sources:
                ordered_sources[name] = items

        return self.merge(ordered_sources)

    def merge_tags(
        self,
        items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge duplicate tags within each item.

        Args:
            items: List of content items.

        Returns:
            Items with deduplicated tags.
        """
        result = []
        for item in items:
            new_item = dict(item)
            tags = item.get("tags", [])
            if isinstance(tags, list):
                seen: set[str] = set()
                unique_tags = []
                for tag in tags:
                    if tag not in seen:
                        seen.add(tag)
                        unique_tags.append(tag)
                new_item["tags"] = unique_tags
            result.append(new_item)
        return result

    def _resolve_conflict(
        self,
        existing: dict[str, Any],
        new_item: dict[str, Any],
        new_source: str,
    ) -> dict[str, Any]:
        """Resolve a conflict between two items with the same key."""
        if self.conflict_strategy == "newest":
            existing_date = self._get_date(existing)
            new_date = self._get_date(new_item)
            if new_date and (not existing_date or new_date > existing_date):
                return {**new_item, "_source": new_source}
            return existing

        elif self.conflict_strategy == "highest_score":
            existing_score = existing.get("score", 0.0)
            new_score = new_item.get("score", 0.0)
            if new_score > existing_score:
                return {**new_item, "_source": new_source}
            return existing

        elif self.conflict_strategy == "merge_tags":
            existing_tags = set(existing.get("tags", []))
            new_tags = set(new_item.get("tags", []))
            merged_tags = list(existing_tags | new_tags)
            result = dict(new_item)
            result["tags"] = merged_tags
            result["_source"] = f"{existing.get('_source', '')},{new_source}"
            return result

        # Default: keep existing
        return existing

    def _get_date(
        self,
        item: dict[str, Any],
    ) -> datetime | None:
        """Get the date from an item."""
        for key in ("updated_at", "published_at", "date"):
            value = item.get(key)
            if value:
                if isinstance(value, str):
                    return datetime.fromisoformat(value)
                if isinstance(value, datetime):
                    return value
        return None
