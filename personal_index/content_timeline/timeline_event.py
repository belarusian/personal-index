"""Timeline event data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TimelineEventType(Enum):
    """Type of timeline event."""

    CREATED = "created"
    UPDATED = "updated"
    DELETED = "deleted"
    BOOKMARKED = "bookmarked"
    TAGGED = "tagged"
    SAVED = "saved"
    ARCHIVED = "archived"
    LINKED = "linked"
    SEARCHED = "searched"


@dataclass
class TimelineEvent:
    """Represents an event in the content timeline."""

    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    content_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "system"
    item_id: str = ""
    title: str = ""
    url: str = ""
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Serialize event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "content_id": self.content_id,
            "metadata": self.metadata,
            "source": self.source,
            "item_id": self.item_id,
            "title": self.title,
            "url": self.url,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        """Deserialize event from dictionary."""
        et = data.get("event_type", "created")
        if isinstance(et, str):
            et = TimelineEventType(et)

        ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)

        return cls(
            event_id=data["event_id"],
            event_type=et,
            timestamp=ts,
            content_id=data["content_id"],
            metadata=data.get("metadata", {}),
            source=data.get("source", "system"),
            item_id=data.get("item_id", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, TimelineEvent):
            return NotImplemented
        return self.event_id == other.event_id
