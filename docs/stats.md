# stats — `personal_index.stats`

Spec page (matches CURRENT code as of cycle 254).

`stats.py` is the read-only statistics reporter for the search index. It
exposes two public types: the `IndexStats` dataclass (the result shape)
and the `StatsCollector` dataclass (the reporter). It performs **no**
persistence of its own — it reads the in-memory `SearchIndex` and returns
computed values. It does **not** own the `CrawledPage` / `Interest` value types —
those live in `personal_index.models` (see `docs/content-model.md`). This
page documents `personal_index.stats` (`StatsCollector` — index statistics
aggregation over a `SearchIndex`), which is **DIFFERENT** from the other
stats/metrics/analytics modules:

- `personal_index.analytics` (`docs/analytics.md`) — `AnalyticsTracker`
  records *search/crawl events* over time and persists them; it is an event
  log, not an index aggregate.
- `personal_index.content_analytics` (`docs/content-analytics.md`) —
  `ContentAnalytics` computes analytics over *content items*; it does not
  read a `SearchIndex`.
- `personal_index.metrics` — a separate metrics module; unrelated to index
  statistics.
- `personal_index.dashboard.stats` — `RealTimeStats`, a dashboard-only
  operational-stats dataclass; it re-exports `StatsCollector` for
  convenience but is a different module.

`StatsCollector` is the single place that turns the raw `SearchIndex` page
set into the `total_pages` / `total_words` / `unique_domains` /
`avg_content_length` / `pages_with_interests` / `top_domains` /
`top_interests` / `oldest_page` / `newest_page` numbers the CLI `stats`
command and the dashboard display.

## `IndexStats` (dataclass, line 14)

Fields (in declaration order, all with defaults): `total_pages: int = 0`
(line 16), `total_words: int = 0` (line 17), `unique_domains: int = 0`
(line 18), `avg_content_length: float = 0.0` (line 19),
`pages_with_interests: int = 0` (line 23 — total interest matches across all
pages, **one per matched interest, not one per page**),
`top_domains: list[tuple[str, int]] = []` (line 24),
`top_interests: list[tuple[str, int]] = []` (line 25),
`oldest_page: datetime | None = None` (line 26),
`newest_page: datetime | None = None` (line 27).

## `CrawlStats` (dataclass, line 31) — removed (ARCH-86, Option A)

`CrawlStats` was a public `@dataclass` (four fields, all defaulting to `0`:
`total_crawls`, `total_pages_crawled`, `total_errors`, `total_bytes_fetched`)
that **nothing in the module ever produced or populated** — no method on
`StatsCollector` (or anywhere else in `personal_index/`) returned a
`CrawlStats` or set its fields. It was a dead public type: the only reference
outside its own definition was the test
`tests/test_stats.py::TestCrawlStats::test_defaults`, which merely
constructed the empty default.

**Confirmed contract (ARCH-86, Option A — remove the dead surface):** the
`CrawlStats` dataclass is **removed** from `personal_index.stats`. It is no
longer importable from the module. `get_index_stats` returns only
`IndexStats`, exactly as before — no returned value changes. The pinning
witness is `tests/test_stats.py::TestCrawlStats` (updated to assert
`CrawlStats` is no longer importable) alongside the existing
`TestGetIndexStatsDocPinning` suite, which pins that `get_index_stats` still
returns the same `IndexStats` values. See `tickets/ARCH-86.md`.

## `StatsCollector` (dataclass, line 41)

Fields (in declaration order): `search_index: SearchIndex | None = None`
(line 45). The former `interest_store: InterestStore | None = None` field
(line 44) is **removed** (ARCH-86, Option A) — it was a public field that was
accepted in the constructor but never read anywhere in the module, so
constructing `StatsCollector(interest_store=...)` now raises `TypeError`
(unexpected keyword). Interest statistics are derived from
`CrawledPage.matched_interests` (the pages), **not** from an `InterestStore`.

- `get_index_stats(self) -> IndexStats` (line 47): if `self.search_index` is
  **falsy**, returns an all-default `IndexStats` (every field at its
  dataclass default) without touching the index (line 60-61). Otherwise it
  reads `pages = self.search_index.urls()` (line 63), sets
  `stats.total_pages = len(pages)` (line 64), and delegates the per-page
  accumulation to `_accumulate_page_stats(pages)` (line 73), which returns
  `(total_words, total_content_length, domain_counts, interest_counts,
  pages_with_interests, timestamps)`. It then sets:
  - `stats.total_words = total_words` (line 75)
  - `stats.unique_domains = len(domain_counts)` (line 76)
  - `stats.avg_content_length = total_content_length /
    max(stats.total_pages, 1)` (line 77-79) — the `max(..., 1)` guards the
    division so an empty index yields `0.0`, not `ZeroDivisionError`.
  - `stats.pages_with_interests = pages_with_interests` (line 80)
  - `stats.top_domains = sorted(domain_counts.items(), key=count,
    reverse=True)[:10]` (line 81-84) — capped to the top 10.
  - `stats.top_interests = sorted(interest_counts.items(), key=count,
    reverse=True)[:10]` (line 85-88) — capped to the top 10.
  - `stats.oldest_page = min(timestamps)` / `stats.newest_page =
    max(timestamps)` (line 90-92) — set **only** when at least one page has
    a `crawled_at` timestamp; otherwise both stay `None`.
