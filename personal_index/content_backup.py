"""Content backup module - backup and restore functionality."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional


class BackupStatus(str, Enum):
    """Status of a backup entry."""

    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"


class BackupType(str, Enum):
    """Type of backup."""

    FULL = "full"
    INCREMENTAL = "incremental"


@dataclass
class BackupEntry:
    """An entry in a backup archive."""

    url: str
    content_hash: str
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    content: Optional[str] = None
    author: str = ""
    tags: list[str] = field(default_factory=list)
    status: BackupStatus = BackupStatus.PENDING
    backup_type: BackupType = BackupType.FULL
    content_length: int = 0
    published_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    error: Optional[str] = None

    def __post_init__(self) -> None:
        """Set content_length from content if provided."""
        if self.content is not None and self.content_length == 0:
            self.content_length = len(self.content)

    def mark_completed(self) -> None:
        """Mark the entry as completed."""
        self.status = BackupStatus.COMPLETED
        self.error = None

    def mark_failed(self, error: str) -> None:
        """Mark the entry as failed."""
        self.status = BackupStatus.FAILED
        self.error = error

    def mark_pending(self) -> None:
        """Mark the entry as pending."""
        self.status = BackupStatus.PENDING
        self.error = None

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def set_content(self, content: str) -> None:
        """Set the content."""
        self.content = content
        self.content_length = len(content) if content else 0

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "url": self.url,
            "content_hash": self.content_hash,
            "title": self.title,
            "content": self.content,
            "author": self.author,
            "tags": list(self.tags),
            "status": self.status.value,
            "backup_type": self.backup_type.value,
            "content_length": self.content_length,
            "created_at": self.created_at,
            "published_at": self.published_at,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupEntry":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = BackupStatus(status)
        elif not isinstance(status, BackupStatus):
            status = BackupStatus.PENDING

        backup_type = data.get("backup_type", "full")
        if isinstance(backup_type, str):
            backup_type = BackupType(backup_type)
        elif not isinstance(backup_type, BackupType):
            backup_type = BackupType.FULL

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            content_hash=data.get("content_hash", ""),
            title=data.get("title", ""),
            content=data.get("content"),
            author=data.get("author", ""),
            tags=data.get("tags", []),
            status=status,
            backup_type=backup_type,
            content_length=data.get("content_length", 0),
            published_at=data.get("published_at"),
            created_at=created_at,
            error=data.get("error"),
        )


@dataclass
class BackupArchive:
    """An archive of backup entries."""

    archive_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    backup_type: BackupType = BackupType.FULL
    entries: list[BackupEntry] = field(default_factory=list)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def add_entry(self, entry: BackupEntry) -> None:
        """Add an entry, replacing if URL already exists."""
        existing = self.get_entry_by_url(entry.url)
        if existing:
            idx = self.entries.index(existing)
            self.entries[idx] = entry
        else:
            self.entries.append(entry)

    def remove_entry(self, entry_id: str) -> None:
        """Remove an entry by ID."""
        self.entries = [e for e in self.entries if e.entry_id != entry_id]

    def get_entry_by_url(self, url: str) -> Optional[BackupEntry]:
        """Get an entry by URL."""
        for entry in self.entries:
            if entry.url == url:
                return entry
        return None

    def get_completed_entries(self) -> list[BackupEntry]:
        """Get all completed entries."""
        return [e for e in self.entries if e.status == BackupStatus.COMPLETED]

    def get_failed_entries(self) -> list[BackupEntry]:
        """Get all failed entries."""
        return [e for e in self.entries if e.status == BackupStatus.FAILED]

    def get_stats(self) -> dict:
        """Get archive statistics."""
        stats = {
            "total": len(self.entries),
            "completed": 0,
            "failed": 0,
            "pending": 0,
            "total_content_size": self.get_total_content_size(),
        }
        for entry in self.entries:
            if entry.status == BackupStatus.COMPLETED:
                stats["completed"] += 1
            elif entry.status == BackupStatus.FAILED:
                stats["failed"] += 1
            elif entry.status == BackupStatus.PENDING:
                stats["pending"] += 1
        return stats

    def get_total_content_size(self) -> int:
        """Get total size of all content."""
        return sum(e.content_length for e in self.entries)

    def batch_add(self, entries: list[BackupEntry]) -> None:
        """Add multiple entries."""
        for entry in entries:
            self.add_entry(entry)

    def contains_url(self, url: str) -> bool:
        """Check if a URL is in the archive."""
        return self.get_entry_by_url(url) is not None

    def clear_all(self) -> None:
        """Remove all entries."""
        self.entries.clear()

    def get_entries_sorted_by_date(self) -> list[BackupEntry]:
        """Get entries sorted by created date (descending)."""
        return sorted(self.entries, key=lambda e: e.created_at, reverse=True)

    def to_dict(self) -> dict:
        """Serialize the archive."""
        return {
            "archive_id": self.archive_id,
            "name": self.name,
            "backup_type": self.backup_type.value,
            "entries": [entry.to_dict() for entry in self.entries],
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupArchive":
        """Deserialize the archive."""
        backup_type = data.get("backup_type", "full")
        if isinstance(backup_type, str):
            backup_type = BackupType(backup_type)
        elif not isinstance(backup_type, BackupType):
            backup_type = BackupType.FULL

        archive = cls(
            archive_id=data.get("archive_id", uuid.uuid4().hex[:12]),
            name=data.get("name", ""),
            backup_type=backup_type,
        )
        archive.entries = [
            BackupEntry.from_dict(entry_data)
            for entry_data in data.get("entries", [])
        ]
        return archive


@dataclass
class BackupManager:
    """Manager for backup archives."""

    archives: list[BackupArchive] = field(default_factory=list)

    def create_backup(self, name: str = "") -> str:
        """Create a new backup archive. Returns archive ID."""
        archive = BackupArchive(name=name)
        self.archives.append(archive)
        return archive.archive_id

    def get_archive(self, archive_id: str) -> Optional[BackupArchive]:
        """Get an archive by ID."""
        for archive in self.archives:
            if archive.archive_id == archive_id:
                return archive
        return None

    def add_entry_to_backup(self, archive_id: str, entry: BackupEntry) -> None:
        """Add an entry to a backup archive."""
        archive = self.get_archive(archive_id)
        if archive:
            archive.add_entry(entry)

    def delete_backup(self, archive_id: str) -> None:
        """Delete a backup archive."""
        self.archives = [a for a in self.archives if a.archive_id != archive_id]

    def list_backups(self) -> list[BackupArchive]:
        """List all backup archives."""
        return list(self.archives)

    def restore_from_backup(
        self, archive_id: str, url: Optional[str] = None
    ) -> list[BackupEntry]:
        """Restore entries from a backup archive."""
        archive = self.get_archive(archive_id)
        if not archive:
            return []
        if url:
            entry = archive.get_entry_by_url(url)
            if entry:
                return [entry]
            return []
        return list(archive.get_completed_entries())

    def get_backup_stats(self, archive_id: str) -> Optional[dict]:
        """Get stats for a backup archive."""
        archive = self.get_archive(archive_id)
        if archive:
            return archive.get_stats()
        return None

    def get_latest_backup(self) -> Optional[BackupArchive]:
        """Get the most recent backup archive."""
        if not self.archives:
            return None
        return max(self.archives, key=lambda a: a.created_at)

    def compare_backups(
        self, archive_id_1: str, archive_id_2: str
    ) -> dict:
        """Compare two backup archives."""
        archive1 = self.get_archive(archive_id_1)
        archive2 = self.get_archive(archive_id_2)
        if not archive1 or not archive2:
            return {"changed": [], "added": [], "removed": []}

        urls1 = {e.url: e.content_hash for e in archive1.entries}
        urls2 = {e.url: e.content_hash for e in archive2.entries}

        changed = [
            url for url in urls1
            if url in urls2 and urls1[url] != urls2[url]
        ]
        added = [url for url in urls2 if url not in urls1]
        removed = [url for url in urls1 if url not in urls2]

        return {"changed": changed, "added": added, "removed": removed}

    def merge_backups(self, archive_id_1: str, archive_id_2: str) -> str:
        """Merge two backup archives into a new one. Returns new archive ID."""
        archive1 = self.get_archive(archive_id_1)
        archive2 = self.get_archive(archive_id_2)
        if not archive1 or not archive2:
            return self.create_backup("merged")

        merged_id = self.create_backup("merged")
        merged = self.get_archive(merged_id)
        if merged:
            for entry in archive1.entries:
                merged.add_entry(BackupEntry.from_dict(entry.to_dict()))
            for entry in archive2.entries:
                merged.add_entry(BackupEntry.from_dict(entry.to_dict()))
        return merged_id

    def get_total_backup_size(self) -> int:
        """Get total size of all backups."""
        return sum(a.get_total_content_size() for a in self.archives)

    def cleanup_old_backups(self, keep: int = 3) -> None:
        """Keep only the N most recent backups."""
        if len(self.archives) <= keep:
            return
        sorted_archives = sorted(
            self.archives, key=lambda a: a.created_at, reverse=True
        )
        self.archives = sorted_archives[:keep]

    def to_dict(self) -> dict:
        """Serialize the manager."""
        return {
            "archives": [archive.to_dict() for archive in self.archives],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "BackupManager":
        """Deserialize the manager."""
        mgr = cls()
        mgr.archives = [
            BackupArchive.from_dict(archive_data)
            for archive_data in data.get("archives", [])
        ]
        return mgr
