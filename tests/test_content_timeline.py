"""Tests for the content timeline module."""

from datetime import datetime, timedelta

import pytest

from personal_index.content_timeline import (
    Timeline,
    TimelineEvent,
    TimelineEventType,
)


class TestTimelineEvent:
    def test_create_event(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        )
        assert event.event_id == "evt-1"
        assert event.event_type == TimelineEventType.CREATED
        assert event.source == "system"

    def test_event_to_dict(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.BOOKMARKED,
            timestamp=datetime(2024, 1, 1, 12, 0),
            content_id="content-1",
            metadata={"user": "alice"},
            source="user",
        )
        d = event.to_dict()
        assert d["event_type"] == "bookmarked"
        assert d["metadata"]["user"] == "alice"
        assert d["source"] == "user"

    def test_event_from_dict(self) -> None:
        data = {
            "event_id": "evt-1",
            "event_type": "created",
            "timestamp": "2024-01-01T00:00:00",
            "content_id": "content-1",
            "metadata": {"key": "value"},
            "source": "crawler",
        }
        event = TimelineEvent.from_dict(data)
        assert event.event_type == TimelineEventType.CREATED
        assert event.source == "crawler"
        assert event.metadata == {"key": "value"}

    def test_event_custom_metadata(self) -> None:
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.TAGGED,
            timestamp=datetime.now(),
            content_id="content-1",
            metadata={"tags": ["python", "web"]},
        )
        assert "tags" in event.metadata


class TestTimeline:
    def test_empty_timeline(self) -> None:
        t = Timeline()
        assert t.get_event_count() == 0
        assert t.content_ids == set()

    def test_add_event(self) -> None:
        t = Timeline()
        event = TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        )
        t.add_event(event)
        assert t.get_event_count() == 1
        assert "content-1" in t.content_ids

    def test_events_sorted_by_time(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        assert t.events[0].event_id == "evt-1"
        assert t.events[1].event_id == "evt-2"

    def test_get_events_for_content(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-2",
        ))
        events = t.get_events_for_content("content-1")
        assert len(events) == 1
        assert events[0].content_id == "content-1"

    def test_get_events_by_type(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.BOOKMARKED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        events = t.get_events_by_type(TimelineEventType.BOOKMARKED)
        assert len(events) == 1
        assert events[0].event_type == TimelineEventType.BOOKMARKED

    def test_get_events_in_range(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 15),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-3",
            event_type=TimelineEventType.DELETED,
            timestamp=datetime(2024, 2, 1),
            content_id="content-1",
        ))
        events = t.get_events_in_range(
            datetime(2024, 1, 10), datetime(2024, 1, 20),
        )
        assert len(events) == 1
        assert events[0].event_id == "evt-2"

    def test_get_latest_event(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.UPDATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-1",
        ))
        latest = t.get_latest_event()
        assert latest is not None
        assert latest.event_id == "evt-2"

    def test_get_latest_event_empty(self) -> None:
        t = Timeline()
        assert t.get_latest_event() is None

    def test_get_latest_event_by_content(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        t.add_event(TimelineEvent(
            event_id="evt-2",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 2),
            content_id="content-2",
        ))
        latest = t.get_latest_event("content-1")
        assert latest is not None
        assert latest.content_id == "content-1"

    def test_get_content_event_count(self) -> None:
        t = Timeline()
        for i in range(5):
            t.add_event(TimelineEvent(
                event_id=f"evt-{i}",
                event_type=TimelineEventType.CREATED,
                timestamp=datetime(2024, 1, i + 1),
                content_id="content-1",
            ))
        assert t.get_content_event_count("content-1") == 5
        assert t.get_content_event_count("content-2") == 0

    def test_to_dict_and_from_dict(self) -> None:
        t = Timeline()
        t.add_event(TimelineEvent(
            event_id="evt-1",
            event_type=TimelineEventType.CREATED,
            timestamp=datetime(2024, 1, 1),
            content_id="content-1",
        ))
        d = t.to_dict()
        t2 = Timeline.from_dict(d)
        assert t2.get_event_count() == 1
        assert t2.events[0].event_id == "evt-1"
