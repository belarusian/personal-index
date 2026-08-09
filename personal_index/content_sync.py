"""Content sync module - sync across devices."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Callable, Optional


class SyncStatus(str, Enum):
    """Status of a sync entry."""

    PENDING = "pending"
    SYNCED = "synced"
    FAILED = "failed"
    CONFLICT = "conflict"


class SyncDirection(str, Enum):
    """Direction of sync operation."""

    UPLOAD = "upload"
    DOWNLOAD = "download"


class ConflictResolution(str, Enum):
    """Strategy for resolving sync conflicts."""

    LOCAL_WINS = "local_wins"
    REMOTE_WINS = "remote_wins"
    NEWEST_WINS = "newest_wins"


@dataclass
class SyncEntry:
    """An entry in the sync manifest."""

    url: str
    content_hash: str
    entry_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    device_id: str = ""
    tags: list[str] = field(default_factory=list)
    status: SyncStatus = SyncStatus.PENDING
    direction: SyncDirection = SyncDirection.UPLOAD
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    synced_at: Optional[str] = None
    error: Optional[str] = None
    remote_hash: Optional[str] = None
    remote_created_at: Optional[str] = None

    def mark_synced(self) -> None:
        """Mark the entry as synced."""
        self.status = SyncStatus.SYNCED
        self.synced_at = datetime.now(timezone.utc).isoformat()
        self.error = None

    def mark_failed(self, error: str) -> None:
        """Mark the entry as failed."""
        self.status = SyncStatus.FAILED
        self.error = error

    def mark_pending(self) -> None:
        """Mark the entry as pending."""
        self.status = SyncStatus.PENDING
        self.synced_at = None
        self.error = None

    def mark_conflict(self, error: str) -> None:
        """Mark the entry as having a conflict."""
        self.status = SyncStatus.CONFLICT
        self.error = error

    def add_tag(self, tag: str) -> None:
        """Add a tag if not already present."""
        if tag not in self.tags:
            self.tags.append(tag)

    def remove_tag(self, tag: str) -> None:
        """Remove a tag if present."""
        if tag in self.tags:
            self.tags.remove(tag)

    def update_content_hash(self, content_hash: str) -> None:
        """Update the content hash and reset to pending."""
        self.content_hash = content_hash
        self.status = SyncStatus.PENDING
        self.synced_at = None

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "entry_id": self.entry_id,
            "url": self.url,
            "content_hash": self.content_hash,
            "title": self.title,
            "device_id": self.device_id,
            "status": self.status.value,
            "direction": self.direction.value,
            "tags": list(self.tags),
            "created_at": self.created_at,
            "synced_at": self.synced_at,
            "error": self.error,
            "remote_hash": self.remote_hash,
            "remote_created_at": self.remote_created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncEntry":
        """Deserialize from dictionary."""
        status = data.get("status", "pending")
        if isinstance(status, str):
            status = SyncStatus(status)
        elif not isinstance(status, SyncStatus):
            status = SyncStatus.PENDING

        direction = data.get("direction", "upload")
        if isinstance(direction, str):
            direction = SyncDirection(direction)
        elif not isinstance(direction, SyncDirection):
            direction = SyncDirection.UPLOAD

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            entry_id=data.get("entry_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            content_hash=data.get("content_hash", ""),
            title=data.get("title", ""),
            device_id=data.get("device_id", ""),
            tags=data.get("tags", []),
            status=status,
            direction=direction,
            created_at=created_at,
            synced_at=data.get("synced_at"),
            error=data.get("error"),
            remote_hash=data.get("remote_hash"),
            remote_created_at=data.get("remote_created_at"),
        )


@dataclass
class SyncManifest:
    """A manifest of sync entries for a device."""

    manifest_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    device_id: str = ""
    entries: list[SyncEntry] = field(default_factory=list)

    def add_entry(self, entry: SyncEntry) -> None:
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

    def get_entry_by_url(self, url: str) -> Optional[SyncEntry]:
        """Get an entry by URL."""
        for entry in self.entries:
            if entry.url == url:
                return entry
        return None

    def get_pending_entries(self) -> list[SyncEntry]:
        """Get all pending entries."""
        return [e for e in self.entries if e.status == SyncStatus.PENDING]

    def get_synced_entries(self) -> list[SyncEntry]:
        """Get all synced entries."""
        return [e for e in self.entries if e.status == SyncStatus.SYNCED]

    def get_failed_entries(self) -> list[SyncEntry]:
        """Get all failed entries."""
        return [e for e in self.entries if e.status == SyncStatus.FAILED]

    def get_conflict_entries(self) -> list[SyncEntry]:
        """Get all conflict entries."""
        return [e for e in self.entries if e.status == SyncStatus.CONFLICT]

    def get_entries_by_direction(self, direction: SyncDirection) -> list[SyncEntry]:
        """Get entries by direction."""
        return [e for e in self.entries if e.direction == direction]

    def get_stats(self) -> dict:
        """Get manifest statistics."""
        stats = {
            "total": len(self.entries),
            "pending": 0,
            "synced": 0,
            "failed": 0,
            "conflict": 0,
        }
        for entry in self.entries:
            if entry.status == SyncStatus.PENDING:
                stats["pending"] += 1
            elif entry.status == SyncStatus.SYNCED:
                stats["synced"] += 1
            elif entry.status == SyncStatus.FAILED:
                stats["failed"] += 1
            elif entry.status == SyncStatus.CONFLICT:
                stats["conflict"] += 1
        return stats

    def retry_failed(self) -> None:
        """Mark all failed entries as pending."""
        for entry in self.entries:
            if entry.status == SyncStatus.FAILED:
                entry.mark_pending()

    def clear_all(self) -> None:
        """Remove all entries."""
        self.entries.clear()

    def merge_with(self, remote: "SyncManifest") -> "SyncManifest":
        """Merge with a remote manifest, detecting conflicts."""
        merged = SyncManifest(
            manifest_id=uuid.uuid4().hex[:12],
            device_id=self.device_id,
        )
        # Copy all local entries
        for entry in self.entries:
            merged.add_entry(SyncEntry.from_dict(entry.to_dict()))
        # Merge remote entries
        for remote_entry in remote.entries:
            local_entry = merged.get_entry_by_url(remote_entry.url)
            if local_entry and local_entry.content_hash != remote_entry.content_hash:
                # Conflict detected - store remote info
                local_entry.mark_conflict(
                    f"Remote has different hash: {remote_entry.content_hash}"
                )
                local_entry.remote_hash = remote_entry.content_hash
                local_entry.remote_created_at = remote_entry.created_at
            elif not local_entry:
                merged.add_entry(SyncEntry.from_dict(remote_entry.to_dict()))
        return merged

    def to_dict(self) -> dict:
        """Serialize the manifest."""
        return {
            "manifest_id": self.manifest_id,
            "device_id": self.device_id,
            "entries": [entry.to_dict() for entry in self.entries],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncManifest":
        """Deserialize the manifest."""
        manifest = cls(
            manifest_id=data.get("manifest_id", uuid.uuid4().hex[:12]),
            device_id=data.get("device_id", ""),
        )
        manifest.entries = [
            SyncEntry.from_dict(entry_data)
            for entry_data in data.get("entries", [])
        ]
        return manifest


@dataclass
class SyncConflict:
    """Represents a sync conflict between local and remote."""

    url: str
    local: SyncEntry
    remote: SyncEntry

    def to_dict(self) -> dict:
        """Serialize the conflict."""
        return {
            "url": self.url,
            "local_hash": self.local.content_hash,
            "remote_hash": self.remote.content_hash,
            "local_entry": self.local.to_dict(),
            "remote_entry": self.remote.to_dict(),
        }


@dataclass
class SyncEngine:
    """Engine for managing sync operations."""

    device_id: str
    manifest: SyncManifest = field(default_factory=SyncManifest)

    def __post_init__(self) -> None:
        """Set device_id on manifest."""
        self.manifest.device_id = self.device_id

    def add_item_for_sync(
        self, url: str, content_hash: str, title: str = ""
    ) -> None:
        """Add an item for syncing."""
        existing = self.manifest.get_entry_by_url(url)
        if existing and existing.content_hash == content_hash and existing.status == SyncStatus.SYNCED:
            return
        entry = SyncEntry(
            url=url,
            content_hash=content_hash,
            title=title,
            device_id=self.device_id,
        )
        self.manifest.add_entry(entry)

    def batch_add_for_sync(self, items: list[tuple[str, str, str]]) -> None:
        """Add multiple items for syncing. Each item is (url, hash, title)."""
        for url, content_hash, title in items:
            self.add_item_for_sync(url, content_hash, title)

    def remove_item_from_sync(self, url: str) -> None:
        """Remove an item from sync."""
        entry = self.manifest.get_entry_by_url(url)
        if entry:
            self.manifest.remove_entry(entry.entry_id)

    def run_sync(
        self,
        on_sync: Optional[Callable[[str, SyncEntry], None]] = None,
        on_fail: Optional[Callable[[str, SyncEntry, str], None]] = None,
    ) -> dict:
        """Run sync for all pending entries."""
        result = {"synced": 0, "failed": 0}
        pending = self.manifest.get_pending_entries()
        for entry in pending:
            try:
                entry.mark_synced()
                result["synced"] += 1
                if on_sync:
                    on_sync(entry.url, entry)
            except Exception as e:
                entry.mark_failed(str(e))
                result["failed"] += 1
                if on_fail:
                    on_fail(entry.url, entry, str(e))
        return result

    def apply_remote_manifest(self, remote: SyncManifest) -> None:
        """Apply a remote manifest, detecting conflicts."""
        for remote_entry in remote.entries:
            local_entry = self.manifest.get_entry_by_url(remote_entry.url)
            if local_entry and local_entry.content_hash != remote_entry.content_hash:
                local_entry.mark_conflict(
                    f"Remote has different hash: {remote_entry.content_hash}"
                )
                local_entry.remote_hash = remote_entry.content_hash
                local_entry.remote_created_at = remote_entry.created_at
            elif not local_entry:
                self.manifest.add_entry(
                    SyncEntry.from_dict(remote_entry.to_dict())
                )

    def resolve_conflict(
        self, url: str, resolution: ConflictResolution
    ) -> None:
        """Resolve a conflict for a given URL."""
        entry = self.manifest.get_entry_by_url(url)
        if not entry or entry.status != SyncStatus.CONFLICT:
            return

        if resolution == ConflictResolution.LOCAL_WINS:
            # Keep local hash
            entry.remote_hash = None
            entry.remote_created_at = None
            entry.mark_synced()
        elif resolution == ConflictResolution.REMOTE_WINS:
            # Use remote hash
            if entry.remote_hash:
                entry.content_hash = entry.remote_hash
            entry.remote_hash = None
            entry.remote_created_at = None
            entry.mark_synced()
        elif resolution == ConflictResolution.NEWEST_WINS:
            # Compare created_at timestamps
            local_time = entry.created_at
            remote_time = entry.remote_created_at or ""
            if remote_time > local_time:
                if entry.remote_hash:
                    entry.content_hash = entry.remote_hash
            entry.remote_hash = None
            entry.remote_created_at = None
            entry.mark_synced()

    def get_conflicts(self) -> list[SyncConflict]:
        """Get all current conflicts."""
        conflicts = []
        for entry in self.manifest.get_conflict_entries():
            conflicts.append(
                SyncConflict(
                    url=entry.url,
                    local=entry,
                    remote=SyncEntry(
                        url=entry.url,
                        content_hash=entry.remote_hash or "",
                    ),
                )
            )
        return conflicts

    def get_sync_status(self) -> dict:
        """Get overall sync status."""
        return self.manifest.get_stats()

    def retry_all_failed(self) -> None:
        """Retry all failed entries."""
        self.manifest.retry_failed()

    def to_dict(self) -> dict:
        """Serialize the engine."""
        return {
            "device_id": self.device_id,
            "manifest": self.manifest.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SyncEngine":
        """Deserialize the engine."""
        engine = cls(
            device_id=data.get("device_id", ""),
            manifest=SyncManifest.from_dict(data.get("manifest", {})),
        )
        return engine
