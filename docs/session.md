# `personal_index.session` — spec

Crawl session tracking and management. Models a single crawl run
(`CrawlSession`) with its counters (`SessionStats`), a lifecycle status enum
(`SessionStatus`), and a `SessionManager` that owns a session registry plus
optional JSON persistence (`save_session` / `load_session`). No network, no
crawl — this module only records and persists the *bookkeeping* of a crawl.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/session.py` — the crawl-session tracker
> (`SessionStatus` / `SessionStats` / `CrawlSession` / `SessionManager`).
> It is **distinct from** any HTTP/`http.client` "session" concept and from
> the `ai/cycle-*.md` gate log (a file, not a module). Two test files import
> this module: `tests/test_session.py:7` and `tests/deep/test_session.py:24`
> both do `from personal_index.session import (...)`.

## Public surface

Line numbers refer to `personal_index/session.py`.

### `SessionStatus` (line 15) — `str` Enum

| member | value |
|--------|-------|
| `ACTIVE` | `"active"` |
| `PAUSED` | `"paused"` |
| `COMPLETED` | `"completed"` |
| `FAILED` | `"failed"` |
| `STOPPED` | `"stopped"` |

### `SessionStats` (line 26) — dataclass

Fields (all default to zero/empty): `urls_crawled: int`, `urls_failed: int`,
`urls_skipped: int`, `bytes_downloaded: int`, `pages_indexed: int`,
`errors: list[str]`, `domains_seen: set[str]`.

| member | line | signature | returns |
|--------|------|-----------|---------|
| `success_rate` (property) | 38 | `() -> float` | `urls_crawled / (urls_crawled + urls_failed)`, or `0.0` when the denominator is `0` |
| `total_processed` (property) | 44 | `() -> int` | `urls_crawled + urls_failed + urls_skipped` |
| `to_dict` | 48 | `() -> dict` | 9-key dict (see below) |

`to_dict` returns exactly these keys: `urls_crawled`, `urls_failed`,
`urls_skipped`, `bytes_downloaded`, `pages_indexed`, `success_rate`,
`total_processed`, `domains_seen` (**`len(domains_seen)` — an int count, not
the set**), `error_count` (**`len(errors)` — an int count, not the list**).

### `CrawlSession` (line 68) — dataclass

Fields: `session_id: str`, `name: str = ""`, `status: SessionStatus =
SessionStatus.ACTIVE`, `started_at: float` (default `time.time()`),
`completed_at: float | None = None`, `stats: SessionStats` (default factory),
`config: dict = {}`, `metadata: dict = {}`.

| member | line | signature | returns |
|--------|------|-----------|---------|
| `duration` (property) | 81 | `() -> float \| None` | `(completed_at or time.time()) - started_at` |
| `pause` | 86 | `() -> None` | `ACTIVE -> PAUSED`; no-op from any other status |
| `resume` | 91 | `() -> None` | `PAUSED -> ACTIVE`; no-op from any other status |
| `complete` | 96 | `() -> None` | sets `COMPLETED` + `completed_at = time.time()` (idempotent) |
| `fail` | 101 | `(error: str) -> None` | sets `FAILED` + `completed_at`, appends `error` to `stats.errors` |
| `stop` | 107 | `() -> None` | sets `STOPPED` + `completed_at` |
| `record_url_crawled` | 112 | `(url: str, size: int = 0) -> None` | `urls_crawled += 1`, `bytes_downloaded += size`, `domains_seen.add(urlparse(url).netloc)` |
| `record_url_failed` | 125 | `(url: str, error: str = "") -> None` | `urls_failed += 1`; if `error` truthy, appends `f"{url}: {error}"` to `stats.errors` |
| `record_url_skipped` | 136 | `(url: str) -> None` | `urls_skipped += 1` (url not stored) |
| `record_page_indexed` | 144 | `() -> None` | `pages_indexed += 1` |
| `to_dict` | 148 | `() -> dict` | 9-key dict: `session_id`, `name`, `status` (`.value` str), `started_at`, `completed_at`, `duration`, `stats` (nested `stats.to_dict()`), `config`, `metadata` |

### `SessionManager` (line 167)

| member | line | signature | returns |
|--------|------|-----------|---------|
| `__init__` | 170 | `(storage_path: str \| None = None) -> None` | empty registry; `_active_session = None` |
| `create_session` | 175 | `(session_id, name="", config=None) -> CrawlSession` | new session; becomes active only if no active session yet; **overwrites** an existing id |
| `get_session` | 197 | `(session_id) -> CrawlSession \| None` | the session or `None` |
| `get_active_session` | 208 | `() -> CrawlSession \| None` | the active session or `None` |
| `set_active` | 218 | `(session_id) -> bool` | `True` + activates if found, else `False` |
| `list_sessions` | 232 | `() -> list[CrawlSession]` | all sessions (insertion order) |
| `list_active` | 240 | `() -> list[CrawlSession]` | sessions with `status == ACTIVE` |
| `remove_session` | 248 | `(session_id) -> bool` | `True` + removes (clears active if it was active); `False` if absent |
| `save_session` | 264 | `(session_id) -> str \| None` | path written to `<storage_path>/<session_id>.json`, or `None` if no session or no `storage_path` |
| `load_session` | 282 | `(filepath) -> CrawlSession \| None` | loaded session (registered in the registry), or `None` on any failure (see guard paths) |
| `session_count` (property) | 329 | `() -> int` | `len` of the registry |

## Invariants

- **Status transitions are guarded.** `pause` only fires from `ACTIVE`;
  `resume` only from `PAUSED`. `complete` / `fail` / `stop` are unconditional
  terminal setters (they do not check the prior status).
- **`success_rate` never divides by zero.** The denominator
  (`urls_crawled + urls_failed`) is guarded: `0.0` when it is `0`.
- **`load_session` degrades to `None`, never raises.** It returns `None` for:
  a missing file, a non-dict JSON top level, a `status` value that is not a
  valid `SessionStatus` member, a missing/empty `session_id`, and corrupt or
  truncated JSON (the `json.JSONDecodeError` is caught).
- **`save_session` is a no-op (returns `None`) when** the session id is not in
  the registry **or** `storage_path` was never set.

## Known contract hole

**Save/load round-trip silently drops `errors` and `domains_seen`** (ARCH-92).
`SessionStats.to_dict` (line 48) serializes `errors` as `error_count` (an int)
and `domains_seen` as `len(domains_seen)` (an int) — the *contents* of both
collections are not written to disk. `load_session` (line 282) reconstructs
`SessionStats` from only the five numeric fields (`urls_crawled`,
`urls_failed`, `urls_skipped`, `bytes_downloaded`, `pages_indexed`) and never
restores `errors` or `domains_seen`. So a session that recorded N error
messages and M distinct domains, when saved and reloaded, comes back with
`errors == []` and `domains_seen == set()`. The counts are preserved; the
data behind them is not. This is pinned (as the *current* behavior) by the
validator's deep tests `tests/deep/test_session.py::test_round_trip_domains_seen_lost`
and `test_round_trip_errors_lost`.
