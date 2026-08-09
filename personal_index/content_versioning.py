"""Content versioning module - version control for saved content."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class ContentVersion:
    """A versioned snapshot of content."""

    content_id: str
    version_number: int
    content: str
    title: str = ""
    message: str = ""
    is_pinned: bool = False
    metadata: dict = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def content_hash(self) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(self.content.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "version_number": self.version_number,
            "content": self.content,
            "title": self.title,
            "content_hash": self.content_hash,
            "created_at": self.created_at,
            "message": self.message,
            "is_pinned": self.is_pinned,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ContentVersion":
        return cls(
            content_id=data["content_id"],
            version_number=data["version_number"],
            content=data["content"],
            title=data.get("title", ""),
            message=data.get("message", ""),
            is_pinned=data.get("is_pinned", False),
            metadata=data.get("metadata", {}),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
        )


@dataclass
class VersionRecord:
    """Record of a version save operation."""

    content_id: str
    version_number: int
    content: str
    title: str = ""
    message: str = ""
    metadata: dict = field(default_factory=dict)
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "version_number": self.version_number,
            "content": self.content,
            "title": self.title,
            "message": self.message,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class VersionStore:
    """Manages content versions with version control capabilities."""

    def __init__(self, max_versions: int = 10):
        self.max_versions = max_versions
        self._versions: dict[str, list[ContentVersion]] = {}
        self._version_counters: dict[str, int] = {}

    def save_version(
        self,
        content_id: str,
        content: str,
        title: str = "",
        message: str = "",
        metadata: Optional[dict] = None,
    ) -> VersionRecord:
        """Save a new version of content.

        Skips saving if content is identical to the latest version.
        """
        if content_id not in self._versions:
            self._versions[content_id] = []
            self._version_counters[content_id] = 0

        # Skip duplicate content
        if self._versions[content_id]:
            latest = self._versions[content_id][-1]
            if latest.content == content:
                record = VersionRecord(
                    content_id=content_id,
                    version_number=latest.version_number,
                    content=content,
                    title=latest.title or title,
                    message=latest.message or message,
                    metadata=latest.metadata or (metadata or {}),
                )
                return record

        self._version_counters[content_id] += 1
        version_number = self._version_counters[content_id]

        version = ContentVersion(
            content_id=content_id,
            version_number=version_number,
            content=content,
            title=title,
            message=message,
            metadata=metadata or {},
        )

        self._versions[content_id].append(version)

        # Enforce max versions
        if len(self._versions[content_id]) > self.max_versions:
            self._versions[content_id] = self._versions[content_id][
                -self.max_versions:
            ]

        record = VersionRecord(
            content_id=content_id,
            version_number=version_number,
            content=content,
            title=title,
            message=message,
            metadata=metadata or {},
        )
        return record

    def get_versions(self, content_id: str) -> list[ContentVersion]:
        """Get all versions for a content ID."""
        return self._versions.get(content_id, [])

    def get_latest(self, content_id: str) -> Optional[ContentVersion]:
        """Get the latest version for a content ID."""
        versions = self._versions.get(content_id, [])
        return versions[-1] if versions else None

    def get_version_by_number(
        self, content_id: str, version_number: int
    ) -> Optional[ContentVersion]:
        """Get a specific version by its version number."""
        versions = self._versions.get(content_id, [])
        for v in versions:
            if v.version_number == version_number:
                return v
        return None

    def get_all_content_ids(self) -> list[str]:
        """Get all content IDs that have versions."""
        return list(self._versions.keys())

    def version_count(self, content_id: str) -> int:
        """Get the number of versions for a content ID."""
        return len(self._versions.get(content_id, []))

    def clear(self, content_id: str) -> None:
        """Clear all versions for a content ID."""
        self._versions.pop(content_id, None)
        self._version_counters.pop(content_id, None)

    def clear_all(self) -> None:
        """Clear all versions for all content IDs."""
        self._versions.clear()
        self._version_counters.clear()

    def has_versions(self, content_id: str) -> bool:
        """Check if a content ID has any versions."""
        return bool(self._versions.get(content_id, []))
