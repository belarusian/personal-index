"""Snapshot management for content versioning."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from personal_index.content_diff.changes import ContentDiff


@dataclass
class Snapshot:
    """A point-in-time snapshot of content.

    Attributes:
        snapshot_id: Unique snapshot identifier.
        timestamp: When the snapshot was taken.
        data: Content data at this point in time.
        label: Optional label for the snapshot.
    """

    snapshot_id: str
    timestamp: datetime
    data: dict[str, Any]
    label: str = ""


@dataclass
class SnapshotManager:
    """Manages content snapshots for versioning.

    Attributes:
        snapshots: Dictionary of item_id to list of snapshots.
        max_snapshots: Maximum snapshots per item.
    """

    snapshots: dict[str, list[Snapshot]] = field(default_factory=dict)
    max_snapshots: int = 10
    _counter: int = field(default=0, repr=False)

    def create_snapshot(
        self,
        item: dict[str, Any],
        id_field: str = "id",
        label: str = "",
    ) -> Snapshot:
        """Create a new snapshot of a content item.

        Args:
            item: Content item to snapshot.
            id_field: Field name for item ID.
            label: Optional label.

        Returns:
            The created Snapshot.
        """
        item_id = str(item.get(id_field, "unknown"))
        self._counter += 1
        snapshot = Snapshot(
            snapshot_id=f"{item_id}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{self._counter}",
            timestamp=datetime.now(timezone.utc),
            data=dict(item),
            label=label,
        )

        self.snapshots.setdefault(item_id, []).append(snapshot)

        # Enforce max snapshots
        if len(self.snapshots[item_id]) > self.max_snapshots:
            self.snapshots[item_id] = self.snapshots[item_id][-self.max_snapshots:]

        return snapshot

    def get_snapshots(self, item_id: str) -> list[Snapshot]:
        """Get all snapshots for an item.

        Args:
            item_id: Item identifier.

        Returns:
            List of snapshots sorted by timestamp.
        """
        return sorted(
            self.snapshots.get(item_id, []),
            key=lambda s: s.timestamp,
        )

    def get_latest(self, item_id: str) -> Snapshot | None:
        """Get the latest snapshot for an item.

        Args:
            item_id: Item identifier.

        Returns:
            Latest snapshot or None.
        """
        snaps = self.get_snapshots(item_id)
        return snaps[-1] if snaps else None

    def diff_snapshots(
        self,
        item_id: str,
        old_id: str,
        new_id: str,
    ) -> ContentDiff | None:
        """Compute diff between two snapshots.

        Args:
            item_id: Item identifier.
            old_id: Old snapshot ID.
            new_id: New snapshot ID.

        Returns:
            ContentDiff or None if snapshots not found.
        """
        snaps = self.snapshots.get(item_id, [])
        old_snap = next((s for s in snaps if s.snapshot_id == old_id), None)
        new_snap = next((s for s in snaps if s.snapshot_id == new_id), None)

        if old_snap is None or new_snap is None:
            return None

        return ContentDiff.compute(old_snap.data, new_snap.data)

    def get_history(
        self,
        item_id: str,
    ) -> list[ContentDiff]:
        """Get change history for an item.

        Args:
            item_id: Item identifier.

        Returns:
            List of ContentDiff objects showing changes between snapshots.
        """
        snaps = self.get_snapshots(item_id)
        diffs: list[ContentDiff] = []

        for i in range(1, len(snaps)):
            diff = ContentDiff.compute(snaps[i - 1].data, snaps[i].data)
            diffs.append(diff)

        return diffs
