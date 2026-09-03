# TICKET-319: content_timeline.TimelineEntry.from_dict raises ValueError on a corrupt stored timestamp

- Status: OPEN
- Issue: #474
- Module: personal_index/content_timeline/timeline_entry.py
- Defect class: (a) unguarded parse — `datetime.fromisoformat(ts)` is called on a value
  that can originate from external, untrusted data.

## Symptom
`TimelineEntry.from_dict` (timeline_entry.py:52) does:
    ts = data.get("timestamp", datetime.now(timezone.utc).isoformat())
    if isinstance(ts, str):
        ts = datetime.fromisoformat(ts)
`timestamp` is a plain value read verbatim from the input dict. A corrupt/non-ISO
`timestamp` string therefore makes `from_dict` raise `ValueError: Invalid isoformat
string`. `TimelineEntry` is a public, exported model (re-exported in
`personal_index/content_timeline/__init__.py`), so `from_dict` is a deserialization
surface that accepts externally-sourced strings.

## Evidence (verified at runtime, cycle 48)
- `TimelineEntry.from_dict({"item_id": "x", "timestamp": "not-a-timestamp"})`
  -> `ValueError: Invalid isoformat string: 'not-a-timestamp'`.
- The sibling `TimelineEvent.from_dict` (timeline_event.py:65) guards the identical
  parse with `try/except ValueError: ts = datetime.now(timezone.utc)`, and a regression
  test already pins that behavior (`test_from_dict_bad_timestamp_degrades_to_datetime`).
  `TimelineEntry.from_dict` is the only remaining unguarded `fromisoformat` call site in
  the family (all others — content_feed, progress, scheduler, backup_store, url_utils,
  sitemap, export_markdown, dashboard/aggregator, search_facets — are guarded).
No test in tests/test_content_timeline.py exercised a non-ISO `timestamp` on
`TimelineEntry.from_dict` before this fix.

## Impact
A single corrupt `timestamp` string in externally-sourced timeline data makes
`TimelineEntry.from_dict` raise, aborting deserialization of the whole record. Same
defect family as TICKET-312/313 (unguarded `datetime.fromisoformat` on corrupt stored
timestamps) and the sibling `TimelineEvent.from_dict` guard.

## Fix (minimal, additive)
Guard the parse in `TimelineEntry.from_dict`: on `ValueError` (or a non-string value)
fall back to `datetime.now(timezone.utc)`, matching the sibling `TimelineEvent.from_dict`
behavior exactly. No signature or behavior change for valid timestamps. Adds regression
tests pinning the guard (corrupt string, non-string value, and a valid round-trip).
