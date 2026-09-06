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
    ViewResult,
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

    def test_timeline_entry_from_dict_bad_timestamp_degrades_to_datetime(self) -> None:
        entry = TimelineEntry.from_dict(
            {"item_id": "i1", "timestamp": "not-a-date"}
        )
        assert isinstance(entry.timestamp, datetime)
        assert entry.item_id == "i1"

    def test_timeline_entry_from_dict_non_string_timestamp_passthrough(self) -> None:
        ts = _ts(3, 6)
        entry = TimelineEntry.from_dict({"item_id": "i1", "timestamp": ts})
        assert entry.timestamp == ts

    def test_timeline_entry_from_dict_valid_timestamp_round_trips(self) -> None:
        entry = TimelineEntry.from_dict(
            {"item_id": "i1", "timestamp": _ts(4, 9).isoformat()}
        )
        assert entry.timestamp == _ts(4, 9)
        assert entry.item_id == "i1"

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


class TestGetSummaryPinning:
    """Pins the corrected Timeline.get_summary claim (TICKET-475)."""

    def test_get_summary_exact_keys_and_values(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        tl.add_event(_event("e2", "c2", _ts(2)))
        tl.add_event(_event("e3", "c1", _ts(3)))
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        tl.add_entry("i2", "T2", timestamp=_ts(2))
        summary = tl.get_summary()
        assert set(summary.keys()) == {"total_events", "total_entries", "content_ids"}
        assert summary["total_events"] == len(tl.events) == 3
        assert summary["total_entries"] == len(tl.entries) == 2
        assert summary["content_ids"] == list(tl.content_ids)
        assert set(summary["content_ids"]) == {"c1", "c2"}

    def test_get_summary_empty(self) -> None:
        tl = Timeline()
        summary = tl.get_summary()
        assert summary == {"total_events": 0, "total_entries": 0, "content_ids": []}


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


class TestTimelineViewElseBranchPinning:
    """Pins TICKET-477: TimelineView.render else branch uses timeline.events."""

    def test_render_else_branch_uses_events_not_entries(self) -> None:
        from personal_index.content_timeline.timeline_view import TimelineView
        from personal_index.content_timeline.timeline import Timeline
        from personal_index.content_timeline.timeline_event import TimelineEvent, TimelineEventType
        from datetime import datetime, timezone
        
        tl = Timeline()
        # Add an event
        event = TimelineEvent(
            event_id="e1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc),
            content_id="c1",
            item_id="item1",
            title="Event Title",
            url="http://event.com",
            description="Event Desc"
        )
        tl.add_event(event)
        
        # Add an entry with same item_id but different title
        from personal_index.content_timeline.timeline_entry import TimelineEntry, TimelineEventType as EntryEventType
        entry = TimelineEntry(
            item_id="item1",
            timestamp=datetime(2024, 1, 8, 12, 0, tzinfo=timezone.utc),
            title="Entry Title",
            event_type=EntryEventType.SAVED,
            url="http://entry.com",
            description="Entry Desc"
        )
        tl.entries.append(entry)
        
        view = TimelineView()
        # Use a mock mode object to trigger else branch without AttributeError
        class MockMode:
            value = "invalid"
        view.mode = MockMode()  # type: ignore
        
        result = view.render(tl, datetime(2024, 1, 8).date())
        # Should use events, not entries, so title should be "Event Title" not "Entry Title"
        assert len(result.events) == 1
        assert result.events[0]["title"] == "Event Title"
        assert result.events[0]["url"] == "http://event.com"


class TestAddEntryPinning:
    """Pins the corrected add_entry claim (TICKET-466)."""

    def test_add_entry_returns_created_entry(self) -> None:
        tl = Timeline()
        entry = tl.add_entry("i1", "T1", timestamp=_ts(1))
        assert isinstance(entry, TimelineEntry)
        assert entry.item_id == "i1"
        assert entry.title == "T1"
        assert entry.timestamp == _ts(1)
        assert tl.entries[-1] is entry

    def test_add_entry_defaults_timestamp_to_now_utc(self) -> None:
        tl = Timeline()
        before = datetime.now(timezone.utc)
        entry = tl.add_entry("i1", "T1")
        after = datetime.now(timezone.utc)
        assert entry.timestamp.tzinfo is not None
        assert before <= entry.timestamp <= after

    def test_add_entry_defaults_metadata_to_empty_dict(self) -> None:
        tl = Timeline()
        entry = tl.add_entry("i1", "T1")
        assert entry.metadata == {}

    def test_add_entry_preserves_explicit_metadata(self) -> None:
        tl = Timeline()
        entry = tl.add_entry("i1", "T1", metadata={"k": "v"})
        assert entry.metadata == {"k": "v"}

    def test_add_entry_appends_to_entries(self) -> None:
        tl = Timeline()
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        tl.add_entry("i2", "T2", timestamp=_ts(2))
        assert len(tl.entries) == 2

    def test_add_entry_sorts_reverse_newest_first(self) -> None:
        tl = Timeline()
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        tl.add_entry("i3", "T3", timestamp=_ts(3))
        tl.add_entry("i2", "T2", timestamp=_ts(2))
        assert [e.item_id for e in tl.entries] == ["i3", "i2", "i1"]


class TestTimelineEntriesRoundTripPinning:
    """Pins that to_dict/from_dict preserve entries (TICKET-467)."""

    def test_entries_survive_round_trip(self) -> None:
        tl = Timeline()
        tl.add_entry("i1", "T1", timestamp=_ts(1), url="u1", description="d1")
        tl.add_entry("i2", "T2", timestamp=_ts(2), metadata={"k": "v"})
        data = tl.to_dict()
        assert "entries" in data
        assert len(data["entries"]) == 2
        restored = Timeline.from_dict(data)
        assert len(restored.entries) == 2
        by_id = {e.item_id: e for e in restored.entries}
        assert by_id["i1"].title == "T1"
        assert by_id["i1"].url == "u1"
        assert by_id["i1"].description == "d1"
        assert by_id["i2"].metadata == {"k": "v"}

    def test_entries_resorted_newest_first(self) -> None:
        tl = Timeline()
        tl.add_entry("i1", "T1", timestamp=_ts(1))
        tl.add_entry("i3", "T3", timestamp=_ts(3))
        tl.add_entry("i2", "T2", timestamp=_ts(2))
        restored = Timeline.from_dict(tl.to_dict())
        assert [e.item_id for e in restored.entries] == ["i3", "i2", "i1"]

    def test_empty_entries_round_trip(self) -> None:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(1)))
        restored = Timeline.from_dict(tl.to_dict())
        assert restored.entries == []
        assert [e.event_id for e in restored.events] == ["e1"]


