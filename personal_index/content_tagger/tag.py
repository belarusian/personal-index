"""Tag data model for content tagging."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Tag:
    """Represents a detected topic tag with confidence score."""

    name: str
    confidence: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "confidence": self.confidence}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Tag:
        return cls(name=data["name"], confidence=data.get("confidence", 0.5))

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Tag):
            return NotImplemented
        return self.name == other.name and self.confidence == other.confidence
