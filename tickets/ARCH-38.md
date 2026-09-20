# ARCH-38: queue — `_evict_lowest` drops the *highest*-priority task, not the lowest

Status: CLOSED (implemented + merged cycle 350, PR #1678, commit 3152390: _evict_lowest now evicts heap maximum on overflow; pinning tests + deep pin + docs updated)
Component: `personal_index/queue.py`
Issue: #1107
Refs: ARCH-2 (#983 umbrella)

## Architect decision (cycle 281): target contract stands
The target contract (on overflow, evict the HIGHEST `priority` value / lowest
importance, keep the CRITICAL task) is the correct, intended behavior — the
current `heappop`-minimum eviction drops the most important task, the hole this
ticket exists to fix. The validator's deep test
`tests/deep/test_queue_adversarial.py::TestEvictLowestDefect::
test_overflow_keeps_critical_evicts_background` is `@pytest.mark.xfail(strict=True)`
and already asserts the FIXED behavior; once the code is fixed it XPASS-strict
-> RED, so the validator must remove the `xfail(strict=True)` marker (IMPL-9).
That is a `tests/deep/**` change the architect cannot make, so this ticket stays
OPEN-PUSHBACK for the validator; the docs/decision half (this confirmation) is
done.

## Symptom

`Task` is `@dataclass(order=True)` with `priority` as the first
`compare=True` key, and `TaskPriority` is an `int` Enum where **lower value =
higher priority** (`CRITICAL = 0`, `HIGH = 1`, `NORMAL = 2`, `LOW = 3`,
`BACKGROUND = 4`). `heapq` is a min-heap, so the heap **minimum** is the task
with the *lowest* `priority` value — i.e. the *highest*-priority task (a
`CRITICAL` task sorts before a `BACKGROUND` one).

`TaskQueue._evict_lowest` does `heapq.heappop(self._heap)` — it pops that
**minimum** — then `task.cancel()` and `del self._tasks[task_id]`. So when the
queue is full, `enqueue` evicts the **most important** pending task (the
`CRITICAL` / earliest-enqueued one), while logging
`"Task queue is full, dropping lowest priority task"`. The method name, the
log message, and the actual behavior all disagree: the code drops the
highest-priority task, the exact opposite of what the name and log claim.

This is the single most important hole in the module: the queue's whole
purpose is to keep the most important work, and its overflow path silently
discards it.

## Public contract (target)

On overflow (`len(_heap) >= _max_size`), `enqueue` must evict the task with
the **highest** `priority` value (lowest importance, e.g. `BACKGROUND`),
breaking ties by **highest** `sequence` (the most recently enqueued among the
least important) — i.e. pop the heap **maximum**, not the minimum — and the
log message must match the behavior. Concretely:

- With a full queue holding one `CRITICAL` task and one `BACKGROUND` task,
  `enqueue` must cancel the `BACKGROUND` task and keep the `CRITICAL` one.
- Among tasks of equal priority, the most recently enqueued (highest
  `sequence`) is evicted first.
- The evicted task is `cancel()`-ed and removed from `_tasks` (as today), and
  the log message names the *lowest*-priority task (matching the behavior).

## Acceptance criteria

1. With `max_size = 2`, enqueue a `CRITICAL` task and a `BACKGROUND` task,
   then enqueue a third task: the `BACKGROUND` task is cancelled and removed
   from `_tasks`; the `CRITICAL` task is still present (`get_task` returns it,
   `status == PENDING`).
2. With `max_size = 2` and two `NORMAL` tasks (ids `a` then `b`), enqueue a
   third task: task `b` (the later `sequence`) is evicted, task `a` is kept.
3. The evicted task's `status` is `CANCELLED` and it is absent from
   `_tasks` (so `get_task` returns `None` for it).
4. The log message on overflow names the *lowest*-priority task (consistent
   with the evicted task actually being the lowest-priority one).
5. A non-full queue (below `max_size`) evicts nothing: all enqueued tasks
   remain `PENDING` and present in `_tasks`.

## Pinning tests to add (implementer)

- `test_evict_drops_lowest_priority_not_highest`: `max_size=2`; enqueue
  `CRITICAL` (`t_crit`) then `BACKGROUND` (`t_bg`); enqueue a third task
  (`t_new`). Assert `get_task(t_bg).status == TaskStatus.CANCELLED`,
  `get_task(t_bg) is None` (removed from `_tasks`), and
  `get_task(t_crit).status == TaskStatus.PENDING` (the highest-priority task
  survives the overflow — pins the inverted-eviction fix).
- `test_evict_tie_breaks_by_sequence`: `max_size=2`; enqueue two `NORMAL`
  tasks `a` then `b`; enqueue a third. Assert `b` is evicted
  (`get_task(b) is None`) and `a` is kept (`get_task(a).status == PENDING`)
  (pins the highest-`sequence` tie-break among equal priority).
- `test_no_evict_below_max`: `max_size=10`; enqueue three tasks; assert all
  three are `PENDING` and present in `_tasks` (the normal-case pin alongside
  the overflow guard path).

## Docs

`docs/queue.md` (authored this cycle) documents the current behavior and lists
this as the primary contract hole. Update the `_evict_lowest` entry and the
"Contract Holes" section in the **same PR** that implements the fix, so the
page reflects the corrected lowest-priority-eviction semantics.

**Reconciliation note (architect, cycle 314, 2026-09-19):** blocker confirmed validator-owned (tests/deep/** xfail-strict pin of the fixed behavior) — architect cannot edit tests/deep/**; stays OPEN-PUSHBACK for the IMPL/validator lane.

**Systemic blocker (architect, cycle 315, 2026-09-19):** all 5 OPEN-PUSHBACK ARCH tickets (38/43/66/83/84) share ONE root cause — a validator-owned `tests/deep/**` behavioral pin the architect cannot edit. This ticket's pin: `tests/deep/test_queue_adversarial.py::TestEvictLowestDefect::test_overflow_keeps_critical_evicts_background` (xfail-strict, pins the FIXED behavior). Single unblocking action: the validator edits `tests/deep/**` (flip the xfail-strict pin so the fix does not XPASS-strict -> RED). Ticket stays OPEN-PUSHBACK.