class TestRenderPinning:
    """Pins the corrected TimelineView.render claim (TICKET-474)."""

    def _timeline(self) -> Timeline:
        tl = Timeline()
        tl.add_event(_event("e1", "c1", _ts(8, 9), TimelineEventType.CREATED))
        tl.add_event(_event("e2", "c1", _ts(9, 9), TimelineEventType.TAGGED))
        tl.add_event(_event("e3", "c1", _ts(15, 9), TimelineEventType.CREATED))
        return tl

    def test_render_day_dispatch_and_event_dict_keys(self) -> None:
        view = TimelineView()  # default mode DAY
        result = view.render(self._timeline(), date(2024, 1, 8))
        # DAY dispatch -> only the Jan 8 event.
        assert result.mode == "day"
        assert result.total == 1
        ev = result.events[0]
        # Exactly the documented keys, in the documented shapes.
        assert set(ev.keys()) == {
            "item_id", "title", "event_type", "timestamp", "url", "description",
        }
        assert ev["item_id"] == "e1"
        assert ev["event_type"] == "created"  # .value, not the enum
        assert ev["timestamp"] == _ts(8, 9).isoformat()

    def test_render_event_type_filter(self) -> None:
        view = TimelineView()
        view.set_mode(ViewMode.MONTH)
        result = view.render(
            self._timeline(), date(2024, 1, 10), event_type=TimelineEventType.TAGGED
        )
        assert result.total == 1
        assert result.events[0]["item_id"] == "e2"
        assert result.events[0]["event_type"] == "tagged"

    def test_render_summary_passthrough(self) -> None:
        view = TimelineView()
        tl = self._timeline()
        result = view.render(tl, date(2024, 1, 8))
        # summary is timeline.get_summary() (whole-timeline, not filtered).
        assert result.summary == tl.get_summary()
        assert result.summary["total_events"] == 3
        assert result.date == date(2024, 1, 8).isoformat()


