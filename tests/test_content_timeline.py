"""Tests for content_timeline module - chronological view of saved items."""

import pytest
from datetime import datetime, timezone, timedelta

from personal_index.content_timeline.timeline_entry import TimelineEntry, TimelineEventType
from personal_index.content_timeline.timeline import Timeline
from personal_index.content_timeline.timeline_view import TimelineView, ViewMode


# ── TimelineEntry tests ────────────────────────────────────

class TestTimelineEntry:
    def test_create_entry(self):
        entry = TimelineEntry(
            item_id="id1",
            title="Test Article",
            event_type=TimelineEventType.SAVED,
            timestamp=datetime.now(timezone.utc),
        )
        assert entry.item_id == "id1"
        assert entry.title == "Test Article"
        assert entry.event_type == TimelineEventType.SAVED

    def test_entry_default_event_type(self):
        entry = TimelineEntry(
            item_id="id1",
            timestamp=datetime.now(timezone.utc),
        )
        assert entry.event_type == TimelineEventType.SAVED

    def test_entry_to_dict(self):
        ts = datetime.now(timezone.utc)
        entry = TimelineEntry(item_id="id1", title="Test", timestamp=ts)
        d = entry.to_dict()
        assert d["item_id"] == "id1"
        assert d["title"] == "Test"
        assert "timestamp" in d

    def test_entry_from_dict(self):
        ts = datetime.now(timezone.utc)
        d = {
            "item_id": "id2",
            "title": "From Dict",
            "event_type": "saved",
            "timestamp": ts.isoformat(),
        }
        entry = TimelineEntry.from_dict(d)
        assert entry.item_id == "id2"
        assert entry.title == "From Dict"

    def test_entry_equality(self):
        ts = datetime.now(timezone.utc)
        e1 = TimelineEntry(item_id="a", timestamp=ts)
        e2 = TimelineEntry(item_id="a", timestamp=ts)
        assert e1 == e2

    def test_entry_inequality(self):
        ts = datetime.now(timezone.utc)
        e1 = TimelineEntry(item_id="a", timestamp=ts)
        e2 = TimelineEntry(item_id="b", timestamp=ts)
        assert e1 != e2

    def test_entry_with_url(self):
        ts = datetime.now(timezone.utc)
        entry = TimelineEntry(
            item_id="id1",
            title="Link",
            url="https://example.com",
            timestamp=ts,
        )
        assert entry.url == "https://example.com"

    def test_entry_with_metadata(self):
        ts = datetime.now(timezone.utc)
        entry = TimelineEntry(
            item_id="id1",
            title="Post",
            metadata={"author": "alice"},
            timestamp=ts,
        )
        assert entry.metadata == {"author": "alice"}


class TestTimelineEventType:
    def test_event_type_values(self):
        assert TimelineEventType.SAVED.value == "saved"
        assert TimelineEventType.TAGGED.value == "tagged"
        assert TimelineEventType.ARCHIVED.value == "archived"
        assert TimelineEventType.LINKED.value == "linked"
        assert TimelineEventType.SEARCHED.value == "searched"

    def test_event_type_count(self):
        assert len(TimelineEventType) == 5


# ── Timeline tests ─────────────────────────────────────────

