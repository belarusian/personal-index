"""Content pinning functionality for personal index.

Provides functions to pin and unpin content items, marking them as
important or permanently stored.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path


@dataclass
class PinnedItem:
    """A pinned content item."""

    item_id: str
    pinned_at: str = ""
    reason: str = ""
    metadata: dict = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Set default pinned_at timestamp."""
        if not self.pinned_at:
            self.pinned_at = datetime.now(timezone.utc).isoformat()


class ContentPinner:
    """Manage pinned content items."""

    def __init__(self, storage_path: str | None = None) -> None:
        """Initialize the content pinner.

        Args:
            storage_path: Path to store pinned items JSON file.
        """
        self.storage_path = storage_path or str(
            Path.home() / ".personal_index" / "pinned_items.json"
        )
        self._pinned: dict[str, PinnedItem] = {}
        self._load()

    def _load(self) -> None:
        """Load pinned items from storage."""
        if not os.path.exists(self.storage_path):
            self._pinned = {}
            return
        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)
                if not isinstance(data, dict):
                    self._pinned = {}
                    return
            self._pinned = {}
            for item_id, item_data in data.items():
                self._pinned[item_id] = PinnedItem(
                    item_id=item_id,
                    pinned_at=item_data.get("pinned_at", ""),
                    reason=item_data.get("reason", ""),
                    metadata=item_data.get("metadata", {}),
                )
        except (json.JSONDecodeError, KeyError, TypeError):
            self._pinned = {}

    def _save(self) -> None:
        """Save pinned items to storage."""
        parent = Path(self.storage_path).parent
        parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for item_id, item in self._pinned.items():
            data[item_id] = {
                "pinned_at": item.pinned_at,
                "reason": item.reason,
                "metadata": item.metadata,
            }
        with open(self.storage_path, "w") as f:
            json.dump(data, f, indent=2)

    def pin(self, item_id: str, reason: str = "", metadata: dict | None = None) -> bool:
        """Pin a content item.

        Args:
            item_id: ID of the item to pin.
            reason: Optional reason for pinning.
            metadata: Optional metadata dictionary.

        Returns:
            True if successfully pinned. Returns False if the pin could not be
            persisted (e.g. a disk I/O error in ``_save``); on failure the
            in-memory state is rolled back so the item is not left pinned.
        """
        snapshot = dict(self._pinned)
        self._pinned[item_id] = PinnedItem(
            item_id=item_id,
            reason=reason,
            metadata=metadata or {},
        )
        try:
            self._save()
        except OSError:
            self._pinned = snapshot
            return False
        return True

    def unpin(self, item_id: str) -> bool:
        """Unpin a content item.

        Args:
            item_id: ID of the item to unpin.

        Returns:
            True if successfully unpinned (or was not pinned). Returns False
            if the unpin could not be persisted (e.g. a disk I/O error in
            ``_save``); on failure the in-memory state is rolled back so the
            item is not left unpinned.
        """
        if item_id in self._pinned:
            snapshot = dict(self._pinned)
            del self._pinned[item_id]
            try:
                self._save()
            except OSError:
                self._pinned = snapshot
                return False
        return True

    def is_pinned(self, item_id: str) -> bool:
        """Check if an item is pinned.

        Args:
            item_id: ID of the item to check.

        Returns:
            True if the item is pinned.
        """
        return item_id in self._pinned

    def get_pinned_items(self) -> list[PinnedItem]:
        """Get all pinned items.

        Returns:
            List of PinnedItem objects.
        """
        return list(self._pinned.values())

    def clear(self) -> None:
        """Clear all pinned items."""
        self._pinned.clear()
        self._save()


# Module-level instance for convenience
_default_pinner: ContentPinner | None = None


def _get_default_pinner() -> ContentPinner:
    """Get or create the default content pinner instance."""
    global _default_pinner
    if _default_pinner is None:
        _default_pinner = ContentPinner()
    return _default_pinner


def pin_content(item_id: str, reason: str = "", metadata: dict | None = None) -> bool:
    """Pin a content item using the default pinner.

    Args:
        item_id: ID of the item to pin.
        reason: Optional reason for pinning.
        metadata: Optional metadata dictionary.

    Returns:
        True if successfully pinned. Returns False if the pin could not be
        persisted (e.g. a disk I/O error in ``_save``); on failure the
        in-memory state is rolled back so the item is not left pinned.
    """
    return _get_default_pinner().pin(item_id, reason, metadata)


def unpin_content(item_id: str) -> bool:
    """Unpin a content item using the default pinner.

    Args:
        item_id: ID of the item to unpin.

    Returns:
        True if successfully unpinned (or was not pinned). Returns False
        if the unpin could not be persisted (e.g. a disk I/O error in
        _save); on failure the in-memory state is rolled back so the
        item is not left unpinned.
    """
    return _get_default_pinner().unpin(item_id)