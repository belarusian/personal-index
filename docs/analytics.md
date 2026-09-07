# Analytics (`personal_index.analytics`)

Status: **spec** — audited against current code (cycle 170).

`AnalyticsTracker` records search and crawl events in memory and computes
aggregated analytics over them. No persistence is automatic; `save` / `load`
are explicit I/O.

## Dataclasses
- `SearchEvent`: `query`, `timestamp` (auto-set to `datetime.now(timezone.utc).isoformat()` in `__post_init__` when empty), `result_count=0`, `clicked_url=None`, `duration_ms=0.0`.
- `CrawlEvent`: `url`, `timestamp` (auto-set as above when empty), `status_code=0`, `content_size=0`, `duration_ms=0.0`, `error=None`.
- `AnalyticsData`: `total_searches=0`, `total_crawls=0`, `total_pages_indexed=0`, `avg_search_duration_ms=0.0`, `avg_crawl_duration_ms=0.0`, `top_queries=[]`, `top_domains=[]`, `hourly_searches={}`, `daily_searches={}`, `error_count=0`, `success_count=0`.

## AnalyticsTracker
- `__init__`: two empty lists, `_search_events` and `_crawl_events`.
- `record_search(query: str | SearchEvent, result_count=0, clicked_url=None, duration_ms=0.0) -> SearchEvent` — if `query` is already a `SearchEvent` it is used as-is (the other args are ignored); otherwise a `SearchEvent` is constructed from the args. Appends to `_search_events` and returns the event.
- `record_crawl(url, status_code=200, content_size=0, duration_ms=0.0, error=None) -> CrawlEvent` — constructs a `CrawlEvent`, appends to `_crawl_events`, returns it.
- `_compute_search_analytics(top_n) -> AnalyticsData` — search-side fields only; see its exact-contract docstring (already reworded in a prior cycle).
- `_compute_crawl_analytics(top_n) -> AnalyticsData` — crawl-side fields only; **see contract hole below** (blanket docstring).
- `get_analytics(top_n=10) -> AnalyticsData` — calls both sub-computes and merges: search fields (`total_searches`, `avg_search_duration_ms`, `top_queries`, `hourly_searches`, `daily_searches`) from the search result; crawl fields (`total_crawls`, `avg_crawl_duration_ms`, `top_domains`, `error_count`, `success_count`) from the crawl result. `total_pages_indexed` is never set by either sub-compute, so it stays the default `0`.
- `get_search_events(limit=None) -> list[SearchEvent]` / `get_crawl_events(limit=None) -> list[CrawlEvent]` — a positive `limit` returns the last `limit` events (most-recent tail); a falsy `limit` (`None` or `0`) returns all.
- `get_search_stats() -> dict` — guard: no search events -> exactly `{"total": 0}`. Normal: `total`, `avg_results`, `max_results`, `min_results`, `avg_duration_ms`/`max_duration_ms` (over `duration_ms > 0` only), `click_through_rate` (truthy `clicked_url` / total), `unique_queries`.
- `get_crawl_stats() -> dict` — guard: no crawl events -> exactly `{"total": 0}`. Normal: `total`, `avg_duration_ms` (over `duration_ms > 0`), `avg_content_size`/`total_content_size` (over `content_size > 0`), `status_codes` (Counter over ALL events), `error_rate` (truthy `error` / total).
- `save(path) -> str` — writes both event lists to `path` as JSON; returns `path`.
- `load(path) -> int` — guard: missing file, invalid JSON, or non-dict top level -> returns `0` (and does NOT clear existing events). Otherwise clears both lists, repopulates from the JSON, returns total events loaded.
- `clear()` — empties both event lists.
- `_extract_domain(url) -> str | None` (static) — `None` for a falsy url; for a scheme-prefixed url (`"://"` present) the segment between `"://"` and the first `"/"` (host incl. port, port NOT stripped); for a scheme-less url the segment before the first `"/"`; `None` if the split raises. Unlike `url_utils.extract_domain`, it does not strip a port and does not lowercase.

## Contract holes
- `_compute_crawl_analytics` blanket docstring ("AnalyticsData with crawl-related
  fields populated") — does not enumerate the guard path (empty `_crawl_events`
  -> `total_crawls=0` and `avg_crawl_duration_ms`/`top_domains`/`success_count`/
  `error_count` all stay default), the normal-path fields, or that it leaves the
  search fields untouched. Its sibling `_compute_search_analytics` is already in
  exact-contract form, so this is a genuine divergence. -> **ARCH-6**.
