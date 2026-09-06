"""Content versioning and change detection."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


@dataclass
class ContentVersion:
    """A versioned snapshot of content."""

    url: str
    version_id: str
    content_hash: str
    title: str = ""
    content_length: int = 0
    captured_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        """Serialize this ContentVersion to a plain dict.

        Returns a NEW dict (a fresh object on every call, not a
        shared reference) containing exactly the seven ContentVersion
        fields as keys, in dataclass declaration order: url,
        version_id, content_hash, title, content_length, captured_at,
        metadata. The captured_at datetime is serialized to an
        ISO-8601 string via .isoformat(); all other values are the
        corresponding field values. The metadata dict is the SAME
        reference as self.metadata (not copied). The method is pure:
        it does not mutate self.
        """
        return {
            "url": self.url,
            "version_id": self.version_id,
            "content_hash": self.content_hash,
            "title": self.title,
            "content_length": self.content_length,
            "captured_at": self.captured_at.isoformat(),
            "metadata": self.metadata,
        }


class VersionTracker:
    """Tracks content versions and detects changes."""

    def __init__(self, max_versions: int = 10):
        self._versions: dict[str, list[ContentVersion]] = {}
        self._max_versions = max_versions

    @staticmethod
    def compute_hash(content: str) -> str:
        """Compute SHA-256 hash of content."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def generate_version_id(url: str, hash_value: str) -> str:
        """Generate a unique version ID from URL and content hash."""
        combined = f"{url}:{hash_value}"
        return hashlib.sha256(combined.encode()).hexdigest()[:12]

    def record_version(self, url: str, content: str, title: str = "",
                       metadata: dict | None = None) -> ContentVersion:
        """Record a new version of content for a URL."""
        content_hash = self.compute_hash(content)
        version_id = self.generate_version_id(url, content_hash)

        version = ContentVersion(
            url=url,
            version_id=version_id,
            content_hash=content_hash,
            title=title,
            content_length=len(content),
            metadata=metadata or {},
        )

        if url not in self._versions:
            self._versions[url] = []

        # Avoid recording duplicate consecutive versions
        if self._versions[url] and self._versions[url][-1].content_hash == content_hash:
            return self._versions[url][-1]

        self._versions[url].append(version)

        # Enforce max versions
        if len(self._versions[url]) > self._max_versions:
            self._versions[url] = self._versions[url][-self._max_versions:]

        return version

    def get_versions(self, url: str) -> list[ContentVersion]:
        """Get all versions for a URL."""
        return self._versions.get(url, [])

    def get_latest(self, url: str) -> ContentVersion | None:
        """Get the latest version for a URL."""
        versions = self._versions.get(url, [])
        return versions[-1] if versions else None

    def has_changed(self, url: str, new_content: str) -> bool:
        """Check if new content differs from the latest version."""
        latest = self.get_latest(url)
        if latest is None:
            return True
        new_hash = self.compute_hash(new_content)
        return new_hash != latest.content_hash

    def get_change_count(self, url: str) -> int:
        """Get the number of version changes for a URL."""
        return len(self._versions.get(url, []))

    def get_all_urls(self) -> list[str]:
        """Get all tracked URLs."""
        return list(self._versions.keys())

    def clear(self, url: str | None = None) -> None:
        """Clear versions for a URL or all URLs."""
        if url:
            self._versions.pop(url, None)
        else:
            self._versions.clear()

    @property
    def total_versions(self) -> int:
        """Total number of versions tracked."""
        return sum(len(v) for v in self._versions.values())

    @property
    def tracked_urls(self) -> int:
        """Number of URLs being tracked."""
        return len(self._versions)
