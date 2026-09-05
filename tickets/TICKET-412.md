# TICKET-412

- Module: personal_index/analytics.py
- Function: AnalyticsTracker.get_crawl_stats (line 248)
- Status: RESOLVED
- Class: (b) doc-drift (docstring under-promises / does not enumerate behavior)

## Symptom
Docstring is a single blanket line: "Get detailed crawl statistics."
It does not enumerate:
  - the GUARD path: when no crawl events are recorded it returns exactly
    {"total": 0} (no other keys).
  - the RETURN dict fields for the normal path: total, avg_duration_ms,
    avg_content_size, total_content_size, status_codes, error_rate.
  - the sub-component semantics: durations counted only when duration_ms > 0;
    content sizes counted only when content_size > 0 (avg_content_size and
    total_content_size both derive from that filtered list); status_codes is a
    dict of the Counter over every event's status_code; error_rate =
    (events with a truthy error) / total.

## Evidence
personal_index/analytics.py:248-265

## Minimal additive fix
Reword the docstring to state the exact guard path and enumerate the returned
dict fields + their computation. Add ONE pinning test asserting the returned
dict fields for BOTH the normal case (all 6 fields, exact values) and the
guard/empty case (returns exactly {"total": 0}).

## Issue: #662
