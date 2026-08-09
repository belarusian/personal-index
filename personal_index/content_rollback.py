"""Content rollback module - rollback to previous versions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from personal_index.content_versioning import ContentVersion, VersionStore

logger = logging.getLogger(__name__)


class RollbackError(Exception):
    """Error raised during rollback operations."""

    def __init__(self, message: str, content_id: str = ""):
        self.content_id = content_id
        if content_id:
            message = f"[{content_id}] {message}"
        super().__init__(message)


@dataclass
class RollbackRecord:
    """Record of a rollback operation."""

    content_id: str
    from_version: int
    to_version: int
    reason: str = ""
    rolled_back_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "reason": self.reason,
            "rolled_back_at": self.rolled_back_at,
        }


class RollbackManager:
    """Manages rollback operations for content versions."""

    def __init__(self, max_rollback_history: int = 50):
        self.max_rollback_history = max_rollback_history
        self._versions: dict[str, list[ContentVersion]] = {}
        self._version_counters: dict[str, int] = {}
        self._rollback_history: dict[str, list[RollbackRecord]] = {}

    def save_version(
        self,
        content_id: str,
        content: str,
        title: str = "",
        message: str = "",
        metadata: Optional[dict] = None,
    ) -> ContentVersion:
        """Save a new version of content."""
        if content_id not in self._versions:
            self._versions[content_id] = []
            self._version_counters[content_id] = 0

        # Skip duplicate content
        if self._versions[content_id]:
            latest = self._versions[content_id][-1]
            if latest.content == content:
                return latest

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
        return version

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
        """Get a specific version by number."""
        versions = self._versions.get(content_id, [])
        for v in versions:
            if v.version_number == version_number:
                return v
        return None

    def rollback(
        self, content_id: str, target_version: int, reason: str = ""
    ) -> Optional[RollbackRecord]:
        """Rollback content to a previous version.

        Creates a new version with the content from the target version.
        Returns None if already at target version.
        """
        versions = self._versions.get(content_id, [])
        if not versions:
            raise RollbackError(
                "No versions exist for content", content_id=content_id
            )

        # Find target version
        target = None
        if target_version == 0:
            # Version 0 means the very first version
            target = versions[0]
        else:
            for v in versions:
                if v.version_number == target_version:
                    target = v
                    break

        if target is None:
            raise RollbackError(
                f"Version {target_version} not found", content_id=content_id
            )

        # Check if already at target
        latest = versions[-1]
        if latest.version_number == target.version_number:
            return None

        # Record current version before rollback
        from_version = latest.version_number

        # Create new version with target content
        self._version_counters[content_id] += 1
        new_version_number = self._version_counters[content_id]

        new_version = ContentVersion(
            content_id=content_id,
            version_number=new_version_number,
            content=target.content,
            title=target.title,
            message=f"Rollback to v{target.version_number}: {reason}",
            metadata={
                **target.metadata,
                "rollback_from": from_version,
                "rollback_to": target.version_number,
            },
        )

        self._versions[content_id].append(new_version)

        # Record rollback
        record = RollbackRecord(
            content_id=content_id,
            from_version=from_version,
            to_version=target.version_number,
            reason=reason,
        )

        if content_id not in self._rollback_history:
            self._rollback_history[content_id] = []
        self._rollback_history[content_id].append(record)

        # Enforce max rollback history
        if len(self._rollback_history[content_id]) > self.max_rollback_history:
            self._rollback_history[content_id] = (
                self._rollback_history[content_id][
                    -self.max_rollback_history:
                ]
            )

        return record

    def get_rollback_history(self, content_id: str) -> list[RollbackRecord]:
        """Get rollback history for a content ID."""
        return self._rollback_history.get(content_id, [])

    def get_available_versions(self, content_id: str) -> list[ContentVersion]:
        """Get all available versions for rollback."""
        return self._versions.get(content_id, [])

    def can_rollback(self, content_id: str) -> bool:
        """Check if content can be rolled back."""
        versions = self._versions.get(content_id, [])
        return len(versions) > 1
