"""Crawl session tracking and management."""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class SessionStatus(str, Enum):
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
        total = self.urls_crawled + self.urls_failed
        return self.urls_crawled / total if total > 0 else 0.0

    @property
    def total_processed(self) -> int:
        return self.urls_crawled + self.urls_failed + self.urls_skipped

    def to_dict(self) -> dict:
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
    completed_at: Optional[float] = None
    stats: SessionStats = field(default_factory=SessionStats)
    config: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        end = self.completed_at or time.time()
        return end - self.started_at

    def pause(self) -> None:
        if self.status == SessionStatus.ACTIVE:
            self.status = SessionStatus.PAUSED

    def resume(self) -> None:
        if self.status == SessionStatus.PAUSED:
            self.status = SessionStatus.ACTIVE

    def complete(self) -> None:
        self.status = SessionStatus.COMPLETED
        self.completed_at = time.time()

    def fail(self, error: str) -> None:
        self.status = SessionStatus.FAILED
        self.completed_at = time.time()
        self.stats.errors.append(error)

    def stop(self) -> None:
        self.status = SessionStatus.STOPPED
        self.completed_at = time.time()

    def record_url_crawled(self, url: str, size: int = 0) -> None:
        from urllib.parse import urlparse
        self.stats.urls_crawled += 1
        self.stats.bytes_downloaded += size
        parsed = urlparse(url)
        self.stats.domains_seen.add(parsed.netloc)

    def record_url_failed(self, url: str, error: str = "") -> None:
        self.stats.urls_failed += 1
        if error:
            self.stats.errors.append(f"{url}: {error}")

    def record_url_skipped(self, url: str) -> None:
        self.stats.urls_skipped += 1

    def record_page_indexed(self) -> None:
        self.stats.pages_indexed += 1

    def to_dict(self) -> dict:
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

    def __init__(self, storage_path: Optional[str] = None):
        self._sessions: dict[str, CrawlSession] = {}
        self._active_session: Optional[str] = None
        self._storage_path = storage_path

    def create_session(self, session_id: str, name: str = "",
                       config: Optional[dict] = None) -> CrawlSession:
        session = CrawlSession(
            session_id=session_id,
            name=name,
            config=config or {},
        )
        self._sessions[session_id] = session
        if self._active_session is None:
            self._active_session = session_id
        return session

    def get_session(self, session_id: str) -> Optional[CrawlSession]:
        return self._sessions.get(session_id)

    def get_active_session(self) -> Optional[CrawlSession]:
        if self._active_session:
            return self._sessions.get(self._active_session)
        return None

    def set_active(self, session_id: str) -> bool:
        if session_id in self._sessions:
            self._active_session = session_id
            return True
        return False

    def list_sessions(self) -> list[CrawlSession]:
        return list(self._sessions.values())

    def list_active(self) -> list[CrawlSession]:
        return [s for s in self._sessions.values() if s.status == SessionStatus.ACTIVE]

    def remove_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            if self._active_session == session_id:
                self._active_session = None
            return True
        return False

    def save_session(self, session_id: str) -> Optional[str]:
        session = self._sessions.get(session_id)
        if not session or not self._storage_path:
            return None
        path = Path(self._storage_path) / f"{session_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(session.to_dict(), f, indent=2, default=str)
        return str(path)

    def load_session(self, filepath: str) -> Optional[CrawlSession]:
        path = Path(filepath)
        if not path.exists():
            return None
        with open(path) as f:
            data = json.load(f)
        session = CrawlSession(
            session_id=data["session_id"],
            name=data.get("name", ""),
            status=SessionStatus(data.get("status", "active")),
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
        return len(self._sessions)
