"""Functional tests for the content_timeline package.

Covers Timeline (add/sort/range queries), TimelineEvent and TimelineEntry
serialization round-trips, and TimelineView rendering in all modes.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

from personal_index.content_timeline import (
    EntryEventType,
    Timeline,
    TimelineEntry,
    TimelineEvent,
    TimelineEventType,
    TimelineView,
    ViewMode,
)


def _ts(day: int, hour: int = 12) -> datetime:
    """Build a UTC timestamp on 2024-01-<day> at <hour>:00."""
    return datetime(2024, 1, day, hour, 0, 0, tzinfo=timezone.utc)


def _event(event_id: str, content_id: str, ts: datetime,
           etype: TimelineEventType = TimelineEventType.CREATED) -> TimelineEvent:
    return TimelineEvent(
        event_id=event_id,
        event_type=etype,
        timestamp=ts,
        content_id=content_id,
        item_id=event_id,
    )


class TestTimelineAddAndSort:
    def test_add_event_maintains_ascending_order(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e3", "c1", _ts(3)))
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_event(_event("e2", "c1", _ts(2)))
        assert [e.event_id for e in tl.events] == ["e1", "e2", "e3"]

    def test_add_entry_maintains_descending_order(self) -> None:
        tl = Timeline()
        tl.add_entry("i3", "T3", timestamp=_ts(3))
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        tl.add_entry("i2", "T2", timestamp=_ts(2))
        assert [e.item_id for e in tl.entries] == ["i3", "i2", "i1"]

    def test_add_entry_defaults_timestamp_and_metadata(self) -> None:
        tl = Timeline()
        entry = tl.add_entry("i1", "T1")
        assert entry.metadata == {}
        assert entry.timestamp.tzinfo is not None
        assert entry.event_type is EntryEventType.SAVED

    def test_get_event_count(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_event(_event("e2", "c1", _ts(2)))
        assert tl.get_event_count() == 2

    def test_content_ids_unique(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_event(_event("e2", "c2", _ts(2)))
        tl.add_event(_event("e3", "c1", _ts(3)))
        assert tl.content_ids == {"c1", "c2"}


class TestTimelineQueries:
    def _populated(self) -> Timeline:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_event(_event("e2", "c1", _ts(2)))
        tl.add_event(_event("e3", "c2", _ts(3)))
        tl.add_event(_event("e4", "c2", _ts(4), TimelineEventType.TAGGED))
        return tl

    def test_get_events_for_content(self) -> None:
        tl = self._populated()
        assert [e.event_id for e in tl.get_events_for_content("c1")] == ["e1", "e2"]

    def test_get_events_by_type(self) -> None:
        tl = self._populated()
        assert [e.event_id for e in tl.get_events_by_type(TimelineEventType.TAGGED)] == ["e4"]

    def test_get_events_in_range_inclusive(self) -> None:
        tl = self._populated()
        res = tl.get_events_in_range(_ts(2), _ts(3))
        assert [e.event_id for e in res] == ["e2", "e3"]

    def test_get_events_for_day_boundaries(self) -> None:
        tl = Timeline()
        tl.add_event(_event("mid", "c1", _ts(5, 12)))
        tl.add_event(_event("other", "c1", _ts(6, 12)))
        res = tl.get_events_for_day(date(2024, 1, 5))
        assert [e.event_id for e in res] == ["mid"]

    def test_get_events_for_week_monday_based(self) -> None:
        # 2024-01-08 is a Monday; week spans Jan 8-14.
        tl = Timeline()
        tl.add_event(_event("in_week", "c1", _ts(8, 9)))
        tl.add_event(_event("in_week2", "c1", _ts(14, 23)))
        tl.add_event(_event("prev_week", "c1", _ts(7, 23)))
        res = tl.get_events_for_week(date(2024, 1, 10))
        assert [e.event_id for e in res] == ["in_week", "in_week2"]

    def test_get_events_for_month(self) -> None:
        tl = Timeline()
        tl.add_event(_event("jan", "c1", _ts(31, 23)))
        tl.add_event(_event("feb", "c1", datetime(2024, 2, 1, 0, 0, tzinfo=timezone.utc)))
        res = tl.get_events_for_month(2024, 1)
        assert [e.event_id for e in res] == ["jan"]

    def test_get_events_for_month_february(self) -> None:
        tl = Timeline()
        tl.add_event(_event("feb29", "c1", datetime(2024, 2, 29, 12, tzinfo=timezone.utc)))
        res = tl.get_events_for_month(2024, 2)
        assert [e.event_id for e in res] == ["feb29"]

    def test_get_latest_event_overall(self) -> None:
        tl = self._populated()
        latest = tl.get_latest_event()
        assert latest is not None
        assert latest.event_id == "e4"

    def test_get_latest_event_by_content(self) -> None:
        tl = self._populated()
        latest = tl.get_latest_event("c1")
        assert latest is not None
        assert latest.event_id == "e2"

    def test_get_latest_event_empty(self) -> None:
        assert Timeline().get_latest_event() is None

    def test_get_latest_event_missing_content(self) -> None:
        tl = self._populated()
        assert tl.get_latest_event("nope") is None

    def test_get_content_event_count(self) -> None:
        tl = self._populated()
        assert tl.get_content_event_count("c2") == 2


class TestSerialization:
    def test_timeline_event_round_trip(self) -> None:
        ev = TimelineEvent(
            event_id="e1",
            event_type=TimelineEventType.TAGGED,
            timestamp=_ts(5, 8),
            content_id="c1",
            metadata={"k": "v"},
            source="user",
            item_id="i1",
            title="T",
            url="http://x",
            description="D",
        )
        restored = TimelineEvent.from_dict(ev.to_dict())
        assert restored == ev
        assert restored.event_type is TimelineEventType.TAGGED
        assert restored.metadata == {"k": "v"}
        assert restored.source == "user"

    def test_timeline_event_defaults(self) -> None:
        ev = TimelineEvent.from_dict(
            {"event_id": "e1", "timestamp": _ts(1).isoformat(), "content_id": "c1"}
        )
        assert ev.event_type is TimelineEventType.CREATED
        assert ev.source == "system"

    def test_from_dict_bad_timestamp_degrades_to_datetime(self) -> None:
        ev = TimelineEvent.from_dict(
            {"event_id": "e1", "content_id": "c1", "timestamp": "not-a-date"}
        )
        assert isinstance(ev.timestamp, datetime)
        assert ev.event_id == "e1"
        assert ev.content_id == "c1"

    def test_from_dict_missing_event_id_degrades_to_empty(self) -> None:
        ev = TimelineEvent.from_dict(
            {"content_id": "c1", "timestamp": _ts(1).isoformat()}
        )
        assert ev.event_id == ""
        assert ev.content_id == "c1"

    def test_from_dict_missing_content_id_degrades_to_empty(self) -> None:
        ev = TimelineEvent.from_dict(
            {"event_id": "e1", "timestamp": _ts(1).isoformat()}
        )
        assert ev.content_id == ""
        assert ev.event_id == "e1"

    def test_from_dict_valid_record_still_round_trips(self) -> None:
        ev = TimelineEvent(
            event_id="e1",
            event_type=TimelineEventType.TAGGED,
            timestamp=_ts(5, 8),
            content_id="c1",
            metadata={"k": "v"},
            source="user",
        )
        restored = TimelineEvent.from_dict(ev.to_dict())
        assert restored == ev
        assert restored.event_type is TimelineEventType.TAGGED
        assert restored.metadata == {"k": "v"}

    def test_timeline_entry_round_trip(self) -> None:
        entry = TimelineEntry(
            item_id="i1",
            timestamp=_ts(5, 8),
            title="T",
            event_type=EntryEventType.TAGGED,
            url="http://x",
            description="D",
            metadata={"a": 1},
        )
        restored = TimelineEntry.from_dict(entry.to_dict())
        assert restored == entry
        assert restored.event_type is EntryEventType.TAGGED
        assert restored.metadata == {"a": 1}

    def test_timeline_to_dict_from_dict(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(2)))
        tl.add_event(_event("e2", "c1", _ts(1)))
        data = tl.to_dict()
        assert data["event_count"] == 2
        restored = Timeline.from_dict(data)
        assert [e.event_id for e in restored.events] == ["e2", "e1"]

    def test_get_summary(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        summary = tl.get_summary()
        assert summary["total_events"] == 1
        assert summary["total_entries"] == 1
        assert summary["content_ids"] == ["c1"]


class TestTimelineView:
    def _timeline(self) -> Timeline:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(8, 9), TimelineEventType.CREATED))
        tl.add_event(_event("e2", "c1", _ts(9, 9), TimelineEventType.TAGGED))
        tl.add_event(_event("e3", "c1", _ts(15, 9), TimelineEventType.CREATED))
        return tl

    def test_render_day(self) -> None:
        view = TimelineView()
        result = view.render(self._timeline(), date(2024, 1, 8))
        assert result.mode == "day"
        assert result.total == 1
        assert result.events[0]["item_id"] == "e1"

    def test_render_week(self) -> None:
        view = TimelineView()
        view.set_mode(ViewMode.WEEK)
        result = view.render(self._timeline(), date(2024, 1, 10))
        assert result.mode == "week"
        # Week of Jan 8-14 contains e1 (Jan 8) and e2 (Jan 9), not e3 (Jan 15).
        assert result.total == 2
        assert {e["item_id"] for e in result.events} == {"e1", "e2"}

    def test_render_month(self) -> None:
        view = TimelineView()
        view.set_mode(ViewMode.MONTH)
        result = view.render(self._timeline(), date(2024, 1, 10))
        assert result.mode == "month"
        assert result.total == 3

    def test_render_event_type_filter(self) -> None:
        view = TimelineView()
        view.set_mode(ViewMode.MONTH)
        result = view.render(
            self._timeline(), date(2024, 1, 10), event_type=TimelineEventType.TAGGED
        )
        assert result.total == 1
        assert result.events[0]["event_type"] == "tagged"

    def test_view_result_dict_access(self) -> None:
        view = TimelineView()
        result = view.render(self._timeline(), date(2024, 1, 8))
        assert result["total"] == 1
        assert "mode" in result
        assert "missing" not in result
        d = result.to_dict()
        assert d["mode"] == "day"
        assert d["total"] == 1


class TestEdgeCases:
    def test_event_eq_not_implemented_for_other_type(self) -> None:
        ev = _event("e1", "c1", _ts(1))
        assert ev.__eq__("not-an-event") is NotImplemented

    def test_entry_eq_not_implemented_for_other_type(self) -> None:
        entry = TimelineEntry(item_id="i1", timestamp=_ts(1))
        assert entry.__eq__("not-an-entry") is NotImplemented

    def test_view_result_contains_non_str_key(self) -> None:
        view = TimelineView()
        result = view.render(Timeline(), date(2024, 1, 8))
        assert 123 not in result
