"""Content watch module - monitor saved URLs for changes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Optional


class WatchStatus(str, Enum):
    """Status of a URL watch entry."""

    ACTIVE = "active"
    PAUSED = "paused"
    ERROR = "error"


class WatchChangeType(str, Enum):
    """Types of changes detected on watched URLs."""

    CONTENT_CHANGED = "content_changed"
    TITLE_CHANGED = "title_changed"
    STATUS_CHANGED = "status_changed"
    REMOVED = "removed"
    MOVED = "moved"


@dataclass
class WatchEntry:
    """A watched URL entry that monitors for changes."""

    url: str
    watch_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    check_interval_minutes: int = 60
    status: WatchStatus = WatchStatus.ACTIVE
    tags: list[str] = field(default_factory=list)
    last_hash: Optional[str] = None
    last_checked_at: Optional[str] = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    change_count: int = 0

    def update_hash(self, new_hash: str) -> None:
        """Update the stored hash and check timestamp."""
        self.last_hash = new_hash
        self.last_checked_at = datetime.now(timezone.utc).isoformat()

    def is_due(self) -> bool:
        """Check if this watch entry is due for a check."""
        if self.status != WatchStatus.ACTIVE:
            return False
        if self.last_checked_at is None:
            return True
        try:
            last = datetime.fromisoformat(self.last_checked_at)
            now = datetime.now(timezone.utc)
            elapsed = (now - last).total_seconds() / 60
            return elapsed >= self.check_interval_minutes
        except (ValueError, TypeError):
            return True

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "watch_id": self.watch_id,
            "url": self.url,
            "check_interval_minutes": self.check_interval_minutes,
            "status": self.status.value,
            "tags": list(self.tags),
            "last_hash": self.last_hash,
            "last_checked_at": self.last_checked_at,
            "created_at": self.created_at,
            "change_count": self.change_count,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatchEntry":
        """Deserialize from dictionary."""
        status = data.get("status", "active")
        if isinstance(status, str):
            status = WatchStatus(status)
        elif not isinstance(status, WatchStatus):
            status = WatchStatus.ACTIVE

        created_at = data.get("created_at", datetime.now(timezone.utc).isoformat())
        if isinstance(created_at, datetime):
            created_at = created_at.isoformat()

        return cls(
            watch_id=data.get("watch_id", uuid.uuid4().hex[:12]),
            url=data["url"],
            check_interval_minutes=data.get("check_interval_minutes", 60),
            status=status,
            tags=data.get("tags", []),
            last_hash=data.get("last_hash"),
            last_checked_at=data.get("last_checked_at"),
            created_at=created_at,
            change_count=data.get("change_count", 0),
        )


@dataclass
class WatchChange:
    """A detected change on a watched URL."""

    watch_id: str
    change_type: WatchChangeType
    change_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    old_value: Optional[str] = None
    new_value: Optional[str] = None
    detected_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        """Serialize to dictionary."""
        return {
            "change_id": self.change_id,
            "watch_id": self.watch_id,
            "change_type": self.change_type.value,
            "old_value": self.old_value,
            "new_value": self.new_value,
            "detected_at": self.detected_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatchChange":
        """Deserialize from dictionary."""
        ctype = data.get("change_type", "content_changed")
        if isinstance(ctype, str):
            ctype = WatchChangeType(ctype)
        elif not isinstance(ctype, WatchChangeType):
            ctype = WatchChangeType.CONTENT_CHANGED

        detected_at = data.get("detected_at", datetime.now(timezone.utc).isoformat())
        if isinstance(detected_at, datetime):
            detected_at = detected_at.isoformat()

        return cls(
            change_id=data.get("change_id", uuid.uuid4().hex[:12]),
            watch_id=data["watch_id"],
            change_type=ctype,
            old_value=data.get("old_value"),
            new_value=data.get("new_value"),
            detected_at=detected_at,
        )


class WatchManager:
    """Manages URL watch entries and change detection."""

    def __init__(self) -> None:
        self._watches: dict[str, WatchEntry] = {}
        self._url_to_watch: dict[str, str] = {}
        self._changes: dict[str, list[WatchChange]] = {}

    def add_watch(
        self,
        url: str,
        check_interval_minutes: int = 60,
        tags: list[str] | None = None,
        last_checked_at: Optional[str] = None,
    ) -> str:
        """Add a URL to watch. Returns the watch ID."""
        if url in self._url_to_watch:
            return self._url_to_watch[url]
        entry = WatchEntry(
            url=url,
            check_interval_minutes=check_interval_minutes,
            tags=tags or [],
            last_checked_at=last_checked_at,
        )
        self._watches[entry.watch_id] = entry
        self._url_to_watch[url] = entry.watch_id
        self._changes[entry.watch_id] = []
        return entry.watch_id

    def get_watch(self, watch_id: str) -> Optional[WatchEntry]:
        """Get a watch entry by ID."""
        return self._watches.get(watch_id)

    def get_watch_by_url(self, url: str) -> Optional[WatchEntry]:
        """Get a watch entry by URL."""
        wid = self._url_to_watch.get(url)
        if wid:
            return self._watches.get(wid)
        return None

    def list_watches(
        self,
        tags: list[str] | None = None,
        status: Optional[WatchStatus] = None,
    ) -> list[WatchEntry]:
        """List watch entries with optional filters."""
        result = list(self._watches.values())
        if status is not None:
            result = [w for w in result if w.status == status]
        if tags:
            result = [w for w in result if any(t in w.tags for t in tags)]
        return result

    def remove_watch(self, watch_id: str) -> bool:
        """Remove a watch entry. Returns True if removed."""
        entry = self._watches.pop(watch_id, None)
        if entry:
            self._url_to_watch.pop(entry.url, None)
            self._changes.pop(watch_id, None)
            return True
        return False

    def pause_watch(self, watch_id: str) -> None:
        """Pause a watch entry."""
        entry = self._watches.get(watch_id)
        if entry:
            entry.status = WatchStatus.PAUSED

    def resume_watch(self, watch_id: str) -> None:
        """Resume a paused watch entry."""
        entry = self._watches.get(watch_id)
        if entry:
            entry.status = WatchStatus.ACTIVE

    def get_due_watches(self) -> list[WatchEntry]:
        """Get all watch entries that are due for checking."""
        return [w for w in self._watches.values() if w.is_due()]

    def record_change(
        self,
        watch_id: str,
        change_type: WatchChangeType,
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
    ) -> WatchChange:
        """Record a change for a watched URL."""
        change = WatchChange(
            watch_id=watch_id,
            change_type=change_type,
            old_value=old_value,
            new_value=new_value,
        )
        if watch_id not in self._changes:
            self._changes[watch_id] = []
        self._changes[watch_id].append(change)
        entry = self._watches.get(watch_id)
        if entry:
            entry.change_count += 1
        return change

    def get_changes(self, watch_id: str) -> list[WatchChange]:
        """Get all changes for a watched URL."""
        return self._changes.get(watch_id, [])

    def get_recent_changes(
        self, watch_id: str, limit: int = 10
    ) -> list[WatchChange]:
        """Get recent changes for a watched URL."""
        changes = self._changes.get(watch_id, [])
        return changes[-limit:]

    def get_all_changes(self) -> list[WatchChange]:
        """Get all changes across all watches."""
        all_changes = []
        for changes in self._changes.values():
            all_changes.extend(changes)
        return all_changes

    def update_hash(self, watch_id: str, new_hash: str) -> None:
        """Update the stored hash for a watch entry."""
        entry = self._watches.get(watch_id)
        if entry:
            entry.update_hash(new_hash)

    def check_watch(self, watch_id: str, current_hash: str) -> Optional[WatchChange]:
        """Check a watch entry against a current hash. Returns change if detected."""
        entry = self._watches.get(watch_id)
        if not entry or entry.status != WatchStatus.ACTIVE:
            return None
        if entry.last_hash is None:
            entry.update_hash(current_hash)
            return None
        if entry.last_hash != current_hash:
            change = self.record_change(
                watch_id,
                WatchChangeType.CONTENT_CHANGED,
                old_value=entry.last_hash,
                new_value=current_hash,
            )
            entry.update_hash(current_hash)
            return change
        entry.last_checked_at = datetime.now(timezone.utc).isoformat()
        return None

    def get_watch_count(self) -> int:
        """Get the total number of watch entries."""
        return len(self._watches)

    def to_dict(self) -> dict:
        """Serialize the manager state."""
        return {
            "watches": {wid: e.to_dict() for wid, e in self._watches.items()},
            "changes": {
                wid: [c.to_dict() for c in changes]
                for wid, changes in self._changes.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WatchManager":
        """Deserialize manager state."""
        mgr = cls()
        for wid, edata in data.get("watches", {}).items():
            entry = WatchEntry.from_dict(edata)
            mgr._watches[wid] = entry
            mgr._url_to_watch[entry.url] = wid
        for wid, cdata in data.get("changes", {}).items():
            mgr._changes[wid] = [WatchChange.from_dict(c) for c in cdata]
        return mgr
