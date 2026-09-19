# Progress (spec)

`personal_index.progress` — a DEAD progress-tracking module (0 production
importers; see the dead-module note below). It models long-running operations
as a `ProgressTracker` (state machine + step counter + timing) and offers a
`ProgressStore` for in-memory (optionally JSON-persisted) lookup of trackers.
It does **no I/O** of its own beyond the optional `save_all`/`load_all` JSON
round-trip; it is not wired into any pipeline, CLI command, or the crawl→
filter→score→tag→index flow.

> **Dead module (0 importers).** `grep -rn "import progress\b\|from
> personal_index.progress\b\|from .progress\b" personal_index/ --include=*.py`
> returns nothing. The module is exercised only by `tests/test_progress.py`
> and `tests/deep/test_progress_adversarial.py`. It is distinct from the
> `on_progress` callback parameter on `content_batch.BatchProcessor` (see
> content-batch.md) — that is a per-item hook, not this module.

## Public API — `personal_index.progress`

### `ProgressState` (Enum)
Six states: `PENDING` / `RUNNING` / `PAUSED` / `COMPLETED` / `FAILED` /
`CANCELLED`. Values are the lowercase strings.

### `ProgressStep` (dataclass)
Fields, in order: `step_id: str`, `description: str`, `completed: bool =
False`, `started_at: str | None = None`, `finished_at: str | None = None`,
`details: dict[str, Any] = {}`. `to_dict()` returns a plain dict of those
fields. **This class is never instantiated by `ProgressTracker`** — see
contract hole 1.

### `ProgressTracker` (dataclass)
Fields, in order: `operation_id: str = ""`, `operation_name: str = ""`,
`state: str = "pending"`, `total_steps: int = 0`, `current_step: int = 0`,
`steps: list[dict[str, Any]] = []`, `started_at: str | None = None`,
`completed_at: str | None = None`, `message: str = ""`,
`metadata: dict[str, Any] = {}`.

- `__post_init__` — generates `operation_id = "op_<ms>_<6-hex-uuid>"` when
  empty; stamps `started_at` when `state == "running"` and `started_at` is
  `None`.
- `progress_percent` (property) — `0.0` when `total_steps == 0`, else
  `min(100.0, current_step / total_steps * 100.0)`.
- `elapsed_seconds` (property) — `0.0` when `started_at` is falsy or not a
  parseable ISO timestamp; else seconds since `started_at` (UTC now).
- `estimated_remaining` (property) — `0.0` when `current_step == 0` or
  `elapsed_seconds == 0`; else `(elapsed_seconds / current_step) *
  (total_steps - current_step)`.
- `start()` — sets `state = RUNNING`, stamps `started_at`.
- `pause()` — `RUNNING → PAUSED` only (no-op otherwise).
- `resume()` — `PAUSED → RUNNING` only (no-op otherwise).
- `complete()` — sets `state = COMPLETED`, caps `current_step = total_steps`,
  stamps `completed_at`.
- `fail(error_message="")` — sets `state = FAILED`, `message`, `completed_at`.
- `cancel()` — sets `state = CANCELLED`, `completed_at`.
- `advance(step_description="", step_details=None)` — no-op unless
  `state == RUNNING`; else caps `current_step` at `total_steps` and appends a
  **plain dict** step (see contract hole 1).
- `set_total(total)` / `set_message(message)` — plain setters.
- `to_dict()` — dict of all fields plus computed `progress_percent` (rounded
  to 1 dp), `elapsed_seconds` and `estimated_remaining` (rounded to 2 dp).
- `from_dict(data)` (classmethod) — filters `data` to the constructor's
  `valid_keys` (drops `progress_percent`/`elapsed_seconds`/`estimated_
  remaining` and any unknown key) and constructs a fresh tracker.
- `format_bar(width=40)` — `"[<filled>█<empty>░] <pct>.1f%"` string.

### `ProgressStore`
In-memory `dict[str, ProgressTracker]` keyed by `operation_id`, with an
optional `storage_path` for JSON persistence.

- `create(operation_name, total_steps=0, metadata=None)` — builds a tracker,
  stores it, returns it.
- `get(operation_id)` — tracker or `None`.
- `list_active()` — trackers in `RUNNING`/`PAUSED`.
- `list_completed(limit=20)` — trackers in `COMPLETED`/`FAILED`/`CANCELLED`,
  sorted by `completed_at` desc; `[]` when `limit <= 0`.
- `remove(operation_id)` — `True` if present, else `False`.
- `cleanup(max_keep=50)` — removes completed trackers beyond `max_keep`;
  returns count removed.
- `save_all()` — no-op when `storage_path` is falsy; else writes the whole
  store as a JSON object `{operation_id: tracker.to_dict()}`.
- `load_all()` — `0` when `storage_path` is falsy, the file is missing, the
  JSON is malformed, or the top level is not a dict; else loads each entry
  via `ProgressTracker.from_dict` and returns the total tracker count.

## Invariants
- `progress_percent` is always within `[0.0, 100.0]` (clamped).
- `advance()` only mutates a `RUNNING` tracker; a `PENDING`/`PAUSED`/terminal
  tracker is untouched.
- `to_dict`/`from_dict` is a **lossy** round-trip: `from_dict` drops the
  computed fields (`progress_percent`, `elapsed_seconds`,
  `estimated_remaining`) and any key not in `valid_keys`, so a reloaded
  tracker recomputes them from `started_at`/`current_step`/`total_steps`.
- `ProgressStore` persistence is opt-in: with no `storage_path` the store is
  purely in-memory and nothing survives a restart.

## Contract holes

1. **`ProgressStep` is a dead class — the tracker stores plain dicts, not
   `ProgressStep` (ARCH-109):** `ProgressTracker.steps` is typed
   `list[dict[str, Any]]` (progress.py:59) and `advance()` (progress.py:133)
   appends a hand-built `dict` (`step_id`/`description`/`completed`/
   `started_at`/`finished_at`/`details`), never a `ProgressStep` instance. The
   `ProgressStep` dataclass (progress.py:26) and its `to_dict()` are therefore
   unreachable from the tracker's own API — a consumer reading
   `tracker.steps[i]` gets a `dict`, not a `ProgressStep`, and cannot call
   `ProgressStep.to_dict()` on it. The two representations duplicate the same
   six fields with no shared type, so the "step" model is split between a
   dead dataclass and a live ad-hoc dict. The deep test pins the live shape
   (`t.steps[0]["description"]`, `t.steps[0]["details"]`,
   `t.steps[0]["completed"]` — dict access), which is the witness that the
   tracker stores dicts, not `ProgressStep`.
