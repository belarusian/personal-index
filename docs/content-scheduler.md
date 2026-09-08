# Content Scheduler (spec)

`personal_index.content_scheduler` — an in-memory scheduler for crawl /
export / cleanup tasks driven by 5-field cron expressions. It parses a cron
expression into per-field value sets, computes the next run time, and lets a
caller run the tasks that are currently due. It is a pure in-memory module:
**no network I/O, no file I/O, no persistence, and no execution loop** — the
scheduler holds no state beyond what the caller adds, and it never runs a task
on its own; a task runs only when the caller invokes `run_due_tasks`. It is
not wired to any store or pipeline (nothing in `personal_index/` imports it).

The module exports two names: `TaskStatus` (a `str` `Enum`) and
`ScheduledTask` / `TaskScheduler` (the task and its manager).

## Public API

### `TaskStatus`
A `str` `Enum` with five members: `PENDING`, `RUNNING`, `COMPLETED`, `FAILED`,
`CANCELLED`. Each member's value is its lower-cased name (e.g.
`TaskStatus.PENDING == "pending"`). `CANCELLED` is defined but **never
assigned** by any method in this module.

### `ScheduledTask`
A single scheduled task.

#### `__init__(self, task_id: str, name: str, task_type: str, cron_expr: str, callback: Callable | None = None, config: dict[str, Any] | None = None, enabled: bool = True) -> None`
Stores `task_id`, `name`, `task_type`, `cron_expr`, `callback`, `config`
(`None` becomes `{}`), and `enabled`. Initializes `status =
TaskStatus.PENDING`, `created_at = datetime.now(timezone.utc)`,
`last_run = None`, `next_run = None`, `run_count = 0`, `last_error = None`,
then calls `_parse_cron()` (which sets `next_run`).

#### `_parse_cron(self) -> None` (private)
Splits `cron_expr.strip()` on whitespace into 5 fields (minute, hour,
day-of-month, month, day-of-week). If the field count is not 5, sets
`next_run = None` and returns (the task never runs). Otherwise parses each
field via `_parse_field` and, on any `ValueError` (a zero step such as `*/0`,
or a non-numeric token), sets `next_run = None` and returns — malformed
content degrades to "never runs", the same as the wrong-field-count case.
Day-of-week is parsed over the 0-7 range, `7` is folded into `0` (both are
Sunday), and the result is converted from cron DOW (0=Sunday..6=Saturday) to
Python `weekday()` (0=Monday..6=Sunday). `_dom_restricted` /
`_dow_restricted` are set to whether the dom/dow field is not `"*"`. Finally
calls `_compute_next_run()`.

#### `_parse_field(self, field: str, min_val: int, max_val: int) -> list[int]` (private)
Parses one cron field into a sorted list of in-range values. Supports `*`
(the full range), comma lists, `a-b` ranges, and `base/step` steps (where
`base` may be `*`, a single value, or a range). Values outside
`[min_val, max_val]` are dropped. A non-numeric token or a zero step raises
`ValueError` (caught by `_parse_cron`).

#### `_compute_next_run(self) -> None` (private)
Starts at `now` truncated to the minute plus one minute, and scans forward
up to 525600 minutes (one year) for the first candidate whose minute, hour,
month, and day all match. Standard cron day semantics: when **both** dom and
dow are restricted, a day matches if it satisfies dom **OR** dow; otherwise it
must satisfy dom **AND** dow. Sets `next_run` to the first match, or `None`
if no match within a year.

#### `is_due(self) -> bool`
Returns `False` if the task is disabled or `next_run is None`. Otherwise
returns `datetime.now(timezone.utc) >= self.next_run`.

#### `run(self) -> bool`
Sets `status = RUNNING`. If a `callback` is set, calls `callback(self)`. On
success sets `status = COMPLETED`, `last_run = now`, increments `run_count`,
recomputes `next_run`, and returns `True`. If the callback raises, sets
`status = FAILED`, `last_error = str(e)`, and returns `False`. A task with no
callback is a no-op success (returns `True`, `run_count` increments).

