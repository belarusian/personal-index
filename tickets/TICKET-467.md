# TICKET-467: Timeline.to_dict / from_dict drop `entries` (round-trip data loss)

## File
`personal_index/content_timeline/timeline.py`

## Symptom
`Timeline` holds two collections: `self.events` (TimelineEvent) and
`self.entries` (TimelineEntry, populated by `add_entry`). But
`to_dict()` serializes only `events` (+ `event_count`) and `from_dict()`
restores only `events`. Any `TimelineEntry` added via `add_entry` is
silently lost on a `to_dict()` -> `from_dict()` round-trip, even though
`get_summary()` reports `total_entries` for them.

## Evidence
- `to_dict` (timeline.py ~line 130): returns only
  `{"events": [...], "event_count": ...}` — no `entries` key.
- `from_dict` (timeline.py ~line 137): loops only over
  `data.get("events", [])`; never reads `entries`.
- `add_entry` (line 26) appends to `self.entries`; `get_summary`
  (line 120) counts `total_entries = len(self.entries)`.
- Existing test `test_timeline_to_dict_from_dict`
  (tests/test_content_timeline.py:246) only asserts `events` survive.

## Minimal additive fix
- `to_dict`: add `"entries": [e.to_dict() for e in self.entries]`.
- `from_dict`: after restoring events, loop over
  `data.get("entries", [])`, `TimelineEntry.from_dict` each, append to
  `timeline.entries`, and re-sort `timeline.entries` newest-first
  (reverse by timestamp) to match `add_entry`'s invariant.
- Add pinning tests: entries survive round-trip; entries re-sorted
  newest-first; empty entries list round-trips.

Issue: #775

## Status
OPEN
