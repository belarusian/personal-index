"""Content pin module - pin important content versions."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from personal_index.content_versioning import ContentVersion
from personal_index.content_rollback import RollbackError

logger = logging.getLogger(__name__)


class PinError(Exception):
    """Error raised during pin operations."""

    def __init__(self, message: str, content_id: str = ""):
        self.content_id = content_id
        if content_id:
            message = f"[{content_id}] {message}"
        super().__init__(message)


@dataclass
class PinnedVersion:
    """A pinned version of content."""

    content_id: str
    version_number: int
    pinned_by: str = "system"
    reason: str = ""
    pinned_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "version_number": self.version_number,
            "pinned_by": self.pinned_by,
            "reason": self.reason,
            "pinned_at": self.pinned_at,
        }


class PinManager:
    """Manages pinned versions of content."""

    def __init__(self, max_pins_per_content: int = 10):
        self.max_pins_per_content = max_pins_per_content
        self._versions: dict[str, list[ContentVersion]] = {}
        self._version_counters: dict[str, int] = {}
        self._pins: dict[str, list[PinnedVersion]] = {}

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
    ) -> Optional[object]:
        """Rollback content to a previous version."""
        versions = self._versions.get(content_id, [])
        if not versions:
            raise RollbackError(
                "No versions exist for content", content_id=content_id
            )

        target = None
        if target_version == 0:
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

        latest = versions[-1]
        if latest.version_number == target.version_number:
            return None

        from_version = latest.version_number

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
        return new_version

    def pin(
        self,
        content_id: str,
        version_number: int,
        pinned_by: str = "system",
        reason: str = "",
    ) -> PinnedVersion:
        """Pin a specific version of content."""
        versions = self._versions.get(content_id, [])
        if not versions:
            raise PinError("No versions exist for content", content_id=content_id)

        # Find the version
        target = None
        for v in versions:
            if v.version_number == version_number:
                target = v
                break

        if target is None:
            raise PinError(
                f"Version {version_number} not found", content_id=content_id
            )

        # Check if already pinned
        if content_id not in self._pins:
            self._pins[content_id] = []

        for pin in self._pins[content_id]:
            if pin.version_number == version_number:
                raise PinError(
                    f"Version {version_number} is already pinned",
                    content_id=content_id,
                )

        # Check max pins
        if len(self._pins[content_id]) >= self.max_pins_per_content:
            raise PinError(
                f"Maximum pins ({self.max_pins_per_content}) reached",
                content_id=content_id,
            )

        pinned = PinnedVersion(
            content_id=content_id,
            version_number=version_number,
            pinned_by=pinned_by,
            reason=reason,
        )

        self._pins[content_id].append(pinned)

        # Mark version as pinned
        target.is_pinned = True

        return pinned

    def unpin(self, content_id: str, version_number: int) -> None:
        """Unpin a specific version of content."""
        if content_id not in self._pins:
            raise PinError(
                f"No pins exist for content", content_id=content_id
            )

        # Check if the version is actually pinned
        was_pinned = False
        new_pins = []
        for p in self._pins[content_id]:
            if p.version_number == version_number:
                was_pinned = True
            else:
                new_pins.append(p)

        if not was_pinned:
            raise PinError(
                f"Version {version_number} is not pinned", content_id=content_id
            )

        self._pins[content_id] = new_pins

    def get_pins(self, content_id: str) -> list[PinnedVersion]:
        """Get all pins for a content ID."""
        return self._pins.get(content_id, [])

    def is_pinned(self, content_id: str, version_number: int) -> bool:
        """Check if a specific version is pinned."""
        pins = self._pins.get(content_id, [])
        return any(p.version_number == version_number for p in pins)

    def get_all_pins(self) -> list[PinnedVersion]:
        """Get all pins across all content IDs."""
        all_pins = []
        for pins in self._pins.values():
            all_pins.extend(pins)
        return all_pins

    def pin_count(self, content_id: str) -> int:
        """Get the number of pins for a content ID."""
        return len(self._pins.get(content_id, []))

    def get_pinned_content(
        self, content_id: str, version_number: int
    ) -> Optional[str]:
        """Get the content of a pinned version."""
        version = self.get_version_by_number(content_id, version_number)
        if version:
            return version.content
        return None

    def unpin_all(self, content_id: str) -> None:
        """Remove all pins for a content ID."""
        self._pins.pop(content_id, None)
