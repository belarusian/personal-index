# TICKET-539: Timeline.get_events_for_week docstring omits exact week-window contract

Status: RESOLVED (merged via PR #954, issue #953 closed)

File: personal_index/content_timeline/timeline.py
Method: Timeline.get_events_for_week (def at line 102)

Symptom:
The docstring is a terse one-liner ("Get events for the week containing the
given date.") that omits the exact contract the code delivers:
  * the week is MONDAY-based: monday = d - timedelta(days=d.weekday())
  * the window is INCLUSIVE on both ends:
      start = datetime(monday.year, monday.month, monday.day, tzinfo=timezone.utc)
              (i.e. Monday 00:00:00.000000 UTC)
      end   = datetime(sunday.year, sunday.month, sunday.day, 23, 59, 59, 999999,
              tzinfo=timezone.utc)  where sunday = monday + timedelta(days=6)
              (i.e. Sunday 23:59:59.999999 UTC)
  * an event is returned iff start <= e.timestamp <= end
  * the result preserves self.events order (ascending by timestamp)

Evidence (verified live):
  get_events_for_week(date(2024,1,10))  # Wed -> week Mon 1/8 .. Sun 1/14
    includes an event at exactly Mon 1/8 00:00:00.000000 UTC (lower bound)
    includes an event at exactly Sun 1/14 23:59:59.999999 UTC (upper bound)
    excludes an event at Sun 1/7 23:59:59.999999 UTC (previous week)
    excludes an event at Mon 1/15 00:00:00.000000 UTC (next week)
  date(2024,1,10).weekday() == 2; monday = 1/10 - 2 days = 2024-01-08.

Existing tests (tests/test_content_timeline.py:
  test_get_events_for_week_monday_based) pin only that the week is Monday-based
  and that the range is inclusive at the day level (Jan 8 and Jan 14 in, Jan 7
  out). They do NOT pin the exact boundary times (Monday 00:00:00.000000 /
  Sunday 23:59:59.999999), the weekday formula, or the ordering guarantee.

Minimal additive fix:
  1. Reword the get_events_for_week docstring to state the exact contract
     (Monday-based window, the two exact UTC boundary datetimes, the inclusive
     start <= ts <= end predicate, and the ascending-order result).
  2. Add a pinning test (TestGetEventsForWeekDocstring539) that asserts the
     docstring states the contract (key phrases: "Monday", "00:00:00",
     "23:59:59", "inclusive") AND re-pins the non-obvious behaviors: an event at
     exactly Monday 00:00:00.000000 UTC is included, an event at exactly
     Sunday 23:59:59.999999 UTC is included, an event at the previous Sunday
     and the next Monday are excluded, and the result is in ascending order.

Type: (a) public method lacking an exact-contract docstring + pinning test.
No reword commit exists in history for get_events_for_week (git log on
timeline.py shows reword commits only for get_summary (TICKET-475), to_dict/
from_dict (TICKET-467), and add_entry (TICKET-466)) -- a fresh type-a case.

Issue: #953
