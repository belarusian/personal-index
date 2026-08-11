"""Content source definitions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceConfig:
    """Configuration for a content source.

    Attributes:
        name: Source name.
        enabled: Whether the source is enabled.
        priority: Source priority.
        refresh_interval: Refresh interval in seconds.
        options: Additional source options.
    """

    name: str
    enabled: bool = True
    priority: int = 0
    refresh_interval: int = 3600
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentSource:
    """A source of content items.

    Attributes:
        config: Source configuration.
        items: Content items from this source.
    """

    config: SourceConfig
    items: list[dict[str, Any]] = field(default_factory=list)

    def add_items(self, items: list[dict[str, Any]]) -> None:
        """Add items to this source.

        Args:
            items: Content items to add.
        """
        self.items.extend(items)

    def get_items(self) -> list[dict[str, Any]]:
        """Get all items from this source.

        Returns:
            List of content items.
        """
        return list(self.items)

    def clear(self) -> None:
        """Clear all items from this source."""
        self.items.clear()

    @property
    def item_count(self) -> int:
        """Number of items in this source."""
        return len(self.items)
