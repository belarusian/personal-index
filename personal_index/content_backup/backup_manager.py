"""Backup manager for orchestrating content backups."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

from personal_index.content_backup.backup_store import BackupEntry, BackupStore


@dataclass
class BackupConfig:
    """Configuration for backup operations.

    Attributes:
        max_backups: Maximum number of backups to retain.
        include_metadata: Whether to include item metadata.
        compression: Whether to compress backup data.
    """

    max_backups: int = 10
    include_metadata: bool = True
    compression: bool = False


@dataclass
class BackupManager:
    """Manages content backup operations.

    Attributes:
        store: The backup store.
        config: Backup configuration.
    """

    store: BackupStore = field(default_factory=BackupStore)
    config: BackupConfig = field(default_factory=BackupConfig)

    def __post_init__(self) -> None:
        self.store.max_backups = self.config.max_backups

    def create_backup(
        self,
        items: list[dict[str, Any]],
        label: str | None = None,
    ) -> BackupEntry:
        """Create a new backup of content items.

        Args:
            items: Content items to back up.
            label: Optional label for the backup.

        Returns:
            The created BackupEntry.
        """
        metadata: dict[str, Any] = {
            "created_by": "BackupManager",
            "label": label or "",
        }
        return self.store.add_backup(items, metadata=metadata)

    def create_incremental_backup(
        self,
        items: list[dict[str, Any]],
        last_backup_id: str | None = None,
    ) -> BackupEntry:
        """Create an incremental backup with only new/changed items.

        Args:
            items: Current content items.
            last_backup_id: ID of the last backup to compare against.

        Returns:
            BackupEntry with only changed items.
        """
        if last_backup_id:
            last = self.store.get_backup(last_backup_id)
            if last:
                last_ids = {item.get("id") for item in last.data}
                new_items = [
                    item for item in items
                    if item.get("id") not in last_ids
                ]
                if new_items:
                    return self.store.add_backup(
                        new_items,
                        metadata={"type": "incremental", "base": last_backup_id},
                    )
                return self.store.add_backup([], metadata={"type": "incremental", "base": last_backup_id})

        return self.create_backup(items)

    def get_backup_summary(self) -> dict[str, Any]:
        """Get a summary of all backups.

        Returns:
            Dictionary with backup summary information.
        """
        backups = self.store.list_backups()
        return {
            "total_backups": len(backups),
            "total_items_backed_up": sum(b.item_count for b in backups),
            "latest_backup": (
                backups[0].backup_id if backups else None
            ),
            "oldest_backup": (
                backups[-1].backup_id if backups else None
            ),
        }

    def cleanup_old_backups(
        self,
        older_than: timedelta | None = None,
    ) -> int:
        """Remove backups older than a specified duration.

        Args:
            older_than: Duration threshold.

        Returns:
            Number of backups removed.
        """
        if older_than is None:
            older_than = timedelta(days=30)

        cutoff = datetime.now(timezone.utc) - older_than
        removed = 0
        to_remove = [
            b.backup_id
            for b in self.store.list_backups()
            if b.timestamp < cutoff
        ]
        for bid in to_remove:
            if self.store.delete_backup(bid):
                removed += 1
        return removed
