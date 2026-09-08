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
        """Initialize an empty timeline.

        No guard path: always constructs.

        Returns ``None``. Side effects: sets ``self.events = []`` and
        ``self.entries = []``.
        """
        self.events: list[TimelineEvent] = []
        self.entries: list[TimelineEntry] = []

    def add_event(self, event: TimelineEvent) -> None:
        """Add a TimelineEvent to the timeline, maintaining ascending order.

        No guard path: always appends.

        Returns ``None``. Side effects: appends ``event`` to ``self.events``
        and re-sorts ``self.events`` in ascending order by ``timestamp``.
        """
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
        """Return the set of unique content IDs referenced by stored events.

        No guard path: always computes.

        Returns ``{e.content_id for e in self.events}``. No side effects.
        """
        return {e.content_id for e in self.events}

    def get_event_count(self) -> int:
        """Return the total number of stored events.

        No guard path: always computes.

        Returns ``len(self.events)``. No side effects.
        """
        return len(self.events)

    def get_events_for_content(self, content_id: str) -> list[TimelineEvent]:
        """Return the stored events whose content_id equals the given ID.

        No guard path: always computes (returns an empty list when no event
        matches).

        Returns ``[e for e in self.events if e.content_id == content_id]``,
        preserving ``self.events`` order (ascending by timestamp). No side
        effects.
        """
        return [e for e in self.events if e.content_id == content_id]

    def get_events_by_type(self, event_type: TimelineEventType) -> list[TimelineEvent]:
        """Return the stored events whose event_type equals the given type.

        No guard path: always computes (returns an empty list when no event
        matches).

        Returns ``[e for e in self.events if e.event_type == event_type]``,
        preserving ``self.events`` order (ascending by timestamp). No side
        effects.
        """
        return [e for e in self.events if e.event_type == event_type]

    def get_events_in_range(
        self, start: datetime, end: datetime
    ) -> list[TimelineEvent]:
        """Return the stored events within the inclusive time range.

        No guard path: always computes (returns an empty list when no event
        falls in the range).

        An event is returned iff ``start <= e.timestamp <= end`` (inclusive
        on both ends). The result preserves ``self.events`` order (ascending
        by timestamp). No side effects.
        """
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_latest_event(self, content_id: str | None = None) -> TimelineEvent | None:
        """Return the latest stored event, optionally filtered by content ID.

        Guard path: if ``content_id`` is not None and no stored event has
        that content_id, returns ``None``.

        Guard path: if ``content_id`` is None and ``self.events`` is empty,
        returns ``None``.

        For ``content_id`` not None with a match, returns the last (latest)
        event among those whose ``content_id`` equals the given ID. For
        ``content_id`` None with a non-empty timeline, returns
        ``self.events[-1]`` (the latest event overall). No side effects.
        """
        if content_id is not None:
            filtered = [e for e in self.events if e.content_id == content_id]
            if not filtered:
                return None
            return filtered[-1]
        if not self.events:
            return None
        return self.events[-1]

    def get_content_event_count(self, content_id: str) -> int:
        """Return the number of stored events for a specific content item.

        No guard path: always computes (returns 0 when no event matches).

        Returns ``len(self.get_events_for_content(content_id))``. No side
        effects.
        """
        return len(self.get_events_for_content(content_id))


    def get_events_for_day(self, d: date) -> list[TimelineEvent]:
        """Return the stored events that fall on the given calendar day.

        No guard path: always computes (returns an empty list when no event
        falls on the day).

        The window is INCLUSIVE on both ends: ``start`` =
        ``datetime(d.year, d.month, d.day, tzinfo=timezone.utc)`` (00:00:00
        UTC) and ``end`` = ``datetime(d.year, d.month, d.day, 23, 59, 59,
        999999, tzinfo=timezone.utc)`` (23:59:59.999999 UTC). An event is
        returned iff ``start <= e.timestamp <= end``. The result preserves
        ``self.events`` order (ascending by timestamp). No side effects.
        """
        start = datetime(d.year, d.month, d.day, tzinfo=timezone.utc)
        end = datetime(d.year, d.month, d.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_for_week(self, d: date) -> list[TimelineEvent]:
        """Get events for the week containing the given date.

        The week is MONDAY-based: ``monday = d - timedelta(days=d.weekday())``
        and ``sunday = monday + timedelta(days=6)``. The window is INCLUSIVE
        on both ends:

          * ``start`` = ``datetime(monday.year, monday.month, monday.day,
            tzinfo=timezone.utc)``  -- Monday 00:00:00.000000 UTC
          * ``end``   = ``datetime(sunday.year, sunday.month, sunday.day,
            23, 59, 59, 999999, tzinfo=timezone.utc)``  -- Sunday 23:59:59.999999 UTC

        An event is returned iff ``start <= e.timestamp <= end``. The result
        preserves ``self.events`` order (ascending by timestamp).
        """
        # Monday of the week
        monday = d - timedelta(days=d.weekday())
        start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
        # Sunday end of week
        sunday = monday + timedelta(days=6)
        end = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_events_for_month(self, year: int, month: int) -> list[TimelineEvent]:
        """Return the stored events that fall in the given month.

        No guard path: always computes (returns an empty list when no event
        falls in the month).

        The window is INCLUSIVE on both ends: ``start`` =
        ``datetime(year, month, 1, tzinfo=timezone.utc)`` (1st 00:00:00 UTC)
        and ``end`` = ``datetime(year, month, last_day, 23, 59, 59, 999999,
        tzinfo=timezone.utc)`` (last day 23:59:59.999999 UTC), where
        ``last_day = calendar.monthrange(year, month)[1]``. An event is
        returned iff ``start <= e.timestamp <= end``. The result preserves
        ``self.events`` order (ascending by timestamp). No side effects.
        """
        last_day = calendar.monthrange(year, month)[1]
        start = datetime(year, month, 1, tzinfo=timezone.utc)
        end = datetime(year, month, last_day, 23, 59, 59, 999999, tzinfo=timezone.utc)
        return [e for e in self.events if start <= e.timestamp <= end]

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the timeline.

        Returns a dict with exactly the keys:
          * ``total_events``  -> ``len(self.events)``
          * ``total_entries`` -> ``len(self.entries)``
          * ``content_ids``   -> ``list(self.content_ids)`` (the unique
            content IDs referenced by the stored events, in set order).
        """
        return {
            "total_events": len(self.events),
            "total_entries": len(self.entries),
            "content_ids": list(self.content_ids),
        }

    def to_dict(self) -> dict[str, Any]:
        """Serialize the timeline to a dict.

        No guard path: always computes.

        Returns a dict with exactly the keys:
          * ``events``      -> ``[e.to_dict() for e in self.events]``
          * ``entries``     -> ``[e.to_dict() for e in self.entries]``
          * ``event_count`` -> ``self.get_event_count()`` (i.e.
            ``len(self.events)``).
        No side effects.
        """
        return {
            "events": [e.to_dict() for e in self.events],
            "entries": [e.to_dict() for e in self.entries],
            "event_count": self.get_event_count(),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Timeline:
        """Deserialize a timeline from a dict.

        No guard path: always constructs (missing ``events`` / ``entries``
        keys are treated as empty lists).

        Returns a new ``Timeline`` whose ``events`` are
        ``[TimelineEvent.from_dict(d) for d in data.get("events", [])]``
        re-sorted ascending by timestamp, and whose ``entries`` are
        ``[TimelineEntry.from_dict(d) for d in data.get("entries", [])]``
        re-sorted descending (newest-first) by timestamp. No side effects
        beyond constructing the returned object.
        """
        timeline = cls()
        for event_data in data.get("events", []):
            event = TimelineEvent.from_dict(event_data)
            timeline.events.append(event)
        timeline.events.sort(key=lambda e: e.timestamp)
        for entry_data in data.get("entries", []):
            entry = TimelineEntry.from_dict(entry_data)
            timeline.entries.append(entry)
        timeline.entries.sort(key=lambda e: e.timestamp, reverse=True)
        return timeline
