# Timeline (`personal_index.content_timeline`)

Status: **spec** — audited against current code (cycle 169).

## TimelineEventType
Enum: CREATED / UPDATED / DELETED / BOOKMARKED / TAGGED / SAVED / ARCHIVED /
LINKED / SEARCHED.

## TimelineEvent
Fields: `event_id`, `event_type`, `timestamp` (datetime), `content_id`,
`metadata` (dict), `source` ("system"), `item_id`, `title`, `url`,
`description`. `to_dict` / `from_dict` serialize `event_type` to its `.value`
and `timestamp` to ISO (on `ValueError` the timestamp falls back to
`datetime.now(timezone.utc)`). `__eq__` compares by `event_id` only.

## Timeline
Holds `events: list[TimelineEvent]` and `entries: list[TimelineEntry]`.
- `add_event(event)` — appends and re-sorts `events` **ascending** by
  timestamp (oldest first).
- `add_entry(item_id, title, event_type=SAVED, timestamp=None, url="",
  description="", metadata=None) -> TimelineEntry` — builds a `TimelineEntry`
  (timestamp defaults to now, metadata to `{}`), appends to `entries`, re-sorts
  `entries` **reverse** (newest first), returns the entry.
- `content_ids` (property) -> set[str] — unique `content_id` over `events`.
- `get_event_count() -> int`.
- `get_events_for_content(content_id) -> list[TimelineEvent]`.
- `get_events_by_type(event_type) -> list[TimelineEvent]`.
- `get_events_in_range(start, end) -> list[TimelineEvent]` — inclusive both ends.
- `get_latest_event(content_id=None) -> TimelineEvent | None` — None when no
  (filtered) events; else the last element (newest, since `events` is
  ascending).
- `get_content_event_count(content_id) -> int`.
- `get_events_for_day(d) -> list[TimelineEvent]` — UTC day window, inclusive.
- `get_events_for_week(d) -> list[TimelineEvent]` — MONDAY-based week
  (Monday 00:00:00.000000 UTC .. Sunday 23:59:59.999999 UTC), inclusive.
- `get_events_for_month(year, month) -> list[TimelineEvent]` — UTC month
  window, inclusive.
- `get_summary() -> dict` — exactly `total_events`, `total_entries`,
  `content_ids` (list of the unique content IDs).
- `to_dict()` / `from_dict()` — serialize events + entries + event_count.

## Contract holes
- **Ordering asymmetry (documented, not a defect).** `events` is kept
  ascending (oldest first) while `entries` is kept reverse (newest first).
  `get_latest_event` relies on `events` being ascending (`[-1]` = newest).
  This is intentional but easy to break; the pinning tests should assert the
  ordering of both lists.