#### `to_dict(self) -> dict[str, Any]`
Returns a plain dict with exactly these keys in order: `task_id`, `name`,
`task_type`, `cron_expr`, `enabled`, `status` (the enum's `.value` string),
`created_at` (ISO), `last_run` (ISO or `None`), `next_run` (ISO or `None`),
`run_count`, `last_error`, `config`.

### `TaskScheduler`
Manages a collection of `ScheduledTask`s.

#### `__init__(self) -> None`
Initializes an empty `_tasks` dict and `_task_counter = 0`.

#### `add_task(self, name: str, task_type: str, cron_expr: str, callback: Callable | None = None, config: dict[str, Any] | None = None) -> ScheduledTask`
Increments `_task_counter`, builds a `ScheduledTask` with the auto-generated
`task_id = f"task_{counter}"`, stores it in `_tasks`, and returns it. There is
no dedup or validation on `name` / `task_type` / `cron_expr`.

#### `get_task(self, task_id: str) -> ScheduledTask | None`
Returns the task for `task_id`, or `None` if absent.

#### `list_tasks(self, task_type: str | None = None) -> list[ScheduledTask]`
Returns all tasks, or only those whose `task_type` equals the given value.

#### `remove_task(self, task_id: str) -> bool`
Deletes the task and returns `True`, or returns `False` if absent.

#### `enable_task(self, task_id: str) -> bool`
Sets `enabled = True` and returns `True`, or returns `False` if absent.

#### `disable_task(self, task_id: str) -> bool`
Sets `enabled = False` and returns `True`, or returns `False` if absent.

#### `run_due_tasks(self) -> list[dict[str, Any]]`
Iterates `_tasks` in insertion order; for each task where `is_due()` is true,
calls `task.run()` and appends `{"task_id", "name", "success", "status"}`
(`status` is the enum's `.value`). Tasks that are disabled or not yet due are
skipped. Returns the list of result dicts (empty if nothing is due).

#### `get_stats(self) -> dict[str, Any]`
Returns `{"total_tasks", "enabled", "disabled", "by_type"}` where `by_type`
maps each `task_type` to its count.

## Contract holes
1. **The scheduler is passive — there is no execution loop, tick, or
   `start`/`stop`.** `TaskScheduler` exposes no method that runs tasks on a
   timer; a task runs only when the caller explicitly invokes
   `run_due_tasks()`. The module is named a "scheduler" and its docstring
   promises to "schedule crawls, exports, and cleanup tasks", but the
   scheduling is entirely the caller's responsibility: nothing in
   `personal_index/` calls `run_due_tasks`, so out of the box no task ever
   runs. There is also no `start`/`stop`/`tick`/`run_forever` API to drive it,
   and no way to cancel a running task (`TaskStatus.CANCELLED` is defined but
   never assigned). (Most important hole — ticketed as **ARCH-28**.)
2. **`next_run` is computed once at construction and never refreshed until
   the task runs.** `is_due()` compares `now >= next_run`, but `next_run` is
   only (re)computed in `__init__` and after a successful `run()`. A task
   created long ago whose `next_run` has since passed is immediately "due" on
   the first `run_due_tasks()` call, even though its cron schedule may have
   many missed intervals in between; there is no catch-up / skip-missed
   policy, and a disabled task's `next_run` is never advanced.
3. **`add_task` has no dedup or validation.** The auto-generated
   `task_{counter}` id prevents key collisions, but the same `name` /
   `task_type` / `cron_expr` can be added any number of times (each becomes a
   distinct task), and a malformed `cron_expr` is accepted silently (the task
   is stored with `next_run = None` and simply never runs) rather than
   rejected at `add_task` time.

## Tests
`tests/test_content_scheduler.py` pins `add_task` (default / callback /
config / multiple), the default enabled + PENDING status, cron parsing
(every-minute / hourly / daily / weekly / invalid / step / range /
range-with-step / dom+dow OR / dow-only / dom-only / dow-7-is-Sunday /
dow-7-in-range / multiple / zero-step-degrades / non-numeric-degrades),
`get_task` (hit + miss), `list_tasks` (all / by-type / empty), `remove_task`
(hit + miss), `enable_task` / `disable_task` (hit + miss + re-enable),
`run` (success / failure / no-callback / run-count / last-run /
failure-preserves-error), `run_due_tasks` (due / skips-disabled /
skips-not-due), `to_dict` (before + after run, all-fields), `get_stats`
(empty / with-tasks / disabled / by-type-multiple), and the `TaskStatus`
enum values. The passive-scheduler and stale-`next_run` contract holes (1-2)
are **not** currently pinned — see ARCH-28.