- `_accumulate_page_stats(self, pages: list[str]) -> tuple[int, int,
  dict[str, int], dict[str, int], int, list[datetime]]` (line 96): asserts
  `self.search_index is not None` (line 100), then iterates `pages`. For each
  url it calls `page = self.search_index.get(url)` (line 109) and `continue`s
  when `page is None` (line 110-111). For a present page it accumulates:
  `total_words += len(page.content.split())` (line 113),
  `total_content_length += len(page.content)` (line 114),
  `domain = extract_domain(url)` and, when truthy,
  `domain_counts[domain] += 1` (line 116-118), then for **each**
  `interest_name in page.matched_interests` it does
  `interest_counts[interest_name] += 1` **and** `pages_with_interests += 1`
  (line 120-124) — so a page matching 3 interests contributes 3 to
  `pages_with_interests`, not 1. Finally, when `page.crawled_at` is truthy it
  appends it to `timestamps` (line 126-127).
- `format_index_stats(self) -> str` (line 138): calls `get_index_stats()` and
  renders a fixed block — `=== Index Statistics ===`, `Total pages`,
  `Total words`, `Unique domains`, `Avg content length` (formatted `:.0f`),
  `Interest matches` — then, only when non-empty, a `Top domains:` section
  and a `Top interests:` section, and only when set, `Oldest page:` /
  `Newest page:` lines. Returns the `"\n".join` of the lines.

## Invariants
- `get_index_stats` and `format_index_stats` are **read-only**: they never
  mutate the `SearchIndex`; they only read `urls()` / `get()` /
  `page.content` / `page.matched_interests` / `page.crawled_at`.
- The guard path is total: a falsy `search_index` returns an all-default
  `IndexStats` and never touches the index, so `StatsCollector()` with no
  arguments is safe to call.
- `avg_content_length` can never raise `ZeroDivisionError`: the denominator
  is `max(total_pages, 1)`, so an empty index yields `0.0`.
- `top_domains` / `top_interests` are always capped to at most 10 entries,
  sorted by count descending.
- `oldest_page` / `newest_page` are `None` unless at least one page carries a
  `crawled_at` timestamp.
- `pages_with_interests` counts **interest matches** (a page matching N
  interests adds N), not distinct pages — the field comment (line 22-23) and
  the accumulation (line 120-124) agree.

## Persistence
- **None.** `StatsCollector` performs no I/O and writes no file. It reads the
  in-memory `SearchIndex` (which itself may have been loaded from disk by the
  `SearchIndex` — see `docs/search_index.md`) and returns computed values.
  There is no save/load, no serialization, and no round-trip to pin.

## Confirmed contract (ARCH-86, Option A — remove the dead surface)
`StatsCollector.interest_store` (line 44) was a **public field** that was
accepted in the constructor but **never read** anywhere in the module. The
only reference to `interest_store` in `stats.py` was its declaration at line
44; `get_index_stats` / `_accumulate_page_stats` / `format_index_stats` never
touched it. Every interest-derived statistic — `pages_with_interests`
(line 80) and `top_interests` (line 85-88) — is computed from
`page.matched_interests` (line 120), the `CrawledPage`'s own field, **not**
from the `InterestStore`.

So passing a populated `InterestStore` (e.g. one with an interest named
"Py") had **zero effect** on any returned statistic. The test fixture
`tests/test_stats.py::collector` even constructed the collector with a
populated `interest_store` (an "Py" interest added at line 16), which
masked the dead field: the tests passed whether or not the store was
populated because the store was never consulted.

**Confirmed contract (ARCH-86, Option A — remove the dead surface):** the
`interest_store` field is **removed** from `StatsCollector` (along with the
`InterestStore` import it pulled in), and the dead `CrawlStats` dataclass
(line 31) is **removed** too. `StatsCollector` then has exactly one field,
`search_index`, and its constructor is `StatsCollector(search_index=...)`;
constructing it with `interest_store=...` raises `TypeError` (unexpected
keyword). `get_index_stats` behavior is **exactly as today** — it still
returns `IndexStats` computed from `search_index` and the pages'
`matched_interests`; no returned value changes. The `StatsCollector`
docstring states that interest statistics are derived from
`CrawledPage.matched_interests` (the pages), not from an `InterestStore`.

The pinning witness is `tests/test_stats.py`: the new dead-field-removed pin
asserts `inspect.signature(StatsCollector)` has no `interest_store`
parameter and `StatsCollector(interest_store=store)` raises `TypeError`, and
the existing `TestGetIndexStatsDocPinning` suite (including
`test_guard_path_returns_all_defaults` / `test_no_search_index`) pins that
`get_index_stats` still returns the same `IndexStats` values for the same
`search_index`. See `tickets/ARCH-86.md`.

**Adjacent behaviors that are NOT holes** (do not re-ticket):
- `avg_content_length` denominator/numerator mismatch — **not** a hole:
  `SearchIndex.urls()` returns `list(self._pages.keys())` and `get()` returns
  `self._pages.get(url)` (search_index.py lines 113, 127-128), so the two are
  consistent; the `if page is None: continue` guard (line 110-111) is dead for
  a real `SearchIndex` and the `max(total_pages, 1)` guard makes the empty
  case `0.0`, not a division error.
- `pages_with_interests` counting matches-not-pages — **not** a hole: it is
  the documented, intended behavior (field comment line 22-23) and is pinned
  by `test_pages_with_interests_counts_matches_not_pages`.
- The falsy-`search_index` guard path, the top-10 cap, and the
  oldest/newest-conditional — **not** holes: all are pinned by
  `TestGetIndexStatsDocPinning`.
