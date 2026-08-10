"""Content diff comparison module."""

from __future__ import annotations

from dataclasses import dataclass, field
from difflib import unified_diff
from typing import Any


@dataclass
class DiffResult:
    """Result of comparing two content versions."""

    url: str
    added_lines: int = 0
    removed_lines: int = 0
    changed_lines: int = 0
    diff_text: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


def compute_diff(old_content: str, new_content: str, url: str = "") -> DiffResult:
    """Compute the diff between two content versions."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)

    diff_lines = list(unified_diff(old_lines, new_lines, fromfile="old", tofile="new"))
    diff_text = "".join(diff_lines)

    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    changed = min(added, removed)

    return DiffResult(
        url=url,
        added_lines=added,
        removed_lines=removed,
        changed_lines=changed,
        diff_text=diff_text,
    )
