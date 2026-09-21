"""Adversarial deep tests for the content_timeline module (cycle 340).

Never-probed module lane. Covers Timeline window functions (day/week/month),
the TimelineView renderer, TimelineEvent/TimelineEntry round-trips, equality
semantics, idempotence, edge-case inputs (None/empty/unicode/out-of-range),
and one end-to-end CLI run.

QA-68 (xfail-strict pins): TimelineEvent.from_dict / TimelineEntry.from_dict
docstrings claim a NON-STRING timestamp "degrades to datetime.now(timezone.utc)",
but the code only catches ValueError, so a non-string (e.g. int) timestamp is
stored verbatim and later raises AttributeError in to_dict().
"""

from datetime import date, datetime, timezone

import pytest

from personal_index.content_timeline import (
    Timeline,
    TimelineEntry,
    TimelineEvent,
    TimelineEventType,
    EntryEventType,
    TimelineView,
    ViewMode,
    ViewResult,
)


def _ev(eid, ts, cid="c1", et=TimelineEventType.SAVED):
    return TimelineEvent(event_id=eid, event_type=et, timestamp=ts, content_id=cid)


# --- QA-68: non-string timestamp must degrade to now-utc per docstring ---

def test_event_from_dict_nonstring_timestamp_degrades():
    e = TimelineEvent.from_dict({"event_id": "e1", "timestamp": 12345})
    # per docstring: ts should be a tz-aware datetime (now-utc), not the int
    assert isinstance(e.timestamp, datetime)
    assert e.to_dict()["timestamp"]  # must not raise


def test_entry_from_dict_nonstring_timestamp_degrades():
    e = TimelineEntry.from_dict({"item_id": "i1", "timestamp": 12345})
    assert isinstance(e.timestamp, datetime)
    assert e.to_dict()["timestamp"]


def test_event_from_dict_none_timestamp_degrades():
    e = TimelineEvent.from_dict({"event_id": "e1", "timestamp": None})
    assert isinstance(e.timestamp, datetime)


# --- armor: ValueError path DOES degrade (the only guard the code has) ---

def test_event_from_dict_invalid_string_degrades():
    e = TimelineEvent.from_dict({"event_id": "e1", "timestamp": "not-a-date"})
    assert isinstance(e.timestamp, datetime)
    assert e.timestamp.tzinfo is not None


def test_entry_from_dict_invalid_string_degrades():
    e = TimelineEntry.from_dict({"item_id": "i1", "timestamp": "garbage"})
    assert isinstance(e.timestamp, datetime)


# --- round-trips ---

def test_event_round_trip_preserves_fields():
    ts = datetime(2024, 5, 1, 12, 0, 0, tzinfo=timezone.utc)
    e = TimelineEvent(event_id="e1", event_type=TimelineEventType.TAGGED,
                      timestamp=ts, content_id="c1", metadata={"k": "v"},
                      source="cli", item_id="i1", title="T", url="u", description="d")
    d = e.to_dict()
    e2 = TimelineEvent.from_dict(d)
    assert e2.event_id == "e1"
    assert e2.event_type is TimelineEventType.TAGGED
    assert e2.timestamp == ts
    assert e2.metadata == {"k": "v"}
    assert e2.source == "cli"
    assert e2.title == "T"


def test_entry_round_trip_preserves_fields():
    ts = datetime(2024, 5, 1, tzinfo=timezone.utc)
    e = TimelineEntry(item_id="i1", timestamp=ts, title="T",
                      event_type=EntryEventType.ARCHIVED, url="u",
                      description="d", metadata={"a": 1})
    d = e.to_dict()
    e2 = TimelineEntry.from_dict(d)
    assert e2.item_id == "i1"
    assert e2.timestamp == ts
    assert e2.event_type is EntryEventType.ARCHIVED
    assert e2.metadata == {"a": 1}


def test_timeline_round_trip_idempotent():
    tl = Timeline()
    tl.add_event(_ev("e1", datetime(2024, 1, 1, tzinfo=timezone.utc)))
    tl.add_event(_ev("e2", datetime(2024, 1, 2, tzinfo=timezone.utc)))
    d = tl.to_dict()
    tl2 = Timeline.from_dict(d)
    assert tl2.to_dict() == d  # idempotent round-trip


# --- window functions: day / week / month ---

def test_events_for_day_inclusive_bounds():
    tl = Timeline()
    tl.add_event(_ev("a", datetime(2024, 3, 10, 0, 0, 0, tzinfo=timezone.utc)))
    tl.add_event(_ev("b", datetime(2024, 3, 10, 23, 59, 59, 999999, tzinfo=timezone.utc)))
    tl.add_event(_ev("c", datetime(2024, 3, 11, 0, 0, 0, tzinfo=timezone.utc)))
    got = {e.event_id for e in tl.get_events_for_day(date(2024, 3, 10))}
    assert got == {"a", "b"}  # inclusive both ends, c excluded


def test_events_for_week_monday_based():
    tl = Timeline()
    # 2024-03-11 is a Monday; 2024-03-10 is Sunday (prior week)
    tl.add_event(_ev("sun", datetime(2024, 3, 10, 12, tzinfo=timezone.utc)))
    tl.add_event(_ev("mon", datetime(2024, 3, 11, 0, 0, 0, tzinfo=timezone.utc)))
    tl.add_event(_ev("sun2", datetime(2024, 3, 17, 23, 59, 59, 999999, tzinfo=timezone.utc)))
    tl.add_event(_ev("next", datetime(2024, 3, 18, 0, 0, 0, tzinfo=timezone.utc)))
    got = {e.event_id for e in tl.get_events_for_week(date(2024, 3, 13))}
    assert got == {"mon", "sun2"}


