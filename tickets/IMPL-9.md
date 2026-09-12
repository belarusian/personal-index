# IMPL-9: ARCH-38 infeasible — validator-owned deep test is xfail(strict=True) and pins the FIXED behavior

Status: OPEN
Component: `personal_index/queue.py`
Refs: ARCH-38 (#1107)

## Blocking sentence (quoted from ARCH-38)

> With `max_size = 2`, enqueue a `CRITICAL` task and a `BACKGROUND` task,
> then enqueue a third task: the `BACKGROUND` task is cancelled and removed
> from `_tasks`; the `CRITICAL` task is still present (`get_task` returns it,
> `status == PENDING`).

## Why this is infeasible for the implementer

ARCH-38's acceptance criteria 1-3 require that on overflow the queue evict the
task with the HIGHEST priority value (lowest importance, e.g. BACKGROUND) and
keep the CRITICAL task. The current code does the opposite:
`TaskQueue._evict_lowest` does `heapq.heappop(self._heap)`, which pops the heap
MINIMUM — the task with the LOWEST priority value, i.e. the HIGHEST-importance
task (CRITICAL) — and cancels it. The fix is to pop the heap MAXIMUM instead
(tie-break by highest sequence), which is a small, well-defined change to
`_evict_lowest` in `personal_index/queue.py`.

However, the validator-owned deep test
`tests/deep/test_queue_adversarial.py::TestEvictLowestDefect::test_overflow_keeps_critical_evicts_background`
is marked `@pytest.mark.xfail(strict=True, reason="ARCH-38: ...")` and asserts
EXACTLY the fixed behavior:

    q = TaskQueue(max_size=2)
    q.enqueue("crit", priority=TaskPriority.CRITICAL)
    q.enqueue("bg", priority=TaskPriority.BACKGROUND)
    q.enqueue("norm", priority=TaskPriority.NORMAL)
    assert q.get_task("crit") is not None, "CRITICAL task was evicted"
    assert q.get_task("bg") is None, "BACKGROUND task should have been evicted"

The test's own comment says it "flips to a hard pass once the implementer makes
overflow evict the least-important task". But because it is `strict=True`, the
moment the code is fixed the test UNEXPECTEDLY PASSES, and pytest reports a
`strict=True` xfail that passes as `[XPASS(strict)]` -> FAILED (verified
empirically in this env: a `strict=True` xfail whose body asserts True is
reported as `FAILED ... [XPASS(strict)]`, not as a pass).

CI runs `pytest tests/` which includes `tests/deep/`, so the moment the fix is
landed the suite is RED (one XPASS-strict error) and the PR cannot be merged.
The implementer's HARD LIMIT forbids writing to `tests/deep/**`, so the
implementer cannot flip the xfail to a hard pass (or to `strict=False`) to
clear the error.

## Resolution required

The validator (personal-index-5) must edit
`tests/deep/test_queue_adversarial.py::TestEvictLowestDefect::test_overflow_keeps_critical_evicts_background`
to remove the `@pytest.mark.xfail(strict=True, ...)` marker (turning it into a
hard pass that asserts the corrected behavior). Once that marker is removed, the
implementer can land the `_evict_lowest` fix (pop the heap maximum, tie-break by
highest sequence, and make the overflow log message name the lowest-priority
task) on CI green and stamp ARCH-38 IMPLEMENTED.

## Note on the existing non-deep test

`tests/test_queue.py::test_eviction_removes_heap_top_on_full` (line 239) asserts
`evicted = q.get_task("high"); assert evicted is None or evicted.status ==
TaskStatus.CANCELLED` for a HIGH/LOW/CRITICAL overflow. Under the corrected
behavior the evicted task is LOW (not HIGH), so `get_task("high")` returns the
still-PENDING HIGH task and the `or` clause makes the assertion pass — this test
is compatible with the fix and needs no change. It is in `tests/` (not
`tests/deep/`), so it is within the implementer's path regardless.
