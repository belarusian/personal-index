"""Content timeline module for personal-index.

Provides chronological organization and browsing of indexed content
with support for time-based filtering and grouping.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class TimelineEntry:
    """A single entry in the content timeline."""
    url: str
    title: str
    timestamp: str
    content_preview: str = ""
    tags: list[str] = field(default_factory=list)
    score: float = 0.0
    event_type: str = "indexed"  # indexed, updated, removed

    @property
    def datetime(self) -> datetime:
        """Parse timestamp to datetime."""
        try:
            return datetime.fromisoformat(self.timestamp)
        except (ValueError, TypeError):
            return datetime.now(timezone.utc)

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "timestamp": self.timestamp,
            "content_preview": self.content_preview,
            "tags": self.tags,
            "score": self.score,
            "event_type": self.event_type,
        }


@dataclass
class TimelineGroup:
    """A group of timeline entries for a time period."""
    period: str  # e.g., "2024-01-15", "2024-W03", "2024-Q1"
    entries: list[TimelineEntry] = field(default_factory=list)
    period_start: str = ""
    period_end: str = ""

    @property
    def count(self) -> int:
        return len(self.entries)


class ContentTimeline:
    """Timeline for browsing content chronologically.

    Organizes content entries by time and supports grouping
    by day, week, month, or custom periods.
    """

    def __init__(self):
        self._entries: list[TimelineEntry] = []

    def add_entry(self, entry: TimelineEntry) -> None:
        """Add an entry to the timeline."""
        self._entries.append(entry)

    def add_entries(self, entries: list[TimelineEntry]) -> None:
        """Add multiple entries."""
        self._entries.extend(entries)

    def get_entries(
        self,
        start: str | None = None,
        end: str | None = None,
        event_type: str | None = None,
    ) -> list[TimelineEntry]:
        """Get entries filtered by time range and event type.

        Args:
            start: Start timestamp (inclusive, ISO format).
            end: End timestamp (inclusive, ISO format).
            event_type: Filter by event type.

        Returns:
            Filtered list of TimelineEntry objects.
        """
        results = list(self._entries)

        if start:
            results = [e for e in results if e.timestamp >= start]
        if end:
            results = [e for e in results if e.timestamp <= end]
        if event_type:
            results = [e for e in results if e.event_type == event_type]

        # Sort by timestamp descending (newest first)
        results.sort(key=lambda e: e.timestamp, reverse=True)
        return results

    def group_by_day(self) -> list[TimelineGroup]:
        """Group entries by day."""
        groups: dict[str, list[TimelineEntry]] = {}
        for entry in self._entries:
            day = entry.timestamp[:10] if len(entry.timestamp) >= 10 else "unknown"
            groups.setdefault(day, []).append(entry)

        result = []
        for day in sorted(groups.keys(), reverse=True):
            entries = sorted(groups[day], key=lambda e: e.timestamp, reverse=True)
            result.append(TimelineGroup(
                period=day,
                entries=entries,
                period_start=f"{day}T00:00:00",
                period_end=f"{day}T23:59:59",
            ))
        return result

    def group_by_week(self) -> list[TimelineGroup]:
        """Group entries by ISO week."""
        groups: dict[str, list[TimelineEntry]] = {}
        for entry in self._entries:
            try:
                dt = entry.datetime
                iso_cal = dt.isocalendar()
                week_key = f"{iso_cal[0]}-W{iso_cal[1]:02d}"
            except (ValueError, TypeError):
                week_key = "unknown"
            groups.setdefault(week_key, []).append(entry)

        result = []
        for week in sorted(groups.keys(), reverse=True):
            entries = sorted(groups[week], key=lambda e: e.timestamp, reverse=True)
            result.append(TimelineGroup(
                period=week,
                entries=entries,
            ))
        return result

    def group_by_month(self) -> list[TimelineGroup]:
        """Group entries by month."""
        groups: dict[str, list[TimelineEntry]] = {}
        for entry in self._entries:
            month = entry.timestamp[:7] if len(entry.timestamp) >= 7 else "unknown"
            groups.setdefault(month, []).append(entry)

        result = []
        for month in sorted(groups.keys(), reverse=True):
            entries = sorted(groups[month], key=lambda e: e.timestamp, reverse=True)
            result.append(TimelineGroup(
                period=month,
                entries=entries,
            ))
        return result

    def get_recent(self, count: int = 10) -> list[TimelineEntry]:
        """Get the most recent entries.

        Args:
            count: Number of entries to return.

        Returns:
            List of most recent TimelineEntry objects.
        """
        sorted_entries = sorted(self._entries, key=lambda e: e.timestamp, reverse=True)
        return sorted_entries[:count]

    def get_stats(self) -> dict[str, Any]:
        """Get timeline statistics."""
        if not self._entries:
            return {
                "total_entries": 0,
                "event_types": {},
                "earliest": None,
                "latest": None,
            }

        event_counts: dict[str, int] = {}
        for entry in self._entries:
            event_counts[entry.event_type] = event_counts.get(entry.event_type, 0) + 1

        timestamps = [e.timestamp for e in self._entries]
        return {
            "total_entries": len(self._entries),
            "event_types": event_counts,
            "earliest": min(timestamps),
            "latest": max(timestamps),
        }

    def clear(self) -> None:
        """Clear all entries."""
        self._entries.clear()

    @property
    def count(self) -> int:
        """Number of entries in the timeline."""
        return len(self._entries)
