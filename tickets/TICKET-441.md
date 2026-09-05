# TICKET-441: get_search_events/get_crawl_events docstring over-promise (blanket "optionally limited")

Status: RESOLVED (0866302)
Issue: #720
Module: personal_index/analytics.py
Class: (b) doc-drift

## Symptom
`AnalyticsTracker.get_search_events` (line ~201) and `get_crawl_events`
(line ~207) carry the blanket docstring:

    """Get search events, optionally limited."""
    """Get crawl events, optionally limited."""

The body performs behavior the docstring does not enumerate:

    events = self._search_events
    if limit:
        events = events[-limit:]
    return events

Two sub-behaviors are unclaimed:
1. A positive `limit` returns only the LAST `limit` events (the most
   recent tail), not the first N.
2. A FALSY `limit` (None or 0) returns ALL events (the `if limit:` guard
   skips the slice).

## Evidence
- personal_index/analytics.py:201-206 (get_search_events body)
- personal_index/analytics.py:207-212 (get_crawl_events body)
- tests/test_analytics.py:125-132 (limit=2 -> events[0].query == "q2", i.e. tail)

## Minimal additive fix
Reword both docstrings to state the EXACT behavior: returns the recorded
events in order; a positive `limit` returns only the last `limit` events
(the most recent tail); a falsy `limit` (None or 0) returns all events.
Add ONE pinning test asserting the returned list fields for both the
falsy-limit (all events) guard path and the positive-limit (tail) main
behavior.
