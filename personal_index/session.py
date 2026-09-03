"""Crawl session tracking and management."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
    """Possible statuses for a crawl session."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


@dataclass
class SessionStats:
    """Statistics for a crawl session."""

    urls_crawled: int = 0
    urls_failed: int = 0
    urls_skipped: int = 0
    bytes_downloaded: int = 0
    pages_indexed: int = 0
    errors: list[str] = field(default_factory=list)
    domains_seen: set[str] = field(default_factory=set)

    @property
    def success_rate(self) -> float:
        """Ratio of successfully crawled URLs to total attempted."""
        total = self.urls_crawled + self.urls_failed
        return self.urls_crawled / total if total > 0 else 0.0

    @property
    def total_processed(self) -> int:
        """Total number of URLs processed (crawled + failed + skipped)."""
        return self.urls_crawled + self.urls_failed + self.urls_skipped

    def to_dict(self) -> dict:
        """Serialize session stats to a dictionary.

        Returns:
            Dictionary representation of the stats.
        """
        return {
            "urls_crawled": self.urls_crawled,
            "urls_failed": self.urls_failed,
            "urls_skipped": self.urls_skipped,
            "bytes_downloaded": self.bytes_downloaded,
            "pages_indexed": self.pages_indexed,
            "success_rate": self.success_rate,
            "total_processed": self.total_processed,
            "domains_seen": len(self.domains_seen),
            "error_count": len(self.errors),
        }


@dataclass
class CrawlSession:
    """Represents a single crawl session."""

    session_id: str
    name: str = ""
    status: SessionStatus = SessionStatus.ACTIVE
    started_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    stats: SessionStats = field(default_factory=SessionStats)
    config: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> float | None:
        """Elapsed time in seconds since the session started."""
        end = self.completed_at or time.time()
        return end - self.started_at

    def pause(self) -> None:
        """Pause the session if currently active."""
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        """Resume the session if currently paused."""
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.ACTIVE

    def complete(self) -> None:
        """Mark the session as completed."""
        self.status = SessionStatus.COMPLETED
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        """Mark the session as failed with an error message."""
        self.status = SessionStatus.FAILED
        self.completed_at = time.time()
        self.stats.errors.append(error)

    def stop(self) -> None:
        """Stop the session (user-initiated halt)."""
        self.status = SessionStatus.STOPPED
        self.completed_at = time.time()

    def record_url_crawled(self, url: str, size: int = 0) -> None:
        """Record a successfully crawled URL.

        Args:
            url: The URL that was crawled.
            size: Number of bytes downloaded.
        """
        from urllib.parse import urlparse
        self.stats.urls_crawled += 1
        self.stats.bytes_downloaded += size
        parsed = urlparse(url)
        self.stats.domains_seen.add(parsed.netloc)

    def record_url_failed(self, url: str, error: str = "") -> None:
        """Record a failed URL crawl.

        Args:
            url: The URL that failed.
            error: Optional error message.
        """
        self.stats.urls_failed += 1
        if error:
            self.stats.errors.append(f"{url}: {error}")

    def record_url_skipped(self, url: str) -> None:
        """Record a skipped URL.

        Args:
            url: The URL that was skipped.
        """
        self.stats.urls_skipped += 1

    def record_page_indexed(self) -> None:
        """Record that a page was indexed."""
        self.stats.pages_indexed += 1

    def to_dict(self) -> dict:
        """Serialize the crawl session to a dictionary.

        Returns:
            Dictionary representation of the session.
        """
        return {
            "session_id": self.session_id,
            "name": self.name,
            "status": self.status.value,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "stats": self.stats.to_dict(),
            "config": self.config,
            "metadata": self.metadata,
        }


class SessionManager:
    """Manages crawl sessions with persistence."""

    def __init__(self, storage_path: str | None = None):
        self._sessions: dict[str, CrawlSession] = {}
        self._active_session: str | None = None
        self._storage_path = storage_path

    def create_session(self, session_id: str, name: str = "",
                       config: dict | None = None) -> CrawlSession:
        """Create a new crawl session.

        Args:
            session_id: Unique session identifier.
            name: Human-readable session name.
            config: Optional configuration dictionary.

        Returns:
            The created CrawlSession.
        """
        session = CrawlSession(
            session_id=session_id,
            name=name,
            config=config or {},
        )
        self._sessions[session_id] = session
        if self._active_session is None:
            self._active_session = session_id
        return session

    def get_session(self, session_id: str) -> CrawlSession | None:
        """Get a session by ID.

        Args:
            session_id: The session identifier.

        Returns:
            The CrawlSession, or None if not found.
        """
        return self._sessions.get(session_id)

    def get_active_session(self) -> CrawlSession | None:
        """Get the currently active session.

        Returns:
            The active CrawlSession, or None.
        """
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None

    def set_active(self, session_id: str) -> bool:
        """Set a session as the active one.

        Args:
            session_id: The session to activate.

        Returns:
            True if the session was found and activated.
        """
        if session_id in self._sessions:
            self._active_session = session_id
            return True
        return False

    def list_sessions(self) -> list[CrawlSession]:
        """List all sessions.

        Returns:
            List of all CrawlSession objects.
        """
        return list(self._sessions.values())

    def list_active(self) -> list[CrawlSession]:
        """List all active sessions.

        Returns:
            List of active CrawlSession objects.
        """
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    def remove_session(self, session_id: str) -> bool:
        """Remove a session.

        Args:
            session_id: The session to remove.

        Returns:
            True if the session was found and removed.
        """
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = None
            return True
        return False

    def save_session(self, session_id: str) -> str | None:
        """Save a session to disk.

        Args:
            session_id: The session to save.

        Returns:
            Path to the saved file, or None if not saved.
        """
        session = self._sessions.get(session_id)
        if not session or not self._storage_path:
            return None
        path = Path(self._storage_path) / f"{session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        return str(path)

    def load_session(self, filepath: str) -> CrawlSession | None:
        """Load a session from disk.

        Args:
            filepath: Path to the session JSON file.

        Returns:
            The loaded CrawlSession, or None if not found.
        """
        path = Path(filepath)
        if not path.exists():
            return None
        with open(path) as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                return None
        if not isinstance(data, dict):
            return None
        try:
            status = SessionStatus(data.get("status", "active"))
        except ValueError:
            return None
        session_id = data.get("session_id")
        if not session_id:
            return None
        session = CrawlSession(
            session_id=session_id,
            name=data.get("name", ""),
            status=status,
            started_at=data.get("started_at", time.time()),
            completed_at=data.get("completed_at"),
            config=data.get("config", {}),
            metadata=data.get("metadata", {}),
        )
        stats_data = data.get("stats", {})
        session.stats = SessionStats(
            urls_crawled=stats_data.get("urls_crawled", 0),
            urls_failed=stats_data.get("urls_failed", 0),
            urls_skipped=stats_data.get("urls_skipped", 0),
            bytes_downloaded=stats_data.get("bytes_downloaded", 0),
            pages_indexed=stats_data.get("pages_indexed", 0),
        )
        self._sessions[session.session_id] = session
        return session

    @property
    def session_count(self) -> int:
        """Number of sessions managed."""
        return len(self._sessions)
