Status: CLAIMED 2026-09-06
Kind: ARCH
Author: architect (cycle 170)
Issue: #992

# ARCH-6: `AnalyticsTracker._compute_crawl_analytics` blanket docstring

## Component
`personal_index.analytics.AnalyticsTracker._compute_crawl_analytics`
(analytics.py).

## Symptom
The docstring is a blanket "AnalyticsData with crawl-related fields populated."
that does not state the guard path (empty `_crawl_events` -> `total_crawls=0`
and `avg_crawl_duration_ms` / `top_domains` / `success_count` / `error_count`
all stay at their `AnalyticsData` defaults), the exact normal-path fields, or
that it leaves the search fields untouched. Its sibling
`_compute_search_analytics` was already reworded to exact-contract form in a
prior cycle, so this is a genuine class-(b) divergence, not a documented
constraint.

## Public contract (the code is the truth)
`_compute_crawl_analytics(top_n: int) -> AnalyticsData`:
- **Behavior:** always sets `data.total_crawls = len(self._crawl_events)`.
- **Guard path:** when `self._crawl_events` is empty the `if` block is skipped
  entirely, so `avg_crawl_duration_ms` stays `0.0`, `top_domains` stays `[]`,
  `success_count` stays `0`, and `error_count` stays `0` (all `AnalyticsData`
  defaults).
- **Normal path (events exist):**
  - `avg_crawl_duration_ms` = mean of the `duration_ms` values that are `> 0`
    (zero/negative durations are excluded; stays `0.0` when none qualify).
  - `top_domains` = `Counter(domain).most_common(top_n)` where `domain =
    _extract_domain(url)` and `None` domains are skipped (not counted); a list
    of `(domain, count)` tuples, at most `top_n`.
  - `success_count` = count of events with `200 <= status_code < 400`.
  - `error_count` = count of events with `status_code >= 400 OR a truthy
    error`. NOTE: an event with `200 <= status_code < 400` AND a truthy
    `error` is counted in BOTH `success_count` and `error_count` (the two
    predicates are independent, not mutually exclusive).
- **Search fields untouched:** `total_searches`, `avg_search_duration_ms`,
  `top_queries`, `hourly_searches`, `daily_searches` are never set here and
  stay at their `AnalyticsData` defaults.
- **Side effects:** none (pure).

## Acceptance criteria
- The docstring states the guard path (empty events -> the four crawl fields
  stay default), the exact normal-path fields (including the `> 0` duration
  filter, the `None`-domain skip, and the independent success/error
  predicates), and that the search fields are untouched — per parts 1-3 of
  docs/CONTRACTS.md.
- ONE pinning test asserts the RETURNED `AnalyticsData` for BOTH the normal
  case (a mix of durations, domains, and status codes, asserting
  `total_crawls` / `avg_crawl_duration_ms` / `top_domains` / `success_count` /
  `error_count` AND that the search fields stay default) AND the guard path
  (an empty tracker -> `total_crawls=0` and all four crawl fields default) —
  the guard path alongside the normal path.

## Pinning tests to add
`test_compute_crawl_analytics_pinned` (normal + empty input), asserting the
returned `AnalyticsData` fields.

## Docs page it updates
`docs/analytics.md` (the `_compute_crawl_analytics` entry + the contract-holes
line, which this ticket resolves).
