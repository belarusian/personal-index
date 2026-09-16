# formatter — Exact Contract

Module: `personal_index/formatter.py` (200 lines, stdlib-only imports:
`re`, `typing`; plus domain types `IndexedPage` / `SearchResult` from
`personal_index.index`, `Interest` from `personal_index.interests`,
`ScheduledJob` from `personal_index.scheduler`).

Pure display-formatting helpers. Eleven module-level functions, all returning a
`str` (no classes, no state, no I/O). Each takes a domain object or a plain
`dict`/`list`/scalar and renders a human-readable multi-line string. None of
them mutate their input.

> **Disambiguation (near-name collision):** This page documents
> `personal_index.formatter` (module `personal_index/formatter.py`, ten
> module-level `format_*` / `truncate` / `highlight` functions — no classes).
> It is **DIFFERENT** from:
> - `personal_index.export` (see [export.md](export.md), class `Exporter` / `ExportResult`)
> - `personal_index.export_markdown` (see [export_markdown.md](export_markdown.md), class `MarkdownExporter`)
> - `personal_index.content_exporter` (see [content-exporter.md](content-exporter.md), class `ContentExporter`)
> - `personal_index.content_export_csv` (see [content-export-csv.md](content-export-csv.md), class `CSVExporter`)
> - `personal_index.bookmark_export` (see [bookmark_export.md](bookmark_export.md), class `BookmarkExporter`)
> - `personal_index.text_utils` (see [text-utils.md](text-utils.md), `truncate_text` / `highlight_text` — different signatures and semantics)
>
> Tests import from this module: `from personal_index.formatter import
> format_search_results, format_interest, format_crawl_stats, format_index_page,
> format_schedule_job, format_table, format_duration, format_file_size,
> format_timestamp, truncate, highlight` (see `tests/test_formatter.py`,
> `tests/deep/test_formatter_adversarial.py`,
> `tests/deep/test_negslice_sweep2_adversarial.py`).

## Public API

All functions are module-level and return `str`.

### format_search_results(results: list[SearchResult], limit: int = 10) -> str (line 14)

Renders numbered results. `limit` is clamped to `max(0, limit)` (a negative
limit renders nothing, identical to `limit=0`). Empty `results` returns the
literal `"No results found."`. Per result: `"{i}. {title}"`, a `URL:` line, an
optional snippet line (only when `result.snippet` is truthy), a
`Score: {relevance_score:.2f}` line, and a blank line.

### format_interest(interest: Interest) -> str (line 37)

Renders `Name: {name} [{enabled|disabled}]`, then optional `Keywords:` /
`Topics:` / `URL Patterns:` lines (each only when the corresponding list is
non-empty), then `Priority: {priority}`.

### format_crawl_stats(stats: dict[str, Any]) -> str (line 53)

Renders four fixed lines using `stats.get(key, 0)` for `pages_crawled`,
`pages_indexed`, `pages_filtered`, `errors`. Missing keys default to `0`
(never raise).

### format_index_page(page: IndexedPage) -> str (line 64)

Renders `Title:` / `URL:` / `Score: {score:.2f}` / `Indexed: {indexed_at}` /
`Words: {word_count}`, then an optional `Keywords:` line (only when
`page.keywords` is non-empty).

### format_schedule_job(job: dict[str, Any] | ScheduledJob) -> str (line 78)

Renders `Name:` / `Interval: {n} hours` / `Runs:` / `Last run:` (a falsy
`last_run` renders as `Never`) / `Seed URLs:`. Three input shapes are
accepted: a `ScheduledJob` (attribute access), a `dict` (`.get` with defaults
`name`→`'unknown'`, `interval_hours`→`0`, `run_count`→`0`, `last_run`→`None`,
`seed_urls`→`[]` via `job.get('seed_urls') or []`), and any other object
(`getattr` fallback with the same defaults). The `dict` path guards
`seed_urls` against a present-but-`None` value (`or []`); the `ScheduledJob`
and `getattr` paths read the attribute directly (see the Documented Contract
Hole for the asymmetry).

### format_table(headers: list[str], rows: list[list[str]]) -> str (line 110)

Renders a ` | `-separated text table with a `-+-` separator. Empty `headers`
or empty `rows` returns `""`. **Ragged-row policy (confirmed contract,
ARCH-83 Option A — widen to the widest row):** the table spans
`n_cols = max(len(headers), max(len(r) for r in rows))` — headers are padded
with empty strings to `n_cols`, and both the width loop and the render loop
run over `range(n_cols)`. A row **shorter** than the table is padded with
empty cells (lossless, unchanged); a row **longer** than the header widens the
table — its excess cells are rendered in extra columns (lossless, symmetric).
Column widths are the max of the header length and each cell's
`len(str(cell))` across all `n_cols` columns. E.g.
`format_table(["A", "B"], [["x", "y", "z"]])` renders a three-column table
containing `x`, `y`, `z`; `format_table(["A", "B"], [["p"]])` renders `p | `
(trailing empty column).

### format_duration(seconds: float) -> str (line 139)

`seconds < 60` → `"{seconds:.1f}s"`; `< 3600` → `"{seconds/60:.1f}m"`; else
`"{seconds/3600:.1f}h"`.

### format_file_size(size: int) -> str (line 148)

