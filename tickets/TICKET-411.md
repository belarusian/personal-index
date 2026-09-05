# TICKET-411

- Module: personal_index/analytics.py
- Function: AnalyticsTracker.get_search_stats (line 214)
- Status: RESOLVED
- Class: (b) doc-drift (docstring under-promises / does not enumerate behavior)

## Symptom
Docstring is a single blanket line: "Get detailed search statistics."
It does not enumerate:
  - the GUARD path: when no search events are recorded it returns exactly
    {"total": 0} (no other keys).
  - the RETURN dict fields for the normal path: total, avg_results,
    max_results, min_results, avg_duration_ms, max_duration_ms,
    click_through_rate, unique_queries.
  - the sub-component semantics: durations only counted when duration_ms > 0;
    click_through_rate = clicked / total where clicked counts events with a
    truthy clicked_url; unique_queries = distinct query strings.

## Evidence
personal_index/analytics.py:214-232

## Minimal additive fix
Reword the docstring to state the exact guard path and enumerate the returned
dict fields + their computation. Add ONE pinning test asserting the returned
dict fields for BOTH the normal case (all 8 fields, exact values) and the
guard/empty case (returns exactly {"total": 0}).

## Issue: #660
