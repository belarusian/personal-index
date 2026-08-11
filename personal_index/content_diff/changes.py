"""Content change detection and diffing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ChangeType(Enum):
    """Types of content changes."""

    ADDED = "added"
    REMOVED = "removed"
    MODIFIED = "modified"
    UNCHANGED = "unchanged"


@dataclass
class Change:
    """A single field change.

    Attributes:
        field: Field name that changed.
        change_type: Type of change.
        old_value: Previous value (None if added).
        new_value: New value (None if removed).
    """

    field: str
    change_type: ChangeType
    old_value: Any = None
    new_value: Any = None


@dataclass
class ContentDiff:
    """Diff between two content items.

    Attributes:
        item_id: ID of the content item.
        changes: List of field-level changes.
        summary: Human-readable summary.
    """

    item_id: str
    changes: list[Change] = field(default_factory=list)
    summary: str = ""

    @classmethod
    def compute(
        cls,
        old_item: dict[str, Any],
        new_item: dict[str, Any],
        id_field: str = "id",
    ) -> ContentDiff:
        """Compute the diff between two content items.

        Args:
            old_item: Previous version of the item.
            new_item: New version of the item.
            id_field: Field name for item ID.

        Returns:
            ContentDiff with computed changes.
        """
        item_id = str(new_item.get(id_field, old_item.get(id_field, "unknown")))
        changes: list[Change] = []

        all_fields = set(old_item.keys()) | set(new_item.keys())

        for field_name in sorted(all_fields):
            old_val = old_item.get(field_name)
            new_val = new_item.get(field_name)

            if field_name not in old_item and field_name in new_item:
                changes.append(Change(
                    field=field_name,
                    change_type=ChangeType.ADDED,
                    new_value=new_val,
                ))
            elif field_name in old_item and field_name not in new_item:
                changes.append(Change(
                    field=field_name,
                    change_type=ChangeType.REMOVED,
                    old_value=old_val,
                ))
            elif old_val != new_val:
                changes.append(Change(
                    field=field_name,
                    change_type=ChangeType.MODIFIED,
                    old_value=old_val,
                    new_value=new_val,
                ))

        # Generate summary
        added = sum(1 for c in changes if c.change_type == ChangeType.ADDED)
        removed = sum(1 for c in changes if c.change_type == ChangeType.REMOVED)
        modified = sum(1 for c in changes if c.change_type == ChangeType.MODIFIED)

        parts = []
        if added:
            parts.append(f"{added} added")
        if removed:
            parts.append(f"{removed} removed")
        if modified:
            parts.append(f"{modified} modified")

        summary = ", ".join(parts) if parts else "No changes"

        return cls(item_id=item_id, changes=changes, summary=summary)

    @property
    def has_changes(self) -> bool:
        """Whether there are any changes."""
        return len(self.changes) > 0

    @property
    def change_count(self) -> int:
        """Number of changes."""
        return len(self.changes)

    def get_changes_by_type(self, change_type: ChangeType) -> list[Change]:
        """Get changes filtered by type.

        Args:
            change_type: Type of change to filter.

        Returns:
            List of matching changes.
        """
        return [c for c in self.changes if c.change_type == change_type]