def test_events_for_month_leap_february():
    tl = Timeline()
    tl.add_event(_ev("feb28", datetime(2024, 2, 28, 12, tzinfo=timezone.utc)))
    tl.add_event(_ev("feb29", datetime(2024, 2, 29, 23, 59, 59, 999999, tzinfo=timezone.utc)))
    tl.add_event(_ev("mar1", datetime(2024, 3, 1, 0, 0, 0, tzinfo=timezone.utc)))
    got = {e.event_id for e in tl.get_events_for_month(2024, 2)}
    assert got == {"feb28", "feb29"}  # leap day included


def test_events_for_month_out_of_range_month():
    tl = Timeline()
    tl.add_event(_ev("x", datetime(2024, 5, 1, tzinfo=timezone.utc)))
    with pytest.raises((ValueError, Exception)):
        tl.get_events_for_month(2024, 13)  # monthrange raises for invalid month


# --- view renderer ---

def test_view_render_day_mode():
    tl = Timeline()
    tl.add_event(_ev("a", datetime(2024, 3, 10, 12, tzinfo=timezone.utc), cid="c1"))
    v = TimelineView()
    v.set_mode(ViewMode.DAY)
    res = v.render(tl, date(2024, 3, 10))
    assert isinstance(res, ViewResult)
    assert res.total == 1
    assert res.mode == "day"
    assert res.date == "2024-03-10"
    # renderer maps e.item_id (default ""), NOT content_id, per its contract
    assert res.events[0]["item_id"] == ""
    assert res.events[0]["timestamp"].startswith("2024-03-10")


def test_view_render_event_type_filter():
    tl = Timeline()
    tl.add_event(_ev("a", datetime(2024, 3, 10, 12, tzinfo=timezone.utc), et=TimelineEventType.SAVED))
    tl.add_event(_ev("b", datetime(2024, 3, 10, 13, tzinfo=timezone.utc), et=TimelineEventType.TAGGED))
    v = TimelineView()
    v.set_mode(ViewMode.DAY)
    res = v.render(tl, date(2024, 3, 10), event_type=TimelineEventType.TAGGED)
    assert res.total == 1
    assert res.events[0]["event_type"] == "tagged"


def test_view_result_dict_access_contract():
    res = ViewResult(events=[], date="d", mode="day", total=0, summary={})
    assert res["total"] == 0
    assert "events" in res
    assert "nope" not in res
    assert 123 not in res  # non-str key -> False
    with pytest.raises(KeyError):
        res["__dunder__"]


# --- equality semantics ---

def test_event_equality_by_id_only():
    a = _ev("same", datetime(2024, 1, 1, tzinfo=timezone.utc), cid="x")
    b = _ev("same", datetime(2024, 9, 9, tzinfo=timezone.utc), cid="y")
    assert a == b  # only event_id matters
    assert (a == "not-an-event") is False  # NotImplemented -> False


def test_entry_equality_by_id_and_ts():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    a = TimelineEntry(item_id="i", timestamp=ts, title="A")
    b = TimelineEntry(item_id="i", timestamp=ts, title="B")
    assert a == b
    c = TimelineEntry(item_id="i", timestamp=datetime(2024, 2, 2, tzinfo=timezone.utc))
    assert a != c


# --- edge inputs ---

def test_empty_timeline_summary():
    tl = Timeline()
    s = tl.get_summary()
    assert s["total_events"] == 0
    assert s["content_ids"] == []
    assert tl.get_latest_event() is None


def test_unicode_content_id_and_metadata():
    ts = datetime(2024, 1, 1, tzinfo=timezone.utc)
    tl = Timeline()
    tl.add_event(_ev("e1", ts, cid="café-日本"))
    assert "café-日本" in tl.content_ids
    e = TimelineEvent(event_id="e1", event_type=TimelineEventType.SAVED,
                      timestamp=ts, content_id="x", metadata={"ключ": "значение"})
    assert TimelineEvent.from_dict(e.to_dict()).metadata["ключ"] == "значение"


def test_get_events_for_content_empty():
    tl = Timeline()
    assert tl.get_events_for_content("missing") == []
    assert tl.get_content_event_count("missing") == 0


def test_add_entry_newest_first_order():
    tl = Timeline()
    tl.add_entry("i1", "old", timestamp=datetime(2024, 1, 1, tzinfo=timezone.utc))
    tl.add_entry("i2", "new", timestamp=datetime(2024, 6, 1, tzinfo=timezone.utc))
    assert tl.entries[0].item_id == "i2"  # reverse (newest-first)


# --- end-to-end CLI run (installed module) ---

def test_cli_init_runs_green(tmp_path):
    import subprocess
    import sys
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    config = data_dir / "config.yaml"
    base = [sys.executable, "-m", "personal_index.cli", "--data-dir", str(data_dir)]
    init = subprocess.run(base + ["init", "--config", str(config)],
                          capture_output=True, text=True, timeout=120)
    assert init.returncode == 0, init.stderr
