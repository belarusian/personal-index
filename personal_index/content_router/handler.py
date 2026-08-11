"""Content handler base class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass
class ContentHandler(ABC):
    """Abstract base class for content handlers.

    Attributes:
        name: Handler name.
        supported_types: Content types this handler supports.
    """

    name: str = "default"
    supported_types: list[str] | None = None

    def __post_init__(self) -> None:
        if self.supported_types is None:
            self.supported_types = ["*"]

    @abstractmethod
    def handle(self, content: dict[str, Any]) -> dict[str, Any]:
        """Handle a content item.

        Args:
            content: Content item to process.

        Returns:
            Processed content item.
        """
        ...

    def can_handle(self, content: dict[str, Any]) -> bool:
        """Check if this handler can process the content.

        Args:
            content: Content item to check.

        Returns:
            True if handler supports this content type.
        """
        content_type = content.get("type", "unknown")
        assert self.supported_types is not None
        return "*" in self.supported_types or content_type in self.supported_types


class PassThroughHandler(ContentHandler):
    """Handler that passes content through unchanged."""

    def __post_init__(self) -> None:
        self.name = "passthrough"
        self.supported_types = ["*"]

    def handle(self, content: dict[str, Any]) -> dict[str, Any]:
        return dict(content)


class TypeHandler(ContentHandler):
    """Handler that processes content based on type."""

    def __post_init__(self) -> None:
        self.name = "type_handler"

    def handle(self, content: dict[str, Any]) -> dict[str, Any]:
        result = dict(content)
        result["processed_by"] = self.name
        result["content_type"] = content.get("type", "unknown")
        return result
