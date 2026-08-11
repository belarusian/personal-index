"""Backup storage for content data."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


@dataclass
class BackupEntry:
    """A single backup entry.

    Attributes:
        backup_id: Unique backup identifier.
        timestamp: When the backup was created.
        item_count: Number of items in the backup.
        data: The backed-up content data.
        metadata: Additional backup metadata.
    """

    backup_id: str
    timestamp: datetime
    item_count: int
    data: list[dict[str, Any]]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class BackupStore:
    """Stores and retrieves content backups.

    Attributes:
        backups: Dictionary of backup_id to BackupEntry.
        max_backups: Maximum number of backups to keep.
    """

    backups: dict[str, BackupEntry] = field(default_factory=dict)
    max_backups: int = 10

    def add_backup(
        self,
        items: list[dict[str, Any]],
        backup_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> BackupEntry:
        """Create a new backup entry.

        Args:
            items: Content items to back up.
            backup_id: Optional backup identifier.
            metadata: Optional metadata.

        Returns:
            The created BackupEntry.
        """
        if backup_id is None:
            backup_id = f"backup_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        entry = BackupEntry(
            backup_id=backup_id,
            timestamp=datetime.now(timezone.utc),
            item_count=len(items),
            data=[dict(item) for item in items],
            metadata=metadata or {},
        )

        self.backups[backup_id] = entry

        # Enforce max backups
        if len(self.backups) > self.max_backups:
            self._evict_oldest()

        return entry

    def get_backup(self, backup_id: str) -> BackupEntry | None:
        """Get a backup by ID.

        Args:
            backup_id: Backup identifier.

        Returns:
            BackupEntry or None if not found.
        """
        return self.backups.get(backup_id)

    def list_backups(self) -> list[BackupEntry]:
        """List all backups sorted by timestamp.

        Returns:
            List of BackupEntry objects.
        """
        return sorted(
            self.backups.values(),
            key=lambda b: b.timestamp,
            reverse=True,
        )

    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup.

        Args:
            backup_id: Backup identifier.

        Returns:
            True if deleted, False if not found.
        """
        if backup_id in self.backups:
            del self.backups[backup_id]
            return True
        return False

    def get_latest(self) -> BackupEntry | None:
        """Get the most recent backup.

        Returns:
            Latest BackupEntry or None.
        """
        backups = self.list_backups()
        return backups[0] if backups else None

    def _evict_oldest(self) -> None:
        """Remove the oldest backup when limit is exceeded."""
        oldest = min(self.backups.values(), key=lambda b: b.timestamp)
        del self.backups[oldest.backup_id]

    def export_to_file(
        self,
        backup_id: str,
        filepath: str | Path,
    ) -> None:
        """Export a backup to a JSON file.

        Args:
            backup_id: Backup identifier.
            filepath: Output file path.
        """
        entry = self.get_backup(backup_id)
        if entry is None:
            raise ValueError(f"Backup {backup_id} not found")

        filepath = Path(filepath)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "backup_id": entry.backup_id,
            "timestamp": entry.timestamp.isoformat(),
            "item_count": entry.item_count,
            "metadata": entry.metadata,
            "items": entry.data,
        }
        filepath.write_text(json.dumps(data, indent=2))

    def import_from_file(
        self,
        filepath: str | Path,
    ) -> BackupEntry:
        """Import a backup from a JSON file.

        Args:
            filepath: Input file path.

        Returns:
            The created BackupEntry.
        """
        filepath = Path(filepath)
        data = json.loads(filepath.read_text())

        entry = BackupEntry(
            backup_id=data["backup_id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            item_count=data["item_count"],
            data=data["items"],
            metadata=data.get("metadata", {}),
        )
        self.backups[entry.backup_id] = entry
        return entry