`size < 1024` → `"{size}B"`; `< 1024**2` → `"{size/1024:.1f}KB"`;
`< 1024**3` → `"{size/1024**2:.1f}MB"`; else `"{size/1024**3:.1f}GB"`.

### format_timestamp(timestamp: str | None) -> str (line 159)

Falsy `timestamp` (`None` / `""`) → `"N/A"`. Otherwise parses via
`datetime.fromisoformat` and renders `"%Y-%m-%d %H:%M:%S"`; on
`ValueError` / `TypeError` (an unparseable string) it returns the **original
string unchanged** (degrades, does not raise).

### truncate(text: str, max_length: int = 100) -> str (line 171)

`max_length` is clamped to `max(0, max_length)`. `len(text) <= max_length` →
`text` unchanged. `max_length < 3` → `text[:max_length]` (no room for the
ellipsis; a negative slice would count from the end and grow the string).
Otherwise `text[:max_length-3] + "..."` — the result is always at most
`max_length` characters.

### highlight(text: str, terms: list[str]) -> str (line 187)

Wraps each matched term in `**` markers. Falsy terms are filtered out; an
empty/filtered-empty `terms` returns `text` unchanged. Terms are combined into
a single alternation ordered **longest-first** (`sorted(terms, key=len,
reverse=True)`), each `re.escape`d, so a term that is a substring of another
(e.g. `cat` / `catalog`) is not re-matched inside the longer term's inserted
markers — each source position matches at most once.

## Invariants

- Every function returns a `str` and **never raises** on the input shapes it
  documents: missing `dict` keys default (`.get` / `getattr` with defaults),
  falsy / empty inputs hit a guard (`""`, `"No results found."`, `"N/A"`,
  unchanged `text`), and unparseable timestamps degrade to the raw string.
- None of the functions **mutate** their input (they build a fresh `lines`
  list / return a new string).
- `truncate`'s output length is **always** `<= max(0, max_length)` — the
  `max_length < 3` branch exists specifically so a negative slice index cannot
  grow the string (the neg-slice guard is pinned by
  `tests/deep/test_negslice_sweep2_adversarial.py`).
- `highlight` matches each source position **at most once** (longest-first
  single alternation), so overlapping/substring terms do not double-wrap.

## Persistence

None. The module is a pure read-only formatter: it holds no state, opens no
files, and does not persist or mutate any backing store.

## Documented Contract Hole

**`format_table` ragged-row handling — CONFIRMED contract (ARCH-83, Option A:
widen to the widest row).** The hole was that the width loop and the render
loop both iterated only over `range(len(headers))`, so a row LONGER than the
header had its excess cells silently dropped (lossy) while a row SHORTER was
padded (lossless) — an asymmetric, undocumented behavior. The architect
resolved the open choice in cycle 287 by confirming **Option A (lossless,
symmetric)** as the contract:

- `n_cols = max(len(headers), max(len(r) for r in rows))`; `headers` is padded
  with empty strings to `n_cols`; the width loop and the render loop both run
  over `range(n_cols)`.
- A row with **fewer** cells than the table: the missing columns are **padded**
  with empty cells (unchanged). E.g.
  `format_table(["A", "B"], [["p"]])` renders `p | ` (trailing empty column).
- A row with **more** cells than the header: the excess cells are **rendered in
  extra columns**, widening the table (no longer dropped). E.g.
  `format_table(["A", "B"], [["x", "y", "z"]])` renders a three-column table
  containing `x`, `y`, `z`.

The `format_table` docstring must state this exact policy (no blanket
`"Format data as a text table."` wording). The existing tests
(`test_basic_table`, `test_empty_table`, `test_no_rows`) exercise only
**rectangular** tables and must still pass unchanged; the ragged-row contract
is pinned by the new `TestFormatTable` tests named in ARCH-83
(`test_long_row_widens_table`, `test_short_row_padded`,
`test_mixed_ragged_rows`), which are the witness that this corrected contract
matches the implemented behavior.

**Adjacent behaviors that are NOT holes** (do not re-ticket):
- `format_search_results` negative-`limit` clamp (`max(0, limit)`) and the
  empty-results `"No results found."` guard — pinned by `test_empty_results`
  and the deep neg-slice sweep.
- `format_schedule_job` `dict` path present-but-`None` `seed_urls` guard
  (`job.get('seed_urls') or []`) — pinned by `test_dict_job_seed_urls_none`.
  (The `ScheduledJob` / `getattr` paths reading the attribute directly is a
  *latent* asymmetry but is **not** a reachable lossy path: `ScheduledJob.seed_urls`
  is a `list` with `default_factory=list` and the `Scheduler` constructor
  normalizes `None` → `[]`, so a `None` attribute is not produced by the
  domain types — do not ticket it as a live defect.)
- `format_timestamp` unparseable-string degradation (returns the raw string,
  does not raise) — pinned by `test_invalid_timestamp`.
- `truncate` neg-slice guard (`max_length < 3` → `text[:max_length]`, output
  always `<= max_length`) — pinned by `test_truncation_small_max_length`,
  `test_truncate_negative_max_length`, and
  `tests/deep/test_negslice_sweep2_adversarial.py`.
- `highlight` longest-first single-alternation (substring terms not
  double-wrapped) — pinned by `test_substring_terms`.
