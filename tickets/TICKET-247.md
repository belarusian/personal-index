# TICKET-247: content_timeline package - no functional test coverage

## File
personal_index/content_timeline/ (timeline.py, timeline_entry.py,
timeline_event.py, timeline_view.py)

## Symptom
The content_timeline package (4 modules, ~407 lines of real logic: date-range
queries, serialization round-trips, view rendering) has NO dedicated test file.
The only coverage comes from tests/test_imports.py, which merely imports each
module (module-level execution only). Function bodies are never exercised.

## Evidence (measured, cycle 2)
- `grep -rln content_timeline tests/` -> no test file references the package.
- Coverage: timeline.py 37% (misses 22-23,36-47,52,56,60,64,70,74-81,85,90-92,
  97-102,106-110,114,122,130-135), timeline_view.py 58% (misses 69-96 = render),
  timeline_entry.py 69%, timeline_event.py 74%.
- Uncovered logic includes: add_event/add_entry sort order, get_events_for_day/
  week/month range boundaries, get_latest_event, to_dict/from_dict round-trips,
  TimelineView.render in DAY/WEEK/MONTH modes + event_type filter.

## Minimal additive fix
Add tests/test_content_timeline.py covering: Timeline add_event/add_entry + sort
order; get_events_for_day/week/month boundary inclusion; get_latest_event (with +
without content_id); get_events_by_type; get_events_in_range; TimelineEvent and
TimelineEntry to_dict/from_dict round-trips; TimelineView.render in all three
modes with and without event_type filter.

## Issue: #325 (gh)

## Status: OPEN
