"""Timeline manager for chronological content view."""

from __future__ import annotations

import calendar
from datetime import date, datetime, timedelta, timezone
from typing import Any

from personal_index.content_timeline.timeline_entry import TimelineEntry
from personal_index.content_timeline.timeline_entry import TimelineEventType as EntryEventType
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
        """Add a TimelineEntry to the timeline.

        Builds a TimelineEntry from the given fields, defaulting
        ``timestamp`` to ``datetime.now(timezone.utc)`` when omitted and
        ``metadata`` to ``{}`` when omitted, appends it to
        ``self.entries``, re-sorts ``self.entries`` in reverse
        (newest-first) order by timestamp, and returns the created entry.
        """
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


    def get_events_for_day(self, d: date) -> list[TimelineEvent]:
        """Get events for a specific day."""
        start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        end = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_for_week(self, d: date) -> list[TimelineEvent]:
        """Get events for the week containing the given date."""
        # Monday of the week
        monday = d - timedelta(days=d.weekday())
        start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
        # Sunday end of week
        sunday = monday + timedelta(days=6)
        end = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_for_month(self, year: int, month: int) -> list[TimelineEvent]:
        """Get events for a specific month."""
        last_day = calendar.monthrange(year, month)[1]
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of the timeline."""
        return {
            "total_events": len(self.events),
            "total_entries": len(self.entries),
            "content_ids": list(self.content_ids),
        }

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
