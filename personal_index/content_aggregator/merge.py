"""Merge strategies for combining content from sources."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class MergeStrategy(Enum):
    """Strategies for merging content from multiple sources."""

    APPEND = "append"
    DEDUP = "dedup"
    REPLACE = "replace"
    MERGE_FIELDS = "merge_fields"


@dataclass
class MergeResult:
    """Result of a merge operation.

    Attributes:
        items: Merged content items.
        strategy: Strategy used.
        total_sources: Number of sources merged.
        total_items: Total items in result.
        duplicates_removed: Number of duplicates removed.
    """

    items: list[dict[str, Any]]
    strategy: MergeStrategy
    total_sources: int
    total_items: int
    duplicates_removed: int = 0


def merge_append(
    all_items: list[list[dict[str, Any]]],
) -> MergeResult:
    """Append all items from all sources.

    Args:
        all_items: List of item lists from each source.

    Returns:
        MergeResult with appended items.
    """
    merged = []
    for items in all_items:
        merged.extend(items)
    return MergeResult(
        items=merged,
        strategy=MergeStrategy.APPEND,
        total_sources=len(all_items),
        total_items=len(merged),
    )


def merge_dedup(
    all_items: list[list[dict[str, Any]]],
    id_field: str = "id",
) -> MergeResult:
    """Merge items removing duplicates by ID.

    Args:
        all_items: List of item lists from each source.
        id_field: Field to use for deduplication.

    Returns:
        MergeResult with deduplicated items.
    """
    seen: set[str] = set()
    merged: list[dict[str, Any]] = []
    total = 0

    for items in all_items:
        for item in items:
            total += 1
            item_id = str(item.get(id_field, ""))
            if item_id and item_id not in seen:
                seen.add(item_id)
                merged.append(item)

    return MergeResult(
        items=merged,
        strategy=MergeStrategy.DEDUP,
        total_sources=len(all_items),
        total_items=len(merged),
        duplicates_removed=total - len(merged),
    )


def merge_replace(
    all_items: list[list[dict[str, Any]]],
    id_field: str = "id",
) -> MergeResult:
    """Merge items, replacing duplicates with latest.

    Args:
        all_items: List of item lists from each source.
        id_field: Field to use for deduplication.

    Returns:
        MergeResult with replaced items.
    """
    items_dict: dict[str, dict[str, Any]] = {}
    total = 0

    for items in all_items:
        for item in items:
            total += 1
            item_id = str(item.get(id_field, ""))
            if item_id:
                items_dict[item_id] = item

    merged = list(items_dict.values())
    return MergeResult(
        items=merged,
        strategy=MergeStrategy.REPLACE,
        total_sources=len(all_items),
        total_items=len(merged),
        duplicates_removed=total - len(merged),
    )


def merge_fields(
    all_items: list[list[dict[str, Any]]],
    id_field: str = "id",
) -> MergeResult:
    """Merge items by combining fields from duplicates.

    Args:
        all_items: List of item lists from each source.
        id_field: Field to use for grouping.

    Returns:
        MergeResult with field-merged items.
    """
    items_dict: dict[str, dict[str, Any]] = {}
    total = 0

    for items in all_items:
        for item in items:
            total += 1
            item_id = str(item.get(id_field, ""))
            if item_id:
                if item_id in items_dict:
                    existing = items_dict[item_id]
                    for key, value in item.items():
                        if key not in existing:
                            existing[key] = value
                else:
                    items_dict[item_id] = dict(item)

    merged = list(items_dict.values())
    return MergeResult(
        items=merged,
        strategy=MergeStrategy.MERGE_FIELDS,
        total_sources=len(all_items),
        total_items=len(merged),
        duplicates_removed=total - len(merged),
    )
