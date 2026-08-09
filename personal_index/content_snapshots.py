"""Content snapshots module - archive point-in-time captures of web pages."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


class SnapshotFormat(str, Enum):
    """Format of the snapshot content."""

    HTML = "html"
    PDF = "pdf"
    TEXT = "text"
    MHTML = "mhtml"


class SnapshotStatus(str, Enum):
    """Status of a snapshot."""

    PENDING = "pending"
    COMPLETE = "complete"
    FAILED = "failed"


@dataclass
class Snapshot:
    """A point-in-time capture of a web page."""

    url: str
    snapshot_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    title: str = ""
    content: str = ""
    format: SnapshotFormat = SnapshotFormat.HTML
    status: SnapshotStatus = SnapshotStatus.COMPLETE
    content_length: int = 0
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def __post_init__(self) -> None:
        if self.content_length == 0 and self.content:
            self.content_length = len(self.content)

    def update_content(self, new_content: str) -> None:
        """Update the snapshot content."""
        self.content = new_content
        self.content_length = len(new_content)
        self.status = SnapshotStatus.COMPLETE
        self.error = None

    def add_metadata(self, key: str, value: str) -> None:
        """Add a metadata key-value pair."""
        self.metadata[key] = value

    def get_metadata(self, key: str) -> Optional[str]:
        """Get a metadata value by key."""
        return self.metadata.get(key)

    def is_complete(self) -> bool:
        """Check if the snapshot is complete."""
        return self.status == SnapshotStatus.COMPLETE

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "snapshot_id": self.snapshot_id,
            "url": self.url,
            "title": self.title,
            "content": self.content,
            "format": self.format.value,
            "status": self.status.value,
            "content_length": self.content_length,
            "error": self.error,
            "metadata": dict(self.metadata),
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Snapshot":
        """Deserialize from dictionary."""
        fmt = data.get("format", "html")
        if isinstance(fmt, str):
            fmt = SnapshotFormat(fmt)
        elif not isinstance(fmt, SnapshotFormat):
            fmt = SnapshotFormat.HTML

        status = data.get("status", "complete")
        if isinstance(status, str):
            status = SnapshotStatus(status)
        elif not isinstance(status, SnapshotStatus):
            status = SnapshotStatus.COMPLETE

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            snapshot_id=data.get("snapshot_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            title=data.get("title", ""),
            content=data.get("content", ""),
            format=fmt,
            status=status,
            content_length=data.get("content_length", 0),
            error=data.get("error"),
            metadata=data.get("metadata", {}),
            created_at=created_at,
        )


class SnapshotManager:
    """Manages point-in-time snapshots of web pages."""

    def __init__(self) -> None:
        self._snapshots: dict[str, Snapshot] = {}
        self._url_snapshots: dict[str, list[str]] = {}

    def create_snapshot(
        self,
        url: str,
        content: str = "",
        title: str = "",
        format: SnapshotFormat = SnapshotFormat.HTML,
        status: SnapshotStatus = SnapshotStatus.COMPLETE,
        error: Optional[str] = None,
        metadata: Optional[dict] = None,
        created_at: Optional[str] = None,
    ) -> str:
        """Create a new snapshot. Returns the snapshot ID."""
        snap = Snapshot(
            url=url,
            content=content,
            title=title,
            format=format,
            status=status,
            error=error,
            metadata=metadata or {},
            created_at=created_at or datetime.now(timezone.utc).isoformat(),
        )
        self._snapshots[snap.snapshot_id] = snap
        if url not in self._url_snapshots:
            self._url_snapshots[url] = []
        self._url_snapshots[url].append(snap.snapshot_id)
        return snap.snapshot_id

    def get_snapshot(self, snapshot_id: str) -> Optional[Snapshot]:
        """Get a snapshot by ID."""
        return self._snapshots.get(snapshot_id)

    def list_snapshots(
        self,
        url: Optional[str] = None,
        format: Optional[SnapshotFormat] = None,
        status: Optional[SnapshotStatus] = None,
        sort_by: str = "date",
    ) -> list[Snapshot]:
        """List snapshots with optional filters."""
        if url:
            ids = self._url_snapshots.get(url, [])
            result = [self._snapshots[sid] for sid in ids if sid in self._snapshots]
        else:
            result = list(self._snapshots.values())

        if format is not None:
            result = [s for s in result if s.format == format]
        if status is not None:
            result = [s for s in result if s.status == status]

        if sort_by == "date":
            result.sort(key=lambda s: s.created_at, reverse=True)

        return result

    def get_latest_snapshot(self, url: str) -> Optional[Snapshot]:
        """Get the most recent snapshot for a URL."""
        snaps = self.list_snapshots(url=url, sort_by="date")
        return snaps[0] if snaps else None

    def get_snapshots_for_url(self, url: str) -> list[Snapshot]:
        """Get all snapshots for a specific URL."""
        return self.list_snapshots(url=url)

    def delete_snapshot(self, snapshot_id: str) -> bool:
        """Delete a snapshot. Returns True if deleted."""
        snap = self._snapshots.pop(snapshot_id, None)
        if snap:
            if snap.url in self._url_snapshots:
                self._url_snapshots[snap.url].remove(snapshot_id)
            return True
        return False

    def update_snapshot_content(self, snapshot_id: str, content: str) -> None:
        """Update the content of a snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap:
            snap.update_content(content)

    def update_snapshot_title(self, snapshot_id: str, title: str) -> None:
        """Update the title of a snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap:
            snap.title = title

    def get_snapshot_count(self) -> int:
        """Get total number of snapshots."""
        return len(self._snapshots)

    def get_snapshot_count_by_url(self, url: str) -> int:
        """Get number of snapshots for a URL."""
        return len(self._url_snapshots.get(url, []))

    def get_total_size(self) -> int:
        """Get total content size of all snapshots."""
        return sum(s.content_length for s in self._snapshots.values())

    def get_snapshots_by_date_range(
        self, start: str, end: str
    ) -> list[Snapshot]:
        """Get snapshots within a date range."""
        result = []
        for snap in self._snapshots.values():
            if start <= snap.created_at <= end:
                result.append(snap)
        result.sort(key=lambda s: s.created_at, reverse=True)
        return result

    def restore_snapshot(self, snapshot_id: str) -> Optional[str]:
        """Restore content from a snapshot."""
        snap = self._snapshots.get(snapshot_id)
        if snap and snap.is_complete():
            return snap.content
        return None

    def compare_snapshots(
        self, old_id: str, new_id: str
    ) -> Optional[dict]:
        """Compare two snapshots and return differences."""
        old_snap = self._snapshots.get(old_id)
        new_snap = self._snapshots.get(new_id)
        if not old_snap or not new_snap:
            return None
        return {
            "old_snapshot_id": old_id,
            "new_snapshot_id": new_id,
            "old_content_length": old_snap.content_length,
            "new_content_length": new_snap.content_length,
            "old_title": old_snap.title,
            "new_title": new_snap.title,
            "title_changed": old_snap.title != new_snap.title,
            "content_changed": old_snap.content != new_snap.content,
            "size_diff": new_snap.content_length - old_snap.content_length,
        }

    def cleanup_old_snapshots(self, days: int = 365) -> int:
        """Remove snapshots older than specified days. Returns count removed."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
        to_remove = [
            sid
            for sid, snap in self._snapshots.items()
            if snap.created_at < cutoff
        ]
        for sid in to_remove:
            self.delete_snapshot(sid)
        return len(to_remove)

    def get_urls_with_snapshots(self) -> list[str]:
        """Get all URLs that have snapshots."""
        return list(self._url_snapshots.keys())

    def to_dict(self) -> dict:
        """Serialize the manager state."""
        return {
            "snapshots": {
                sid: s.to_dict() for sid, s in self._snapshots.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SnapshotManager":
        """Deserialize manager state."""
        mgr = cls()
        for sid, sdata in data.get("snapshots", {}).items():
            snap = Snapshot.from_dict(sdata)
            mgr._snapshots[sid] = snap
            if snap.url not in mgr._url_snapshots:
                mgr._url_snapshots[snap.url] = []
            mgr._url_snapshots[snap.url].append(sid)
        return mgr
