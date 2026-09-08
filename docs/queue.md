# queue — Exact Contract

Module: `personal_index/queue.py` (251 lines)

A thread-safe priority task queue for crawl/index operations. Four public
types: `TaskPriority` (an `int` Enum), `TaskStatus` (a `str` Enum), `Task`
(a `@dataclass(order=True)`), and `TaskQueue` (a plain class). The queue is a
`heapq` min-heap of `Task` guarded by a single `threading.Lock`; a parallel
`_tasks: dict[str, Task]` gives O(1) lookup by `task_id`; a `_completed`
list retains finished tasks for introspection.

## Public API

### TaskPriority

A `@dataclass`-free `int` Enum with five members, **lower value = higher
priority**:

- `CRITICAL = 0`
- `HIGH = 1`
- `NORMAL = 2`
- `LOW = 3`
- `BACKGROUND = 4`

Because it is an `int` Enum, `priority.value` is the raw int stored on a
`Task`, and `Task` ordering is driven by that int (see `Task`).

### TaskStatus

A `str` Enum with five members:

- `PENDING = "pending"`
- `RUNNING = "running"`
- `COMPLETED = "completed"`
- `FAILED = "failed"`
- `CANCELLED = "cancelled"`

### Task

A `@dataclass(order=True)`. Field order and comparison:

- `priority: int` — `compare=True` (first sort key).
- `sequence: int` — `compare=True` (second sort key; FIFO tie-breaker).
- `task_id: str` — `compare=False`.
- `name: str = ""` — `compare=False`.
- `data: dict[str, Any] = field(default_factory=dict)` — `compare=False`.
- `status: TaskStatus = TaskStatus.PENDING` — `compare=False`.
- `created_at: float = field(default_factory=time.time)` — `compare=False`.
- `started_at: float | None = None` — `compare=False`.
- `completed_at: float | None = None` — `compare=False`.
- `error: str | None = None` — `compare=False`.
- `result: Any = None` — `compare=False`.

Because `order=True` and only `priority` + `sequence` are `compare=True`,
`heapq` orders tasks by `(priority, sequence)`: **lowest `priority` value
first** (so `CRITICAL` (0) sorts before `BACKGROUND` (4)), and within the
same priority, **lowest `sequence` first** (FIFO). The heap minimum is
therefore the *highest-priority, earliest-enqueued* task.

#### Lifecycle methods (mutate the task in place)

- `start(self) -> None` — sets `status = RUNNING`, `started_at = time.time()`.
- `complete(self, result: Any = None) -> None` — sets `status = COMPLETED`,
  `completed_at = time.time()`, `result = result`.
- `fail(self, error: str) -> None` — sets `status = FAILED`,
  `completed_at = time.time()`, `error = error`.
- `cancel(self) -> None` — sets `status = CANCELLED`,
  `completed_at = time.time()`.
- `duration` (property) -> `float | None` — `completed_at - started_at` if
  both are set, else `None`.

### TaskQueue

State: `_heap: list[Task]` (the min-heap), `_tasks: dict[str, Task]`
(id → task, includes tasks no longer in the heap), `_lock`
(`threading.Lock`), `_max_size: int`, `_sequence: int` (monotonic counter),
`_completed: list[Task]` (finished tasks, retained).

#### Constructor

- `__init__(self, max_size: int = 10000) -> None`
  Initializes all state to empty / zero; `_max_size = max_size`. **No
  validation** of `max_size` (see contract holes).

#### Enqueue / dequeue

- `enqueue(self, task_id: str, name: str = "",
  priority: TaskPriority = TaskPriority.NORMAL,
  data: dict | None = None) -> Task`
  Under `_lock`: if `len(_heap) >= _max_size`, log a warning
  ("Task queue is full, dropping lowest priority task") and call
  `_evict_lowest()` (see contract holes — it drops the *highest*-priority
  task, not the lowest). Then build `Task(priority=priority.value,
  sequence=_sequence, task_id=task_id, name=name, data=data or {})`,
  increment `_sequence`, `heapq.heappush(_heap, task)`, store
  `_tasks[task_id] = task`, and return the task. **A duplicate `task_id`
  silently overwrites** the `_tasks` entry (the old task object remains in
  the heap if it was not yet dequeued).

- `dequeue(self) -> Task | None`
  Under `_lock`: repeatedly `heapq.heappop(_heap)` until a task with
  `status == PENDING` is found; call `task.start()` on it and return it.
  Non-pending tasks (e.g. `CANCELLED` ones left in the heap by
  `cancel_task`) are popped and **discarded** (not returned, not re-pushed).
  Returns `None` when the heap is empty.

#### Lookup / lifecycle

- `get_task(self, task_id: str) -> Task | None`
  Under `_lock`: `_tasks.get(task_id)`.

