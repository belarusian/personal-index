"""Content diff module - compare content versions."""

from __future__ import annotations

import difflib
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

logger = logging.getLogger(__name__)


class DiffType(Enum):
    """Type of diff line."""
    ADDED = "added"
    REMOVED = "removed"
    UNCHANGED = "unchanged"


@dataclass
class DiffLine:
    """A single line in a diff result."""

    diff_type: DiffType
    line_number: int
    text: str

    def to_dict(self) -> dict:
        return {
            "diff_type": self.diff_type.value,
            "line_number": self.line_number,
            "text": self.text,
        }


@dataclass
class DiffResult:
    """Result of a content diff operation."""

    content_id: str = ""
    from_version: int = 0
    to_version: int = 0
    lines: list[DiffLine] = field(default_factory=list)
    summary: dict = field(default_factory=lambda: {
        "added": 0, "removed": 0, "unchanged": 0
    })

    @property
    def has_changes(self) -> bool:
        return self.added_count > 0 or self.removed_count > 0

    @property
    def added_count(self) -> int:
        return sum(1 for l in self.lines if l.diff_type == DiffType.ADDED)

    @property
    def removed_count(self) -> int:
        return sum(1 for l in self.lines if l.diff_type == DiffType.REMOVED)

    @property
    def unchanged_count(self) -> int:
        return sum(1 for l in self.lines if l.diff_type == DiffType.UNCHANGED)

    def to_dict(self) -> dict:
        return {
            "content_id": self.content_id,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "lines": [l.to_dict() for l in self.lines],
            "summary": self.summary,
            "has_changes": self.has_changes,
        }

    def get_unified_format(
        self, from_file: str = "old.txt", to_file: str = "new.txt"
    ) -> str:
        """Generate unified diff format string."""
        lines = []
        lines.append(f"--- {from_file}")
        lines.append(f"+++ {to_file}")
        for line in self.lines:
            if line.diff_type == DiffType.ADDED:
                lines.append(f"+{line.text}")
            elif line.diff_type == DiffType.REMOVED:
                lines.append(f"-{line.text}")
            else:
                lines.append(f" {line.text}")
        return "\n".join(lines)

    def get_stats(self) -> dict:
        """Get diff statistics."""
        return {
            "added": self.added_count,
            "removed": self.removed_count,
            "unchanged": self.unchanged_count,
            "total_lines": len(self.lines),
            "has_changes": self.has_changes,
        }


class DiffEngine:
    """Engine for computing diffs between content versions."""

    def __init__(self, context_lines: int = 3):
        self.context_lines = context_lines

    def diff(
        self,
        old_content: str,
        new_content: str,
        content_id: str = "",
        from_version: int = 0,
        to_version: int = 0,
    ) -> DiffResult:
        """Compute diff between old and new content."""
        old_lines = old_content.splitlines(keepends=False) if old_content else []
        new_lines = new_content.splitlines(keepends=False) if new_content else []

        matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
        diff_lines = []
        old_line_num = 0
        new_line_num = 0

        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == "equal":
                for idx in range(i1, i2):
                    diff_lines.append(DiffLine(
                        DiffType.UNCHANGED, idx + 1, old_lines[idx]
                    ))
            elif tag == "replace":
                for idx in range(i1, i2):
                    diff_lines.append(DiffLine(
                        DiffType.REMOVED, idx + 1, old_lines[idx]
                    ))
                for idx in range(j1, j2):
                    diff_lines.append(DiffLine(
                        DiffType.ADDED, idx + 1, new_lines[idx]
                    ))
            elif tag == "delete":
                for idx in range(i1, i2):
                    diff_lines.append(DiffLine(
                        DiffType.REMOVED, idx + 1, old_lines[idx]
                    ))
            elif tag == "insert":
                for idx in range(j1, j2):
                    diff_lines.append(DiffLine(
                        DiffType.ADDED, idx + 1, new_lines[idx]
                    ))

        summary = {
            "added": sum(1 for l in diff_lines if l.diff_type == DiffType.ADDED),
            "removed": sum(1 for l in diff_lines if l.diff_type == DiffType.REMOVED),
            "unchanged": sum(1 for l in diff_lines if l.diff_type == DiffType.UNCHANGED),
        }

        return DiffResult(
            content_id=content_id,
            from_version=from_version,
            to_version=to_version,
            lines=diff_lines,
            summary=summary,
        )

    def diff_versions(
        self,
        old_version: Optional[object],
        new_version: Optional[object],
        content_id: str = "",
    ) -> DiffResult:
        """Diff between two version objects (ContentVersion instances)."""
        old_content = old_version.content if old_version else ""
        new_content = new_version.content if new_version else ""
        from_version = old_version.version_number if old_version else 0
        to_version = new_version.version_number if new_version else 0

        return self.diff(
            old_content, new_content,
            content_id=content_id,
            from_version=from_version,
            to_version=to_version,
        )
