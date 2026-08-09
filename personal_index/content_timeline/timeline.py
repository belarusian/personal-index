"""Timeline manager for chronological content view."""

from __future__ import annotations

from datetime import date, datetime, timezone, timedelta
from typing import Any

from personal_index.content_timeline.timeline_entry import TimelineEntry, TimelineEventType


class Timeline:
    """Manages chronological timeline of content events."""

    def __init__(self) -> None:
        self.entries: list[TimelineEntry] = []

    def add_event(
        self,
        item_id: str,
        title: str,
        event_type: TimelineEventType = TimelineEventType.SAVED,
        timestamp: datetime | None = None,
        url: str = "",
        description: str = "",
        metadata: dict[str, Any] | None = None,
    ) -> TimelineEntry:
        """Add an event to the timeline."""
        entry = TimelineEntry(
            item_id=item_id,
            title=title,
            event_type=event_type,
            timestamp=timestamp or datetime.now(timezone.utc),
            url=url,
            description=description,
            metadata=metadata or {},
        )
        self._add_entry(entry)
        return entry

    def _add_entry(self, entry: TimelineEntry) -> None:
        """Add entry maintaining sorted order (newest first)."""
        self.entries.append(entry)
        self.entries.sort(key=lambda e: e.timestamp, reverse=True)

    def filter_by_type(self, event_type: TimelineEventType) -> list[TimelineEntry]:
        """Filter entries by event type."""
        return [e for e in self.entries if e.event_type == event_type]

    def filter_by_date_range(
        self,
        start: datetime,
        end: datetime,
    ) -> list[TimelineEntry]:
        """Filter entries within a date range."""
        return [
            e for e in self.entries
            if start <= e.timestamp <= end
        ]

    def filter_by_item_id(self, item_id: str) -> list[TimelineEntry]:
        """Filter entries by item ID."""
        return [e for e in self.entries if e.item_id == item_id]

    def get_events_for_day(self, day: date) -> list[TimelineEntry]:
        """Get all events for a specific day."""
        start = datetime(day.year, day.month, day.day, tzinfo=timezone.utc)
        end = start + timedelta(days=1)
        return [
            e for e in self.entries
            if start <= e.timestamp < end
        ]

    def get_events_for_week(self, week_start: date) -> list[TimelineEntry]:
        """Get all events for a week starting from the given date."""
        start = datetime(week_start.year, week_start.month, week_start.day, tzinfo=timezone.utc)
        end = start + timedelta(weeks=1)
        return [
            e for e in self.entries
            if start <= e.timestamp < end
        ]

    def get_events_for_month(
        self, year: int, month: int
    ) -> list[TimelineEntry]:
        """Get all events for a specific month."""
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        if month == 12:
            end = datetime(year + 1, 1, 1, tzinfo=timezone.utc)
        else:
            end = datetime(year, month + 1, 1, tzinfo=timezone.utc)
        return [
            e for e in self.entries
            if start <= e.timestamp < end
        ]

    def clear(self) -> None:
        """Clear all timeline entries."""
        self.entries.clear()

    def get_summary(self) -> dict[str, Any]:
        """Get a summary of timeline events."""
        type_counts: dict[str, int] = {}
        for entry in self.entries:
            key = entry.event_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "total_events": len(self.entries),
            "by_type": type_counts,
            "unique_items": len(set(e.item_id for e in self.entries)),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize timeline to dict."""
        return {
            "entries": [e.to_dict() for e in self.entries],
            "summary": self.get_summary(),
        }
