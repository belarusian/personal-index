"""Content changelog module - generate changelog from versions."""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class ChangelogFormat(Enum):
    """Output format for changelog."""
    TEXT = "text"
    MARKDOWN = "markdown"
    JSON = "json"


@dataclass
class ChangelogEntry:
    """A single entry in a changelog."""

    content_id: str
    version_number: int
    change_type: str
    message: str
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "version_number": self.version_number,
            "change_type": self.change_type,
            "message": self.message,
            "created_at": self.created_at,
        }


class ChangelogGenerator:
    """Generates changelogs from version history."""

    def __init__(self, format: ChangelogFormat = ChangelogFormat.TEXT):
        self.format = format

    def generate(
        self, content_id: str, entries: list[ChangelogEntry]
    ) -> str:
        """Generate changelog from entries."""
        if not entries:
            return ""

        if self.format == ChangelogFormat.JSON:
            return self._generate_json(content_id, entries)
        elif self.format == ChangelogFormat.MARKDOWN:
            return self._generate_markdown(content_id, entries)
        else:
            return self._generate_text(content_id, entries)

    def _generate_text(self, content_id: str, entries: list[ChangelogEntry]) -> str:
        lines = [f"Changelog for {content_id}", "=" * 40, ""]
        for entry in reversed(entries):
            lines.append(
                f"v{entry.version_number} [{entry.change_type}] "
                f"{entry.message} ({entry.created_at[:10]})"
            )
        lines.append("")
        return "\n".join(lines)

    def _generate_markdown(self, content_id: str, entries: list[ChangelogEntry]) -> str:
        lines = [f"# Changelog for {content_id}", ""]
        for entry in reversed(entries):
            icon = {"created": "+", "modified": "~", "deleted": "-"}.get(
                entry.change_type, "•"
            )
            lines.append(
                f"- **v{entry.version_number}** {icon} {entry.message} "
                f"`{entry.created_at[:10]}`"
            )
        lines.append("")
        return "\n".join(lines)

    def _generate_json(self, content_id: str, entries: list[ChangelogEntry]) -> str:
        data = {
            "content_id": content_id,
            "entries": [e.to_dict() for e in reversed(entries)],
            "total_entries": len(entries),
        }
        return json.dumps(data, indent=2)

    def generate_from_store(
        self,
        content_id: str,
        store: Optional[object] = None,
        limit: Optional[int] = None,
    ) -> str:
        """Generate changelog from a VersionStore."""
        if store is None:
            return ""

        versions = store.get_versions(content_id)
        if not versions:
            return ""

        entries = []
        for v in versions:
            change_type = "created" if v.version_number == 1 else "modified"
            entries.append(
                ChangelogEntry(
                    content_id=content_id,
                    version_number=v.version_number,
                    change_type=change_type,
                    message=v.message or f"Version {v.version_number}",
                    created_at=v.created_at,
                )
            )

        if limit:
            entries = entries[-limit:]

        return self.generate(content_id, entries)

    def generate_all(self, store: Optional[object] = None) -> str:
        """Generate changelog for all content IDs in store."""
        if store is None:
            return ""

        all_ids = store.get_all_content_ids()
        if not all_ids:
            return ""

        parts = []
        for content_id in all_ids:
            changelog = self.generate_from_store(content_id, store)
            if changelog:
                parts.append(changelog)

        return "\n\n".join(parts)

    def generate_summary(
        self, content_id: str, entries: list[ChangelogEntry]
    ) -> dict:
        """Generate a summary of changelog entries."""
        summary = {
            "content_id": content_id,
            "total_changes": len(entries),
            "change_types": {},
            "first_version": None,
            "latest_version": None,
        }

        for entry in entries:
            ct = entry.change_type
            summary["change_types"][ct] = summary["change_types"].get(ct, 0) + 1
            if summary["first_version"] is None:
                summary["first_version"] = entry.version_number
            summary["latest_version"] = entry.version_number

        return summary
