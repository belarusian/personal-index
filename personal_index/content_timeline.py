"""Content timeline module for tracking content history and events.

Provides functionality to build and query timelines of content-related
events such as creation, updates, bookmarks, and crawls.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class TimelineEventType(Enum):
    """Types of events that can appear in a content timeline."""

    CREATED = "created"
    UPDATED = "updated"
    BOOKMARKED = "bookmarked"
    UNBOOKMARKED = "unbookmarked"
    CRAWLED = "crawled"
    INDEXED = "indexed"
    TAGGED = "tagged"
    CATEGORIZED = "categorized"
    SHARED = "shared"
    VIEWED = "viewed"
    DELETED = "deleted"
    RESTORED = "restored"
    SCORE_CHANGED = "score_changed"


@dataclass
class TimelineEvent:
    """A single event in the content timeline.

    Attributes:
        event_id: Unique identifier for the event.
        event_type: Type of the event.
        timestamp: When the event occurred.
        content_id: ID of the content item this event relates to.
        metadata: Additional event-specific data.
        source: Origin of the event (e.g., 'crawler', 'user', 'system').
    """

    event_id: str
    event_type: TimelineEventType
    timestamp: datetime
    content_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    source: str = "system"

    def to_dict(self) -> dict[str, Any]:
        """Convert event to dictionary."""
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "content_id": self.content_id,
            "metadata": self.metadata,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TimelineEvent:
        """Create event from dictionary."""
        return cls(
            event_id=data["event_id"],
            event_type=TimelineEventType(data["event_type"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            content_id=data["content_id"],
            metadata=data.get("metadata", {}),
            source=data.get("source", "system"),
        )


@dataclass
class Timeline:
    """A collection of timeline events for one or more content items.

    Attributes:
        events: List of timeline events.
        content_ids: Set of content IDs in this timeline.
    """

    events: list[TimelineEvent] = field(default_factory=list)
    content_ids: set[str] = field(default_factory=set)

    def add_event(self, event: TimelineEvent) -> None:
        """Add an event to the timeline."""
        self.events.append(event)
        self.content_ids.add(event.content_id)
        self.events.sort(key=lambda e: e.timestamp)

    def get_events_for_content(
        self,
        content_id: str,
    ) -> list[TimelineEvent]:
        """Get all events for a specific content item."""
        return [e for e in self.events if e.content_id == content_id]

    def get_events_by_type(
        self,
        event_type: TimelineEventType,
    ) -> list[TimelineEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TimelineEvent]:
        """Get events within a time range."""
        return [
            e for e in self.events
            if start <= e.timestamp <= end
        ]

    def get_latest_event(
        self,
        content_id: str | None = None,
    ) -> TimelineEvent | None:
        """Get the most recent event, optionally filtered by content."""
        events = (
            self.get_events_for_content(content_id)
            if content_id
            else self.events
        )
        return events[-1] if events else None

    def get_event_count(self) -> int:
        """Get total number of events."""
        return len(self.events)

    def get_content_event_count(self, content_id: str) -> int:
        """Get number of events for a specific content item."""
        return len(self.get_events_for_content(content_id))

    def to_dict(self) -> dict[str, Any]:
        """Convert timeline to dictionary."""
        return {
            "events": [e.to_dict() for e in self.events],
            "content_ids": list(self.content_ids),
            "event_count": len(self.events),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Timeline:
        """Create timeline from dictionary."""
        timeline = cls()
        for event_data in data.get("events", []):
            timeline.add_event(TimelineEvent.from_dict(event_data))
        return timeline
