"""Tests for content timeline module."""

from __future__ import annotations

import pytest

from personal_index.content_timeline import (
    ContentTimeline,
    TimelineEntry,
    TimelineGroup,
)


def make_entry(
    url: str = "https://example.com",
    title: str = "Test",
    timestamp: str = "2024-01-15T10:00:00",
    event_type: str = "indexed",
    tags: list[str] | None = None,
    score: float = 0.0,
) -> TimelineEntry:
    return TimelineEntry(
        url=url,
        title=title,
        timestamp=timestamp,
        tags=tags or [],
        score=score,
        event_type=event_type,
    )


class TestTimelineEntry:
    def test_datetime_parse(self):
        entry = make_entry(timestamp="2024-01-15T10:00:00")
        dt = entry.datetime
        assert dt.year == 2024
        assert dt.month == 1
        assert dt.day == 15

    def test_to_dict(self):
        entry = make_entry()
        d = entry.to_dict()
        assert d["url"] == "https://example.com"
        assert d["title"] == "Test"
        assert d["event_type"] == "indexed"


class TestTimelineGroup:
    def test_count(self):
        group = TimelineGroup(period="2024-01", entries=[make_entry(), make_entry()])
        assert group.count == 2


class TestContentTimeline:
    def setup_method(self):
        self.timeline = ContentTimeline()
        self.timeline.add_entries([
            make_entry(url="https://a.com", title="A", timestamp="2024-01-15T10:00:00"),
            make_entry(url="https://b.com", title="B", timestamp="2024-01-16T12:00:00"),
            make_entry(url="https://c.com", title="C", timestamp="2024-02-01T08:00:00"),
            make_entry(url="https://d.com", title="D", timestamp="2024-02-01T09:00:00", event_type="updated"),
        ])

    def test_add_entry(self):
        self.timeline.add_entry(make_entry(url="https://new.com", title="New"))
        assert self.timeline.count == 5

    def test_get_entries_all(self):
        entries = self.timeline.get_entries()
        assert len(entries) == 4
        # Should be sorted newest first
        assert entries[0].timestamp >= entries[1].timestamp

    def test_get_entries_time_range(self):
        entries = self.timeline.get_entries(
            start="2024-01-16T00:00:00",
            end="2024-01-16T23:59:59",
        )
        assert len(entries) == 1
        assert entries[0].url == "https://b.com"

    def test_get_entries_event_type(self):
        entries = self.timeline.get_entries(event_type="updated")
        assert len(entries) == 1
        assert entries[0].url == "https://d.com"

    def test_group_by_day(self):
        groups = self.timeline.group_by_day()
        assert len(groups) == 3  # Jan 15, Jan 16, Feb 1
        assert groups[0].period == "2024-02-01"
        assert groups[0].count == 2

    def test_group_by_week(self):
        groups = self.timeline.group_by_week()
        assert len(groups) >= 1
        # All entries should be in groups
        total = sum(g.count for g in groups)
        assert total == 4

    def test_group_by_month(self):
        groups = self.timeline.group_by_month()
        assert len(groups) == 2  # Jan and Feb
        assert groups[0].period == "2024-02"
        assert groups[1].period == "2024-01"

    def test_get_recent(self):
        recent = self.timeline.get_recent(count=2)
        assert len(recent) == 2
        assert recent[0].timestamp >= recent[1].timestamp

    def test_get_stats(self):
        stats = self.timeline.get_stats()
        assert stats["total_entries"] == 4
        assert stats["event_types"]["indexed"] == 3
        assert stats["event_types"]["updated"] == 1

    def test_get_stats_empty(self):
        empty = ContentTimeline()
        stats = empty.get_stats()
        assert stats["total_entries"] == 0
        assert stats["earliest"] is None

    def test_clear(self):
        self.timeline.clear()
        assert self.timeline.count == 0

    def test_count(self):
        assert self.timeline.count == 4
