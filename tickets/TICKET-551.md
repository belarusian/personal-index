# TICKET-551: AnalyticsTracker._compute_search_analytics docstring is a placeholder

- **File:** personal_index/analytics.py
- **Function:** `AnalyticsTracker._compute_search_analytics` (line 118)
- **Symptom (class-(b) doc-drift):** the docstring is a blanket over/under-promise.
  It says "Compute search-related analytics metrics." and "AnalyticsData with
  search-related fields populated." without enumerating WHICH fields are set,
  the guard path, or the return object.
- **Evidence line:** line 120 `"""Compute search-related analytics metrics.`
  and line 126 `AnalyticsData with search-related fields populated.`
- **Exact behavior (from the body):**
  - Always sets `data.total_searches = len(self._search_events)`.
  - Guard path: when `self._search_events` is empty, the `if` block is skipped
    entirely, so `avg_search_duration_ms` stays 0.0, `top_queries` stays [],
    `hourly_searches` stays {}, `daily_searches` stays {}.
  - When events exist:
    - `avg_search_duration_ms` = mean of the `duration_ms` values that are
      `> 0` (skips zero/negative durations; stays 0.0 if none qualify).
    - `top_queries` = `Counter(query).most_common(top_n)` (list of (query, count)).
    - `hourly_searches` = dict keyed by `"%H:00"` (hour bucket) -> count.
    - `daily_searches` = dict keyed by `"%Y-%m-%d"` (day) -> count.
    - Timestamps that fail `datetime.fromisoformat` (ValueError/TypeError) are
      silently skipped (not counted in hourly/daily).
  - Does NOT touch crawl fields (`total_crawls`, `top_domains`,
    `avg_crawl_duration_ms`, `success_count`, `error_count`) — those stay at
    their dataclass defaults.
  - Returns the populated `AnalyticsData` instance.
- **Minimal additive fix:** reword the docstring to enumerate the exact fields
  set, the guard path, the duration filter, the timestamp-skip guard, and the
  crawl-fields-not-touched note; add ONE pinning test asserting the returned
  object's fields for the normal case AND the guard (empty-events) case.
- **Status:** OPEN
- **Issue:** #978