class TestViewResultDictAccessPinning:
    """Pins the scoped ViewResult dict-style access contract (TICKET-476).

    __getitem__/__contains__ must expose exactly the five serialized fields
    (the same key set as to_dict()), not the whole object attribute
    namespace (no dunders).
    """

    def _result(self) -> ViewResult:
        return ViewResult(
            events=[{"item_id": "e1"}],
            date="2024-01-08",
            mode="day",
            total=1,
            summary={"total_events": 1},
        )

    def test_contains_only_serialized_fields(self) -> None:
        r = self._result()
        for key in ("events", "date", "mode", "total", "summary"):
            assert key in r
        # dunders and arbitrary names are NOT part of the dict contract
        assert "__class__" not in r
        assert "__dict__" not in r
        assert "missing" not in r

    def test_getitem_serialized_fields(self) -> None:
        r = self._result()
        assert r["total"] == 1
        assert r["mode"] == "day"
        assert r["date"] == "2024-01-08"
        assert r["events"] == [{"item_id": "e1"}]
        assert r["summary"] == {"total_events": 1}

    def test_getitem_out_of_set_raises_keyerror(self) -> None:
        r = self._result()
        for bad in ("__class__", "__dict__", "missing"):
            try:
                r[bad]
            except KeyError:
                pass
            else:
                raise AssertionError(f"{bad!r} should raise KeyError")

    def test_access_contract_matches_to_dict_keys(self) -> None:
        r = self._result()
        assert set(r.to_dict().keys()) == set(r._FIELDS)
        for key in r._FIELDS:
            assert key in r


class TestGetEventsForWeekDocstring539:
    """Pin the Timeline.get_events_for_week exact week-window contract (TICKET-539)."""

    def test_docstring_states_exact_contract(self) -> None:
        doc = Timeline.get_events_for_week.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "MONDAY-based" in doc
        assert "INCLUSIVE" in doc
        assert "00:00:00" in doc
        assert "23:59:59" in doc
        assert "weekday" in doc
        assert "ascending" in doc

    def test_includes_event_at_exact_monday_start(self) -> None:
        # Lower bound: Monday 00:00:00.000000 UTC is included.
        tl = Timeline()
        tl.add_event(_event("mon_start", "c1",
                            datetime(2024, 1, 8, 0, 0, 0, 0, tzinfo=timezone.utc)))
        res = tl.get_events_for_week(date(2024, 1, 10))
        assert [e.event_id for e in res] == ["mon_start"]

    def test_includes_event_at_exact_sunday_end(self) -> None:
        # Upper bound: Sunday 23:59:59.999999 UTC is included.
        tl = Timeline()
        tl.add_event(_event("sun_end", "c1",
                            datetime(2024, 1, 14, 23, 59, 59, 999999, tzinfo=timezone.utc)))
        res = tl.get_events_for_week(date(2024, 1, 10))
        assert [e.event_id for e in res] == ["sun_end"]

    def test_excludes_previous_sunday_and_next_monday(self) -> None:
        # Just outside the window on both sides.
        tl = Timeline()
        tl.add_event(_event("prev_sun", "c1",
                            datetime(2024, 1, 7, 23, 59, 59, 999999, tzinfo=timezone.utc)))
        tl.add_event(_event("next_mon", "c1",
                            datetime(2024, 1, 15, 0, 0, 0, 0, tzinfo=timezone.utc)))
        res = tl.get_events_for_week(date(2024, 1, 10))
        assert res == []

    def test_week_is_monday_based_for_any_weekday(self) -> None:
        # A Monday input maps to itself; a Sunday input maps back to its Monday.
        tl = Timeline()
        tl.add_event(_event("m", "c1",
                            datetime(2024, 1, 8, 12, 0, 0, 0, tzinfo=timezone.utc)))
        assert [e.event_id for e in tl.get_events_for_week(date(2024, 1, 8))] == ["m"]
        assert [e.event_id for e in tl.get_events_for_week(date(2024, 1, 14))] == ["m"]

    def test_result_preserves_ascending_order(self) -> None:
        tl = Timeline()
        tl.add_event(_event("a", "c1", _ts(8, 9)))
        tl.add_event(_event("b", "c1", _ts(10, 12)))
        tl.add_event(_event("c", "c1", _ts(14, 18)))
        res = tl.get_events_for_week(date(2024, 1, 10))
        assert [e.event_id for e in res] == ["a", "b", "c"]
