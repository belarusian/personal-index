# ARCH-28: content_scheduler is a passive scheduler with no execution loop and a stale next_run

- **Component:** `personal_index/content_scheduler.py`
- **Status:** OPEN
- **Issue:** #1076
- **Carry-forward:** ARCH-2 (#983) — advance the docs umbrella one page
  (docs/content-scheduler.md is the page this cycle).

## Symptom
`TaskScheduler` is named a "scheduler" and its module docstring promises to
"schedule crawls, exports, and cleanup tasks", but it is entirely **passive**:
there is no execution loop, no `start`/`stop`/`tick`/`run_forever`, and no
timer. A task runs only when the caller explicitly invokes
`run_due_tasks()`. Nothing in `personal_index/` calls `run_due_tasks`, so out
of the box no task ever runs. Compounding this, `next_run` is computed once at
construction (and only re-computed after a successful `run()`), so a task
created long ago is immediately "due" on the first `run_due_tasks()` call with
no catch-up / skip-missed policy, and a disabled task's `next_run` is never
advanced. `TaskStatus.CANCELLED` is defined but never assigned.

## Evidence
- `personal_index/content_scheduler.py:178` — `class TaskScheduler` exposes
  only `add_task` / `get_task` / `list_tasks` / `remove_task` / `enable_task` /
  `disable_task` / `run_due_tasks` / `get_stats`; no loop or timer method.
- `personal_index/content_scheduler.py:235` — `run_due_tasks` is the only
  entry point that runs tasks, and it is caller-driven.
- `personal_index/content_scheduler.py:116` — `_compute_next_run` is called
  only from `_parse_cron` (construction) and `run` (line 155); `is_due`
  (line 139) compares `now >= next_run` against a value that is never
  refreshed between runs.
- `grep -rn 'run_due_tasks\|TaskScheduler' personal_index/` — no caller inside
  the package (the module is not wired to any store or pipeline).

## Public contract (what the fix must preserve / define)
- `TaskScheduler.run_due_tasks(self) -> list[dict[str, Any]]` keeps its
  signature and its per-task result shape
  `{"task_id", "name", "success", "status"}`.
- `ScheduledTask.is_due(self) -> bool` keeps its guard: `False` when disabled
  or `next_run is None`.
- The fix must define the scheduling semantics explicitly rather than leave
  them implicit. Two acceptable shapes (pick one, document it in
  docs/content-scheduler.md, and pin it):
  1. **Add a driver** — e.g. `TaskScheduler.tick(self, now: datetime | None = None)
     -> list[dict[str, Any]]` that refreshes each task's `next_run` and runs
     the due ones, plus a documented `run_forever`/`start`/`stop` (or an
     explicit "caller must call `tick`/`run_due_tasks` on a timer" contract).
  2. **Make it honest** — if the module is intended to stay passive, reword
     the module docstring and `TaskScheduler` docstring to state that it holds
     tasks and computes due-ness but performs **no** scheduling of its own,
     and document the stale-`next_run` / no-catch-up behavior as the contract.

## Acceptance criteria
- The module's docstring and `TaskScheduler` docstring state the exact
  scheduling semantics (who drives execution, and what happens to a task whose
  `next_run` has passed without a run).
- Either a driver method exists (shape 1) or the passive contract is stated
  explicitly (shape 2); the two are not left ambiguous.
- The stale-`next_run` behavior is either fixed (refresh on tick / catch-up
  policy) or documented as the intended contract.
- `TaskStatus.CANCELLED` is either used by a cancel path or removed /
  documented as reserved.
- Existing `tests/test_content_scheduler.py` stays green.

## Pinning tests to add (in tests/test_content_scheduler.py)
- A test that pins the driver contract: after constructing a task whose
  `next_run` is in the past, calling the driver (shape 1) or `run_due_tasks`
  (shape 2) behaves as the documented contract states (runs it, or documents
  the immediate-due behavior).
- A test that pins the stale-`next_run` / catch-up behavior: a task created
  with a past `next_run` and never run reports the documented due-ness.
- A test that pins the disabled-task `next_run` behavior (it is not advanced).
- A guard-path pin: a task with a malformed `cron_expr` (`next_run is None`)
  is never run by `run_due_tasks` and is reported as not-due.

## Docs
`docs/content-scheduler.md` (added this cycle) carries the full public API and
the contract-holes section; update its "Contract holes" section in the SAME PR
that resolves this ticket.
