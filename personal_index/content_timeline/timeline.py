"""Timeline manager for chronological content view."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Any

from personal_index.content_timeline.timeline_entry import TimelineEntry, TimelineEventType as EntryEventType
from personal_index.content_timeline.timeline_event import TimelineEvent, TimelineEventType


class Timeline:
    """Manages chronological timeline of content events."""

    def __init__(self) -> None:
        self.events: list[TimelineEvent] = []
        self.entries: list[TimelineEntry] = []

    def add_event(self, event: TimelineEvent) -> None:
        """Add a TimelineEvent to the timeline, maintaining sort order."""
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def add_entry(
        self,
        item_id: str,
        title: str,
        event_type: EntryEventType = EntryEventType.SAVED,
        timestamp: datetime | None = None,
        url: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEntry:
        """Add a TimelineEntry to the timeline."""
        entry = TimelineEntry(
            item_id=item_id,
            title=title,
            event_type=event_type,
            timestamp=timestamp or datetime.now(timezone.utc),
            url=url,
            description=description,
            metadata=metadata or {},
        )
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.timestamp, reverse=True)
        return entry

    @property
    def content_ids(self) -> set[str]:
        """Get all unique content IDs."""
        return {e.content_id for e in self.events}

    def get_event_count(self) -> int:
        """Get total number of events."""
        return len(self.events)

    def get_events_for_content(self, content_id: str) -> list[TimelineEvent]:
        """Get all events for a specific content item."""
        return [e for e in self.events if e.content_id == content_id]

    def get_events_by_type(self, event_type: TimelineEventType) -> list[TimelineEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self, start: datetime, end: datetime
    ) -> list[TimelineEvent]:
        """Get events within a time range."""
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_latest_event(self, content_id: str | None = None) -> TimelineEvent | None:
        """Get the latest event, optionally filtered by content ID."""
        if content_id is not None:
            filtered = [e for e in self.events if e.content_id == content_id]
            if not filtered:
                return None
            return filtered[-1]
        if not self.events:
            return None
        return self.events[-1]

    def get_content_event_count(self, content_id: str) -> int:
        """Get the number of events for a specific content item."""
        return len(self.get_events_for_content(content_id))

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline to dict."""
        return {
            "events": [e.to_dict() for e in self.events],
            "event_count": self.get_event_count(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Timeline:
        """Deserialize timeline from dict."""
        timeline = cls()
        for event_data in data.get("events", []):
            event = TimelineEvent.from_dict(event_data)
            timeline.events.append(event)
        timeline.events.sort(key=lambda e: e.timestamp)
        return timeline