- `cancel_task(self, task_id: str) -> bool`
  Under `_lock`: if the task exists **and** `status == PENDING`, call
  `task.cancel()` and return `True`; else return `False`. A cancelled task
  **stays in the heap** (it is only removed when a later `dequeue` pops it).

- `complete_task(self, task_id: str, result: Any = None) -> bool`
  Under `_lock`: if the task exists **and** `status == RUNNING`, call
  `task.complete(result)`, append it to `_completed`, return `True`; else
  return `False`.

- `fail_task(self, task_id: str, error: str) -> bool`
  Under `_lock`: if the task exists **and** `status == RUNNING`, call
  `task.fail(error)`, append it to `_completed`, return `True`; else return
  `False`.

#### Eviction

- `_evict_lowest(self) -> None` (private)
  If `_heap` is non-empty, `heapq.heappop(_heap)` (the **minimum** = the
  highest-priority task) and, if that task's `task_id` is in `_tasks`,
  `task.cancel()` and `del _tasks[task_id]`. See contract holes: this drops
  the *highest*-priority task while the caller logs "dropping lowest
  priority task".

#### Introspection

- `size` (property) -> `int` — `len(_heap)` (tasks still in the heap,
  including `CANCELLED` ones not yet dequeued).
- `pending_count` (property) -> `int` — count of heap tasks with
  `status == PENDING`.
- `completed_count` (property) -> `int` — `len(_completed)` (finished
  **completed or failed** tasks retained).
- `get_stats(self) -> dict`
  Under `_lock`: builds `status_breakdown` by counting `status.value` over
  `_tasks.values()` (the dict, **not** the heap) and returns
  `{"queue_size": len(_heap), "total_tasks": len(_tasks),
  "completed": len(_completed), "status_breakdown": status_breakdown}`.
  Note `queue_size` (heap) and `total_tasks` (dict) count **different
  populations** — a dequeued (RUNNING) task is in `_tasks` but not in
  `_heap`.
- `clear_completed(self, keep: int = 100) -> None`
  Under `_lock`: if `len(_completed) > keep`, trim to the most recent `keep`
  (`_completed = _completed[-keep:]`). **Never called automatically** —
  `_completed` grows without bound unless the caller invokes this.

## Contract Holes

### (ARCH-38) `_evict_lowest` drops the *highest*-priority task, not the lowest

`Task` is `@dataclass(order=True)` with `priority` as the first
`compare=True` key, and `TaskPriority` is an `int` Enum where **lower value =
higher priority** (`CRITICAL = 0` … `BACKGROUND = 4`). `heapq` is a min-heap,
so the heap **minimum** is the task with the *lowest* `priority` value — i.e.
the *highest*-priority task (a `CRITICAL` task sorts before a `BACKGROUND`
one).

`_evict_lowest` does `heapq.heappop(self._heap)` — it pops that **minimum** —
and cancels + deletes it. So when the queue is full, `enqueue` evicts the
**most important** pending task (the `CRITICAL`/earliest one), while logging
`"Task queue is full, dropping lowest priority task"`. The method name, the
log message, and the actual behavior all disagree: the code drops the
highest-priority task, the exact opposite of what the name and log claim.

This is the single most important hole in the module: the queue's whole
purpose is to keep the most important work, and its overflow path silently
discards it. A defensible contract: on overflow, evict the task with the
**highest** `priority` value (lowest importance, e.g. `BACKGROUND`), breaking
ties by **highest** `sequence` (the most recently enqueued among the least
important) — i.e. pop the heap **maximum**, not the minimum — and make the
log message match. Concretely, with a full queue holding one `CRITICAL` and
one `BACKGROUND` task, `enqueue` must cancel the `BACKGROUND` task and keep
the `CRITICAL` one.

### Secondary holes (documented, not separately ticketed)

- **Duplicate `task_id` overwrites silently.** `enqueue` does
  `_tasks[task_id] = task` with no existence check; a second `enqueue` with
  the same id replaces the dict entry while the first task object may still
  sit in the heap, so `get_task` returns the new task and the old one is
  unreachable by id (but still dequeue-able).
- **`get_stats` mixes two populations.** `queue_size` counts the heap;
  `total_tasks` and `status_breakdown` count the `_tasks` dict, which also
  holds dequeued (RUNNING) and finished tasks. The two numbers are not
  comparable and `status_breakdown` can report `running`/`completed` counts
  that `queue_size` does not reflect.
- **`_completed` is unbounded.** `complete_task` / `fail_task` append to
  `_completed` and nothing trims it except a manual `clear_completed(keep)`
  call; a long-running queue accumulates every finished task in memory.
- **`max_size` is unvalidated.** `max_size <= 0` makes `len(_heap) >=
  _max_size` true on the very first `enqueue`, so every `enqueue` evicts the
  (just-pushed) task's predecessor and the queue never holds more than one
  task; a negative `max_size` behaves the same with no error.
