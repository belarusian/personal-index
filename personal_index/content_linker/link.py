"""Link data model for content linking."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class LinkType(Enum):
    """Type of relationship between content items."""

    TOPIC = "topic"
    KEYWORD = "keyword"
    DOMAIN = "domain"
    TEMPORAL = "temporal"
    CONTENT = "content"


@dataclass
class Link:
    """Represents a relationship between two content items."""

    source_id: str
    target_id: str
    link_type: LinkType = LinkType.CONTENT
    score: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "target_id": self.target_id,
            "link_type": self.link_type.value,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Link:
        lt = data.get("link_type", "content")
        if isinstance(lt, str):
            lt = LinkType(lt)
        return cls(
            source_id=data["source_id"],
            target_id=data["target_id"],
            link_type=lt,
            score=data.get("score", 0.5),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Link):
            return NotImplemented
        return (
            self.source_id == other.source_id
            and self.target_id == other.target_id
            and self.link_type == other.link_type
            and self.score == other.score
        )
