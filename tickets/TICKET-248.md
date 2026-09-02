# TICKET-248: timeline_view.py render() - wrong enum type for event_type filter

## File
personal_index/content_timeline/timeline_view.py

## Symptom
`TimelineView.render`'s `event_type` parameter is annotated with the ENTRY
`TimelineEventType` (imported from timeline_entry, line 13), but the filter
compares it against `e.event_type` where `e` is a `TimelineEvent` whose
`event_type` is the EVENT `TimelineEventType` (from timeline_event). Passing the
annotated (entry) enum silently matches nothing.

## Evidence (measured, cycle 2)
- timeline_view.py:13 `from ...timeline_entry import TimelineEventType`
- timeline_view.py:66 `event_type: TimelineEventType | None = None`
- timeline_view.py:78 `entries = [e for e in entries if e.event_type == event_type]`
- Runtime: with a TAGGED event, `render(..., event_type=EntryType.TAGGED)` ->
  total 0 (annotation says this is the type); `render(..., event_type=EvType.TAGGED)`
  -> total 1. `EntryType.TAGGED == EvType.TAGGED` is False.
- mypy flags the correct usage: arg-type error when passing the event enum.

## Minimal additive fix
Import the EVENT `TimelineEventType` (from timeline_event) in timeline_view.py and
use it for the `event_type` annotation, so the annotated type matches the filter.
Behavior for correct callers becomes correct; the entry enum is no longer the
declared type.

## Issue: #326 (gh)

## Status: OPEN