class TestTimeline:
    def test_add_event(self):
        timeline = Timeline()
        timeline.add_event("id1", "Title", TimelineEventType.SAVED)
        assert len(timeline.entries) == 1

    def test_add_multiple_events(self):
        timeline = Timeline()
        timeline.add_event("id1", "First", TimelineEventType.SAVED)
        timeline.add_event("id2", "Second", TimelineEventType.SAVED)
        assert len(timeline.entries) == 2

    def test_entries_sorted_by_time(self):
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        earlier = now - timedelta(hours=1)
        timeline._add_entry(TimelineEntry(
            item_id="id2", timestamp=now, title="Later"
        ))
        timeline._add_entry(TimelineEntry(
            item_id="id1", timestamp=earlier, title="Earlier"
        ))
        assert timeline.entries[0].title == "Later"

    def test_filter_by_event_type(self):
        timeline = Timeline()
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        timeline.add_event("id2", "B", TimelineEventType.TAGGED)
        filtered = timeline.filter_by_type(TimelineEventType.SAVED)
        assert len(filtered) == 1
        assert filtered[0].item_id == "id1"

    def test_filter_by_date_range(self):
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "Recent", TimelineEventType.SAVED)
        old = now - timedelta(days=100)
        timeline._add_entry(TimelineEntry(
            item_id="id2", timestamp=old, title="Old",
            event_type=TimelineEventType.SAVED,
        ))
        recent = timeline.filter_by_date_range(
            start=now - timedelta(days=30),
            end=now + timedelta(days=1),
        )
        assert len(recent) == 1
        assert recent[0].item_id == "id1"

    def test_filter_by_item_id(self):
        timeline = Timeline()
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        timeline.add_event("id1", "A tagged", TimelineEventType.TAGGED)
        timeline.add_event("id2", "B", TimelineEventType.SAVED)
        filtered = timeline.filter_by_item_id("id1")
        assert len(filtered) == 2

    def test_get_events_for_day(self):
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "Today", TimelineEventType.SAVED)
        yesterday = now - timedelta(days=1)
        timeline._add_entry(TimelineEntry(
            item_id="id2", timestamp=yesterday, title="Yesterday",
            event_type=TimelineEventType.SAVED,
        ))
        today_events = timeline.get_events_for_day(now.date())
        assert len(today_events) == 1
        assert today_events[0].item_id == "id1"

    def test_get_events_for_week(self):
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        for i in range(5):
            timeline.add_event(f"id{i}", f"Event {i}", TimelineEventType.SAVED)
        week_events = timeline.get_events_for_week(now.date())
        assert len(week_events) == 5

    def test_get_events_for_month(self):
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        for i in range(10):
            timeline.add_event(f"id{i}", f"Event {i}", TimelineEventType.SAVED)
        month_events = timeline.get_events_for_month(now.year, now.month)
        assert len(month_events) == 10

    def test_clear(self):
        timeline = Timeline()
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        timeline.clear()
        assert len(timeline.entries) == 0

    def test_get_summary(self):
        timeline = Timeline()
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        timeline.add_event("id2", "B", TimelineEventType.TAGGED)
        summary = timeline.get_summary()
        assert "total_events" in summary
        assert summary["total_events"] == 2

    def test_to_dict(self):
        timeline = Timeline()
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        d = timeline.to_dict()
        assert "entries" in d
        assert len(d["entries"]) == 1


# ── TimelineView tests ─────────────────────────────────────

class TestTimelineView:
    def test_create_view(self):
        view = TimelineView()
        assert view.mode == ViewMode.DAY

    def test_set_mode(self):
        view = TimelineView()
        view.set_mode(ViewMode.WEEK)
        assert view.mode == ViewMode.WEEK

    def test_render_day_view(self):
        view = TimelineView()
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "Event 1", TimelineEventType.SAVED)
        result = view.render(timeline, now.date())
        assert "events" in result
        assert "date" in result

    def test_render_week_view(self):
        view = TimelineView()
        view.set_mode(ViewMode.WEEK)
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "Event 1", TimelineEventType.SAVED)
        result = view.render(timeline, now.date())
        assert "events" in result
        assert "mode" in result

    def test_render_month_view(self):
        view = TimelineView()
        view.set_mode(ViewMode.MONTH)
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "Event 1", TimelineEventType.SAVED)
        result = view.render(timeline, now.date())
        assert "events" in result

    def test_render_empty(self):
        view = TimelineView()
        timeline = Timeline()
        result = view.render(timeline, datetime.now(timezone.utc).date())
        assert len(result["events"]) == 0

    def test_render_with_filter(self):
        view = TimelineView()
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        timeline.add_event("id2", "B", TimelineEventType.TAGGED)
        result = view.render(timeline, now.date(), event_type=TimelineEventType.SAVED)
        assert len(result["events"]) == 1

    def test_render_to_dict(self):
        view = TimelineView()
        timeline = Timeline()
        now = datetime.now(timezone.utc)
        timeline.add_event("id1", "A", TimelineEventType.SAVED)
        result = view.render(timeline, now.date())
        d = result.to_dict()
        assert "events" in d

    def test_view_mode_values(self):
        assert ViewMode.DAY.value == "day"
        assert ViewMode.WEEK.value == "week"
        assert ViewMode.MONTH.value == "month"

    def test_view_mode_count(self):
        assert len(ViewMode) == 3
