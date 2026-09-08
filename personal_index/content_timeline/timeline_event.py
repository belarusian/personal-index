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
        """Serialize the event to a dict.

        No guard path: always computes.

        Returns a dict with exactly the keys:
          * ``event_id``    -> ``self.event_id``
          * ``event_type``  -> ``self.event_type.value``
          * ``timestamp``   -> ``self.timestamp.isoformat()``
          * ``content_id``  -> ``self.content_id``
          * ``metadata``    -> ``self.metadata``
          * ``source``      -> ``self.source``
          * ``item_id``     -> ``self.item_id``
          * ``title``       -> ``self.title``
          * ``url``         -> ``self.url``
          * ``description`` -> ``self.description``
        No side effects.
        """
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
        """Deserialize an event from a dict.

        No guard path: always constructs.

        Returns a new ``TimelineEvent`` with:
          * ``event_id``    -> ``data.get("event_id", "")``
          * ``event_type``  -> ``data.get("event_type", "created")``; if a
            string, converted via ``TimelineEventType(et)``
          * ``timestamp``   -> ``data.get("timestamp", now-utc-iso)``; if a
            string, parsed via ``datetime.fromisoformat``; on ``ValueError``
            (or a non-string value) it degrades to ``datetime.now(timezone.utc)``
          * ``content_id``  -> ``data.get("content_id", "")``
          * ``metadata``    -> ``data.get("metadata", {})``
          * ``source``      -> ``data.get("source", "system")``
          * ``item_id``     -> ``data.get("item_id", "")``
          * ``title``       -> ``data.get("title", "")``
          * ``url``         -> ``data.get("url", "")``
          * ``description`` -> ``data.get("description", "")``
        No side effects beyond constructing the returned object.
        """
        et = data.get("event_type", "created")
        if isinstance(et, str):
            et = TimelineEventType(et)

        ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)

        return cls(
            event_id=data.get("event_id", ""),
            event_type=et,
            timestamp=ts,
            content_id=data.get("content_id", ""),
            metadata=data.get("metadata", {}),
            source=data.get("source", "system"),
            item_id=data.get("item_id", ""),
            title=data.get("title", ""),
            url=data.get("url", ""),
            description=data.get("description", ""),
        )

    def __eq__(self, other: object) -> bool:
        """Compare two events for equality.

        Guard path: if ``other`` is not a ``TimelineEvent``, returns
        ``NotImplemented``.

        For a ``TimelineEvent`` ``other``, returns ``True`` iff
        ``self.event_id == other.event_id`` (all other fields are ignored).
        No side effects.
        """
        if not isinstance(other, TimelineEvent):
            return NotImplemented
        return self.event_id == other.event_id
