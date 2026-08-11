"""Restore manager for recovering content from backups."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_backup.backup_store import BackupEntry, BackupStore


@dataclass
class RestoreResult:
    """Result of a restore operation.

    Attributes:
        success: Whether the restore succeeded.
        items_restored: Number of items restored.
        backup_id: Source backup ID.
        errors: List of error messages.
    """

    success: bool
    items_restored: int
    backup_id: str
    errors: list[str] = field(default_factory=list)


@dataclass
class RestoreManager:
    """Manages content restore operations.

    Attributes:
        store: The backup store.
    """

    store: BackupStore = field(default_factory=BackupStore)

    def restore_from_backup(
        self,
        backup_id: str,
    ) -> RestoreResult:
        """Restore content from a specific backup.

        Args:
            backup_id: Backup identifier to restore from.

        Returns:
            RestoreResult with outcome details.
        """
        entry = self.store.get_backup(backup_id)
        if entry is None:
            return RestoreResult(
                success=False,
                items_restored=0,
                backup_id=backup_id,
                errors=[f"Backup {backup_id} not found"],
            )

        return RestoreResult(
            success=True,
            items_restored=entry.item_count,
            backup_id=backup_id,
        )

    def restore_latest(self) -> RestoreResult:
        """Restore from the most recent backup.

        Returns:
            RestoreResult with outcome details.
        """
        latest = self.store.get_latest()
        if latest is None:
            return RestoreResult(
                success=False,
                items_restored=0,
                backup_id="",
                errors=["No backups available"],
            )

        return self.restore_from_backup(latest.backup_id)

    def restore_items(
        self,
        backup_id: str,
    ) -> list[dict[str, Any]]:
        """Restore and return the actual items from a backup.

        Args:
            backup_id: Backup identifier.

        Returns:
            List of restored content items.
        """
        entry = self.store.get_backup(backup_id)
        if entry is None:
            return []
        return [dict(item) for item in entry.data]

    def merge_restore(
        self,
        backup_id: str,
        existing_items: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Merge restored items with existing items, avoiding duplicates.

        Args:
            backup_id: Backup identifier.
            existing_items: Currently existing items.

        Returns:
            Merged list of items.
        """
        backup_items = self.restore_items(backup_id)
        existing_ids = {item.get("id") for item in existing_items}

        merged = list(existing_items)
        for item in backup_items:
            if item.get("id") not in existing_ids:
                merged.append(item)
                existing_ids.add(item.get("id"))

        return merged
