"""High-level content archiver - compress and manage old content."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from personal_index.content_archive.archive_entry import ArchiveEntry, ArchiveStatus
from personal_index.content_archive.compressor import CompressionFormat, Compressor


@dataclass
class ArchiveConfig:
    """Configuration for the archiver."""

    days_threshold: int = 30
    compression_format: str = "gzip"
    max_archive_size_mb: int = 100

    @property
    def format(self) -> CompressionFormat:
        return CompressionFormat(self.compression_format)


class ContentArchiver:
    """Manages archiving of old content items."""

    def __init__(
        self,
        days_threshold: int = 30,
        compression_format: str = "gzip",
    ) -> None:
        self.config = ArchiveConfig(
            days_threshold=days_threshold,
            compression_format=compression_format,
        )
        self._items: dict[str, ArchiveEntry] = {}
        self._compressor = Compressor()

    def add_item(
        self,
        item_id: str,
        content: str,
        saved_at: str | None = None,
    ) -> None:
        """Add a content item to the archiver."""
        self._items[item_id] = ArchiveEntry(
            item_id=item_id,
            content=content,
        )
        if saved_at:
            self._items[item_id].archived_at = saved_at

    def get_item(self, item_id: str) -> ArchiveEntry | None:
        """Get an item by ID."""
        return self._items.get(item_id)

    def remove_item(self, item_id: str) -> None:
        """Remove an item."""
        self._items.pop(item_id, None)

    def archive_old(self, days_threshold: int | None = None) -> list[str]:
        """Archive items older than the threshold."""
        threshold = days_threshold or self.config.days_threshold
        cutoff = datetime.now(timezone.utc) - timedelta(days=threshold)
        archived_ids: list[str] = []

        for item_id, entry in list(self._items.items()):
            saved_at = entry.archived_at
            if saved_at:
                try:
                    saved_time = datetime.fromisoformat(saved_at)
                    if saved_time < cutoff:
                        entry.archive()
                        archived_ids.append(item_id)
                except (ValueError, TypeError):
                    pass

        return archived_ids

    def restore_item(self, item_id: str) -> bool:
        """Restore an archived item."""
        entry = self._items.get(item_id)
        if entry and entry.status == ArchiveStatus.ARCHIVED:
            entry.restore()
            return True
        return False

    def get_archived_items(self) -> list[ArchiveEntry]:
        """Get all archived items."""
        return [
            e for e in self._items.values()
            if e.status == ArchiveStatus.ARCHIVED
        ]

    def delete_archived(self) -> list[str]:
        """Delete all archived items."""
        deleted: list[str] = []
        for item_id, entry in list(self._items.items()):
            if entry.status == ArchiveStatus.ARCHIVED:
                entry.delete()
                deleted.append(item_id)
        for item_id in deleted:
            del self._items[item_id]
        return deleted

    def get_stats(self) -> dict[str, Any]:
        """Get archive statistics."""
        total = len(self._items)
        archived = sum(1 for e in self._items.values() if e.status == ArchiveStatus.ARCHIVED)
        active = sum(1 for e in self._items.values() if e.status == ArchiveStatus.ACTIVE)
        return {
            "total_items": total,
            "active_items": active,
            "archived_items": archived,
            "deleted_items": total - active - archived,
        }

    def export_archived(self, filepath: str) -> None:
        """Export archived items to a JSON file."""
        archived = self.get_archived_items()
        data = [e.to_dict() for e in archived]
        Path(filepath).write_text(json.dumps(data, indent=2))
