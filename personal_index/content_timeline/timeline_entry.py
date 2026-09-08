"""Timeline entry data model."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class TimelineEventType(Enum):
    """Type of timeline event."""

    SAVED = "saved"
    TAGGED = "tagged"
    ARCHIVED = "archived"
    LINKED = "linked"
    SEARCHED = "searched"


@dataclass
class TimelineEntry:
    """Represents an event in the content timeline."""

    item_id: str
    timestamp: datetime
    title: str = ""
    event_type: TimelineEventType = TimelineEventType.SAVED
    url: str = ""
    description: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize the entry to a dict.

        No guard path: always computes.

        Returns a dict with exactly the keys:
          * ``item_id``     -> ``self.item_id``
          * ``title``       -> ``self.title``
          * ``event_type``  -> ``self.event_type.value``
          * ``timestamp``   -> ``self.timestamp.isoformat()``
          * ``url``         -> ``self.url``
          * ``description`` -> ``self.description``
          * ``metadata``    -> ``self.metadata``
        No side effects.
        """
        return {
            "item_id": self.item_id,
            "title": self.title,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "url": self.url,
            "description": self.description,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEntry:
        """Deserialize an entry from a dict.

        No guard path: always constructs.

        Returns a new ``TimelineEntry`` with:
          * ``item_id``     -> ``data["item_id"]`` (required key)
          * ``timestamp``   -> ``data.get("timestamp", now-utc-iso)``; if a
            string, parsed via ``datetime.fromisoformat``; on ``ValueError``
            (or a non-string value) it degrades to ``datetime.now(timezone.utc)``
          * ``title``       -> ``data.get("title", "")``
          * ``event_type``  -> ``data.get("event_type", "saved")``; if a
            string, converted via ``TimelineEventType(et)``
          * ``url``         -> ``data.get("url", "")``
          * ``description`` -> ``data.get("description", "")``
          * ``metadata``    -> ``data.get("metadata", {})``
        No side effects beyond constructing the returned object.
        """
        et = data.get("event_type", "saved")
        if isinstance(et, str):
            et = TimelineEventType(et)

        ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts)
            except ValueError:
                ts = datetime.now(timezone.utc)

        return cls(
            item_id=data["item_id"],
            timestamp=ts,
            title=data.get("title", ""),
            event_type=et,
            url=data.get("url", ""),
            description=data.get("description", ""),
            metadata=data.get("metadata", {}),
        )

    def __eq__(self, other: object) -> bool:
        """Compare two entries for equality.

        Guard path: if ``other`` is not a ``TimelineEntry``, returns
        ``NotImplemented``.

        For a ``TimelineEntry`` ``other``, returns ``True`` iff
        ``self.item_id == other.item_id`` AND ``self.timestamp ==
        other.timestamp`` (all other fields are ignored). No side effects.
        """
        if not isinstance(other, TimelineEntry):
            return NotImplemented
        return (
            self.item_id == other.item_id
            and self.timestamp == other.timestamp
        )
