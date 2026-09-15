# Scheduler (spec)

`personal_index.scheduler` — persistent, file-backed management of scheduled
crawl jobs. It stores `ScheduleEntry` records (each wrapping a `ScheduleConfig`)
in a JSON file via `ScheduleStore`, and `Scheduler` layers crawl execution on
top (it drives a real `Crawler` against the entry's seed URLs and indexes the
resulting pages into a `SearchIndex`). It is WIRED: `cli.py` imports
`ScheduleConfig`/`ScheduleEntry`/`ScheduleStore` (lines 1105/1149/1186/1201/1236),
`app.py:13` imports `Scheduler`/`ScheduleStore`, and `formatter.py:11` imports
`ScheduledJob`.

> **Near-name distinction (do not confuse):** this page documents
> `personal_index/scheduler.py` (file-backed, `ScheduleStore` + `Scheduler`).
> The SEPARATE page `content-scheduler.md` documents
> `personal_index/content_scheduler.py` (in-memory, cron-expression driven,
> `TaskScheduler` + `ScheduledTask`, no persistence). They share the word
> "scheduler" but are different modules with different classes; the tests
> import `from personal_index.scheduler import ...` for THIS module.

The module exports five names: `ScheduleConfig`, `ScheduleEntry`,
`ScheduleStore`, `Scheduler`, and `ScheduledJob`.

## Public API

### `ScheduleConfig`
A `@dataclass` describing one crawl job's parameters. Fields (all with
defaults): `interval_hours: int = 24`, `enabled: bool = True`,
`seed_urls: list[str] = []`, `max_pages_per_run: int = 50`,
`crawl_depth: int = 2`, `delay: float = 1.0`.

### `ScheduleEntry`
A `@dataclass` for one stored schedule. Fields: `name: str`,
`config: ScheduleConfig`, `run_count: int = 0`,
`total_pages_indexed: int = 0`, `last_run: datetime | None = None`,
`next_run: datetime | None = None`.

### `ScheduleStore`
A `@dataclass` persistent store keyed by entry name.

- `path: str` — the JSON file path.
- `__post_init__` calls `_load()` on construction.
- `_load()` — reads `path`; if the file is absent, or the JSON is corrupt,
  non-dict, or any entry has a missing key / unparseable timestamp, it
  **silently resets `self._entries = {}`** (no warning, no exception). This
  degradation is intentional and pinned by `tests/test_scheduler.py`
  (`test_null_storage_resets_to_empty`, `test_corrupt_last_run_degrades_to_empty`,
  `test_corrupt_next_run_degrades_to_empty`) and
  `tests/deep/test_defensive_load_sweep_adversarial.py`.
- `_save()` — writes all entries to `path`. **Non-atomic:** it opens the
  target file directly with `open(self.path, "w")` (line 108), which truncates
  the existing file at open time, then `json.dump`s. A crash between the
  truncate and the completed write leaves a truncated/empty file; the next
  `_load()` then silently resets the store to empty (see above), so a single
  interrupted save permanently loses ALL schedule entries. See ARCH-104.
- `add(entry)` — insert/overwrite by `entry.name`, then `_save()`.
- `get(name) -> ScheduleEntry | None`.
- `remove(name) -> bool` — deletes and `_save()`s; returns `False` if absent.
- `update(entry)` — overwrite by `entry.name`, then `_save()`.
- `list_all() -> list[ScheduleEntry]`.

### `Scheduler`
A `@dataclass` taking `interest_store: InterestStore`,
`search_index: SearchIndex`, `schedule_store: ScheduleStore`.

- `add_schedule(name, seed_urls, interval_hours=24, max_pages_per_run=50,
  crawl_depth=2, delay=1.0) -> ScheduleEntry` — builds a `ScheduleConfig`,
  sets `next_run = datetime.now(timezone.utc)` (immediately due), stores it.
- `add_job(name, seed_urls=None, interval_hours=24, **kwargs) -> ScheduleEntry`
  — CLI-compatible alias for `add_schedule` (`None` seed_urls becomes `[]`).
- `remove_schedule(name) -> bool` / `remove_job(name) -> bool` (alias).
- `toggle_schedule(name) -> ScheduleEntry | None` — flips
  `config.enabled`, persists via `update`.
- `get_due_schedules() -> list[ScheduleEntry]` — enabled entries whose
  `next_run is None or next_run <= now(utc)`.
- `update_next_run_times()` — for each entry with a `last_run`, sets
  `next_run = last_run + interval_hours` and persists. **Dead in the live
  path:** no production code calls it (only `tests/test_scheduler.py` does);
  `run_schedule` computes `next_run` inline instead.
- `run_schedule(name) -> int` — runs a real `Crawler` over the entry's seed
  URLs, indexes each page into `search_index`, then increments `run_count` /
  `total_pages_indexed`, sets `last_run = now(utc)`,
  `next_run = last_run + interval_hours`, and persists. Returns the page
  count. Returns `0` if the entry is missing or disabled.
- `list_jobs() -> list[ScheduleEntry]`.

### `ScheduledJob`
A `@dataclass` (CLI-facing view). Fields: `name: str`,
`seed_urls: list[str] = []`, `interval_hours: int = 24`, `run_count: int = 0`,
`last_run: str | None = None`, `next_run: str | None = None`,
`enabled: bool = True`. Note `last_run`/`next_run` are `str` here (ISO
strings), unlike `ScheduleEntry`'s `datetime`. Consumed by
`formatter.format_schedule_job` (`formatter.py:78`).

## Invariants

- A `ScheduleStore` always reflects its file after any mutating call
  (`add`/`remove`/`update` all `_save()`).
- `get_due_schedules` never returns disabled entries.
- `run_schedule` on a missing/disabled entry is a no-op returning `0`.

## Known contract holes

- **Non-atomic `_save`** (line 108): `open(self.path, "w")` truncates before
  writing; combined with the silent-empty `_load`, an interrupted save
  permanently loses all entries. See **ARCH-104**.
- **Dead `update_next_run_times`**: defined and unit-tested but never called
  in production; `run_schedule` recomputes `next_run` inline, so the two
  code paths can diverge if one is edited without the other.
