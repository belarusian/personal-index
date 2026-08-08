"""Session management for personal-index authentication."""

from __future__ import annotations

import secrets
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional


@dataclass
class Session:
    """Represents an active user session."""
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    user_id: str = ""
    created_at: float = field(default_factory=time.time)
    last_accessed: float = field(default_factory=time.time)
    expires_at: Optional[float] = None
    data: Dict[str, Any] = field(default_factory=dict)
    ip_address: str = ""
    user_agent: str = ""
    is_active: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "expires_at": self.expires_at,
            "data": self.data,
            "ip_address": self.ip_address,
            "user_agent": self.user_agent,
            "is_active": self.is_active,
        }

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        if not self.is_active:
            return True
        if self.expires_at and time.time() > self.expires_at:
            return True
        return False


class SessionStore:
    """In-memory session store with expiration support."""

    def __init__(self, default_ttl: int = 86400, cleanup_interval: int = 3600):
        self._sessions: Dict[str, Session] = {}
        self._default_ttl = default_ttl
        self._cleanup_interval = cleanup_interval
        self._last_cleanup = time.time()

    def create_session(
        self,
        user_id: str,
        ttl: Optional[int] = None,
        ip_address: str = "",
        user_agent: str = "",
        data: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """Create a new session for a user.

        Args:
            user_id: The user identifier.
            ttl: Session time-to-live in seconds.
            ip_address: Client IP address.
            user_agent: Client user agent string.
            data: Initial session data.

        Returns:
            The created Session object.
        """
        session = Session(
            user_id=user_id,
            expires_at=time.time() + (ttl or self._default_ttl),
            ip_address=ip_address,
            user_agent=user_agent,
            data=data or {},
        )
        self._sessions[session.session_id] = session
        self._maybe_cleanup()
        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID, updating last accessed time.

        Args:
            session_id: The session identifier.

        Returns:
            Session if found and valid, None otherwise.
        """
        session = self._sessions.get(session_id)
        if not session or session.is_expired():
            if session:
                self._sessions.pop(session_id, None)
            return None
        session.last_accessed = time.time()
        self._maybe_cleanup()
        return session

    def update_session(
        self,
        session_id: str,
        data: Optional[Dict[str, Any]] = None,
        extend_ttl: Optional[int] = None,
    ) -> bool:
        """Update session data and optionally extend TTL.

        Args:
            session_id: The session identifier.
            data: Data to merge into session.
            extend_ttl: Additional seconds to extend TTL.

        Returns:
            True if session was updated, False if not found.
        """
        session = self._sessions.get(session_id)
        if not session or session.is_expired():
            return False
        if data:
            session.data.update(data)
        if extend_ttl:
            session.expires_at = time.time() + extend_ttl
        session.last_accessed = time.time()
        return True

    def destroy_session(self, session_id: str) -> bool:
        """Destroy a session.

        Args:
            session_id: The session identifier.

        Returns:
            True if session was destroyed, False if not found.
        """
        return self._sessions.pop(session_id, None) is not None

    def destroy_user_sessions(self, user_id: str) -> int:
        """Destroy all sessions for a user.

        Args:
            user_id: The user identifier.

        Returns:
            Number of sessions destroyed.
        """
        to_remove = [
            sid for sid, s in self._sessions.items() if s.user_id == user_id
        ]
        for sid in to_remove:
            del self._sessions[sid]
        return len(to_remove)

    def get_active_count(self, user_id: Optional[str] = None) -> int:
        """Get count of active sessions.

        Args:
            user_id: Filter by user, or None for all.

        Returns:
            Number of active sessions.
        """
        count = 0
        for session in self._sessions.values():
            if not session.is_expired():
                if user_id is None or session.user_id == user_id:
                    count += 1
        return count

    def _maybe_cleanup(self) -> None:
        """Clean up expired sessions if interval has passed."""
        now = time.time()
        if now - self._last_cleanup >= self._cleanup_interval:
            self.cleanup_expired()
            self._last_cleanup = now

    def cleanup_expired(self) -> int:
        """Remove all expired sessions.

        Returns:
            Number of sessions removed.
        """
        expired = [
            sid for sid, s in self._sessions.items() if s.is_expired()
        ]
        for sid in expired:
            del self._sessions[sid]
        return len(expired)
