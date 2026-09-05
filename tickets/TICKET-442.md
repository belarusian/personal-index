# TICKET-442: record_crawl docstring is a blanket one-liner (class-b doc-drift)

Status: RESOLVED (279927d)
Issue: #722
Module: personal_index/analytics.py
Function: AnalyticsTracker.record_crawl (line 88)

## Symptom
`record_crawl`'s docstring is the blanket one-liner `"""Record a crawl event."""`
and does not enumerate the behavior the body actually performs, while its
sibling `record_search` (line 65) carries a full Args section. The body:
  1. constructs a `CrawlEvent` from `url` (required), `status_code` (default
     200), `content_size` (default 0), `duration_ms` (default 0.0), and
     `error` (default None);
  2. appends the constructed event to the internal crawl event list
     (`self._crawl_events`);
  3. returns the constructed `CrawlEvent` (whose `timestamp` is auto-set by
     the dataclass `__post_init__` when not provided).
None of (1)'s parameter defaults, (2)'s side effect, or (3)'s return value is
stated in the docstring.

## Evidence
- personal_index/analytics.py:91  `"""Record a crawl event."""`
- personal_index/analytics.py:92-100  body: `CrawlEvent(...)` + `self._crawl_events.append(event)` + `return event`
- personal_index/analytics.py:68-74  sibling `record_search` docstring enumerates Args + return (asymmetry)

## Minimal additive fix
Reword the docstring to state the EXACT behavior: enumerate the five
parameters and their defaults, the append-to-internal-list side effect, and the
returned `CrawlEvent`. Add ONE pinning test class asserting the returned
`CrawlEvent` fields for both the main behavior (explicit params) and the guard
path (defaults), plus the internal-list side effect witnessed via
`get_crawl_events()`. No behavior change.

## Line-shift guard
Whole tests/ tree grepped for literal line-range pins: only
tests/test_exception_handling.py pins content_categorizer/linker/pipeline/
url_history by hardcoded lineno ranges; none reference analytics.py. Safe.
