# app — `personal_index.app` (spec)

**DEAD MODULE.** `personal_index/app.py` (470 lines) is NEVER imported or
registered anywhere in the package: `grep -rn 'personal_index.app\|from .app\|import app\b\|PersonalIndexApp' personal_index/ --include=*.py`
returns exactly ONE hit, a docstring mention at `pipeline.py:110`
("Generic content processing pipeline used by PersonalIndexApp."), not an
import. There is no `from personal_index.app import ...` and no
`import personal_index.app` in any live module, the CLI group, or
`__main__`. The module therefore ships a public API (`PersonalIndexApp`)
that no live path constructs or calls. Its contract is audited here as the
dead-module + divergent-contract class (ARCH-100/102 pattern), not as a
live-path contract.

## Purpose (claimed)

`PersonalIndexApp` is the "application factory" that wires the core modules
together behind one object: config, interest store, search index, content
search, scheduler, and the content pipeline. It exposes a small public API
(`initialize`, `shutdown`, `process_content`, `search`, `add_interest`,
`get_stats`) plus lazy `@property` accessors for each component.

## Public API

- `PersonalIndexApp(config_path="config.yaml", data_dir=".personal_index")`
  — constructor; sets the two public fields and the private caches
  (`_config`, `_interest_store`, `_search_index`, `_content_search`,
  `_scheduler`, `_pipeline`) to `None` and `_initialized` to `False`. No I/O.
- `config` (property) — lazy `AppConfig` from `load_config(config_path)`;
  falls back to defaults on a missing/unreadable file.
- `interest_store` (property) — lazy `InterestStore(store_path=<data_dir>/interests.json)`.
- `search_index` (property) — lazy in-memory `SearchIndex()`.
- `content_search` (property) — lazy `ContentSearch()` whose `.index` is
  re-wired to `self.search_index` (so `search()` reads the same index
  `process_content` writes).
- `scheduler` (property) — lazy `Scheduler` backed by
  `ScheduleStore(<data_dir>/schedules.json)`.
- `pipeline` (property) — lazy `ContentPipeline("default")` with the
  extract → filter → score → tag steps (all `on_error="continue"`).
- `initialize()` — idempotent; `os.makedirs(data_dir, exist_ok=True)` then
  forces first-access construction of every component and sets
  `_initialized = True`.
- `shutdown()` — see "Known contract holes" (a log-only no-op).
- `process_content(url, raw_content, title="") -> dict` — `initialize()`,
  run the pipeline, and (only when `passes_filter` is truthy) add the item
  to `search_index`. Returns the pipeline-mutated dict.
- `search(query, limit=20) -> list` — `initialize()`, call
  `content_search.search`, and unwrap each `{"item": {...}, "score": s}`
  entry to the item dict with `score` set.
- `add_interest(name, keywords=None, url_patterns=None, priority=5)` —
  `initialize()`, build an `Interest`, `interest_store.add(...)`.
- `get_stats() -> dict` — `initialize()`, return a 6-field dict
  (`indexed_items`, `interests`, `scheduled_jobs`, `pipeline_steps`,
  `enabled_steps`, `data_dir`).

## Invariants

- Component accessors are memoized: each property constructs its component
  exactly once and caches it on the matching `_` field.
- `content_search.index` is the SAME object as `search_index`, so
  `process_content` (which writes `search_index.add_item`) and `search`
  (which reads `content_search.search`) operate on one shared index.
- `initialize()` is idempotent (guarded by `_initialized`).

## Known contract holes

- **`shutdown()` is a log-only no-op with a dead guard and a false docstring
  claim (ARCH-105).** `app.py:333-347`: the method body is
  `if self._interest_store: pass` followed by a single `logger.info(...)`.
  The `if` guard tests a field whose branch is a bare `pass` — dead code that
  performs no teardown. The docstring (app.py:342) justifies this with
  "No persistence, no component teardown (InterestStore has no save method)",
  but that claim is FALSE: `personal_index/interests.py:44` defines
  `InterestStore._save`, and it is called on every mutation
  (`add` at interests.py:58, `remove` at interests.py:63). So the "no save
  method" rationale is wrong, and the guard + `pass` are a dead field check
  that does nothing. See tickets/ARCH-105.md.
