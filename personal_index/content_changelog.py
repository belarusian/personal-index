"""Content changelog tracking module."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ChangeEntry:
    """A single change entry in the changelog."""

    url: str
    change_type: str
    timestamp: str
    details: dict[str, Any] = field(default_factory=dict)


class ContentChangelog:
    """Track content changes over time."""

    def __init__(self) -> None:
        self._entries: list[ChangeEntry] = []

    def add_entry(self, entry: ChangeEntry) -> None:
        """Add a change entry."""
        self._entries.append(entry)

    def get_entries(self, url: str | None = None) -> list[ChangeEntry]:
        """Return change entries, optionally filtered by exact URL.

        Args:
            url: When truthy, only entries whose ``e.url`` equals ``url``
                (exact string match, not substring or prefix) are returned.
                When falsy (``None`` or empty string), ALL entries are
                returned.

        Returns:
            A NEW list of ``ChangeEntry`` objects (a copy, not the internal
            list) - the filtered subset when ``url`` is truthy, otherwise a
            copy of every stored entry. An empty changelog returns an empty
            list in both cases.
        """
        if url:
            return [e for e in self._entries if e.url == url]
        return list(self._entries)

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()
