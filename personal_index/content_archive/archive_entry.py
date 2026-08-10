"""Archive entry data model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class ArchiveStatus(Enum):
    """Status of an archived content item."""

    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"


@dataclass
class ArchiveEntry:
    """Represents a content item in the archive system."""

    item_id: str
    content: str
    original_size: int = 0
    status: ArchiveStatus = ArchiveStatus.ACTIVE
    archived_at: str | None = None
    restored_at: str | None = None

    def __post_init__(self) -> None:
        if self.original_size == 0:
            self.original_size = len(self.content.encode("utf-8"))

    def archive(self) -> None:
        """Mark this entry as archived."""
        self.status = ArchiveStatus.ARCHIVED
        self.archived_at = datetime.now(timezone.utc).isoformat()

    def restore(self) -> None:
        """Restore this entry to active status."""
        self.status = ArchiveStatus.ACTIVE
        self.restored_at = datetime.now(timezone.utc).isoformat()

    def delete(self) -> None:
        """Mark this entry as deleted."""
        self.status = ArchiveStatus.DELETED

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "content": self.content,
            "original_size": self.original_size,
            "status": self.status.value,
            "archived_at": self.archived_at,
            "restored_at": self.restored_at,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ArchiveEntry:
        status_val = data.get("status", "active")
        if isinstance(status_val, str):
            status_val = ArchiveStatus(status_val)
        return cls(
            item_id=data["item_id"],
            content=data.get("content", ""),
            original_size=data.get("original_size", 0),
            status=status_val,
            archived_at=data.get("archived_at"),
            restored_at=data.get("restored_at"),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ArchiveEntry):
            return NotImplemented
        return self.item_id == other.item_id and self.content == other.content
