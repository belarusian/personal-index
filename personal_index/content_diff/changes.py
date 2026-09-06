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

    @staticmethod
    def _diff_field(name: str, old: dict[str, Any], new: dict[str, Any]) -> Change | None:
        if name not in old and name in new:
            return Change(field=name, change_type=ChangeType.ADDED, new_value=new[name])
        if name in old and name not in new:
            return Change(field=name, change_type=ChangeType.REMOVED, old_value=old[name])
        if old.get(name) != new.get(name):
            return Change(field=name, change_type=ChangeType.MODIFIED, old_value=old.get(name), new_value=new.get(name))
        return None

    @staticmethod
    def _summary_text(changes: list[Change]) -> str:
        parts: list[str] = []
        for ct, label in [(ChangeType.ADDED, "added"), (ChangeType.REMOVED, "removed"), (ChangeType.MODIFIED, "modified")]:
            n = sum(1 for c in changes if c.change_type == ct)
            if n:
                parts.append(f"{n} {label}")
        return ", ".join(parts) if parts else "No changes"

    @classmethod
    def compute(
        cls,
        old_item: dict[str, Any],
        new_item: dict[str, Any],
        id_field: str = "id",
    ) -> ContentDiff:
        """Compute the diff between two content items.

        Builds a ContentDiff from the field-level differences between
        ``old_item`` and ``new_item``.

        Contract:
          * ``item_id`` is resolved by the fallback chain
            ``str(new_item.get(id_field, old_item.get(id_field,
            "unknown")))`` -- the new item's value first, then the old
            item's value, then the literal string ``"unknown"``.
          * The diffed field set is the sorted union of the keys of both
            items (``set(old_item) | set(new_item)``, iterated in sorted
            order).
          * Each field is classified ADDED (present only in new_item),
            REMOVED (present only in old_item), or MODIFIED (present in
            both but with differing values); unchanged fields are
            dropped from ``changes``.
          * ``summary`` is built by ``_summary_text`` as
            ``"N added, N removed, N modified"`` (that fixed order, with
            zero-count types omitted) or ``"No changes"`` when there are
            no changes.

        Args:
            old_item: Previous content item.
            new_item: Current content item.
            id_field: Key used to resolve ``item_id`` (default ``"id"``).

        Returns:
            A ContentDiff with the resolved item_id, the list of field
            changes, and the summary string.
        """
        item_id = str(new_item.get(id_field, old_item.get(id_field, "unknown")))
        all_fields = set(old_item.keys()) | set(new_item.keys())
        changes = [c for fn in sorted(all_fields) if (c := cls._diff_field(fn, old_item, new_item))]
        summary = cls._summary_text(changes)
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
