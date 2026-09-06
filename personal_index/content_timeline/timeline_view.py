"""Timeline view renderer for chronological content display."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum
from typing import Any

from personal_index.content_timeline.timeline import Timeline
from personal_index.content_timeline.timeline_event import TimelineEventType


class ViewMode(Enum):
    """View mode for timeline display."""

    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class ViewResult:
    """Result of rendering a timeline view."""

    events: list[dict[str, Any]] = field(default_factory=list)
    date: str = ""
    mode: str = "day"
    total: int = 0
    summary: dict[str, Any] = field(default_factory=dict)

    # The exact key set exposed by the dict-style access contract
    # (__getitem__/__contains__), kept in sync with to_dict().
    _FIELDS: tuple[str, ...] = ("events", "date", "mode", "total", "summary")

    def __getitem__(self, key: str) -> Any:
        """Allow dict-style access to the serialized fields.

        Only the five fields returned by ``to_dict()`` are addressable;
        any other key (including dunders) raises ``KeyError``.
        """
        if key not in self._FIELDS:
            raise KeyError(key)
        return getattr(self, key)

    def __contains__(self, key: object) -> bool:
        """Allow 'in' operator over the serialized fields only."""
        return isinstance(key, str) and key in self._FIELDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "date": self.date,
            "mode": self.mode,
            "total": self.total,
            "summary": self.summary,
        }


class TimelineView:
    """Renders timeline views in different modes."""

    def __init__(self) -> None:
        self.mode: ViewMode = ViewMode.DAY

    def set_mode(self, mode: ViewMode) -> None:
        """Set the view mode."""
        self.mode = mode

    def render(
        self,
        timeline: Timeline,
        reference_date: date,
        event_type: TimelineEventType | None = None,
    ) -> ViewResult:
        """Render the timeline view for the current mode.

        Dispatches on ``self.mode`` to select the candidate events:
          * DAY   -> ``timeline.get_events_for_day(reference_date)``
          * WEEK  -> ``timeline.get_events_for_week(reference_date)``
          * MONTH -> ``timeline.get_events_for_month(reference_date.year,
                     reference_date.month)``

        When ``event_type`` is not None, the selected events are further
        filtered to those whose ``event_type`` equals the given type.

        Each surviving event is rendered as a dict with exactly the keys
        ``item_id``, ``title``, ``event_type`` (its ``.value``),
        ``timestamp`` (``isoformat()``), ``url`` and ``description``.

        Returns a ``ViewResult`` with ``events`` set to that list, ``date``
        to ``reference_date.isoformat()``, ``mode`` to ``self.mode.value``,
        ``total`` to the number of rendered events, and ``summary`` to
        ``timeline.get_summary()``.
        """
        if self.mode == ViewMode.DAY:
            entries = timeline.get_events_for_day(reference_date)
        elif self.mode == ViewMode.WEEK:
            entries = timeline.get_events_for_week(reference_date)
        elif self.mode == ViewMode.MONTH:
            entries = timeline.get_events_for_month(
                reference_date.year, reference_date.month
            )
        else:
            entries = timeline.entries

        # Filter by event type if specified
        if event_type:
            entries = [e for e in entries if e.event_type == event_type]

        events_data = [
            {
                "item_id": e.item_id,
                "title": e.title,
                "event_type": e.event_type.value,
                "timestamp": e.timestamp.isoformat(),
                "url": e.url,
                "description": e.description,
            }
            for e in entries
        ]

        return ViewResult(
            events=events_data,
            date=reference_date.isoformat(),
            mode=self.mode.value,
            total=len(entries),
            summary=timeline.get_summary(),
        )
