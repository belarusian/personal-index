# `personal_index.performance_monitor` — spec

In-process performance metrics collection and aggregation. Three public types,
no I/O, no persistence, no network, no threading.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/performance_monitor.py` — the `MetricSample` / `MetricStats`
> dataclasses + the `PerformanceMonitor` class + the `TimerContext` context
> manager. It is **distinct from** `personal_index/metrics.py`
> (`docs/metrics.md` — `SystemMetrics` + `MetricsCollector`, system snapshots
> via `os.statvfs` / `resource.getrusage`) and from `personal_index/stats.py`
> (`docs/stats.md` — `StatsCollector` / `IndexStats` / `CrawlStats`, a read-only
> index aggregate). The tests import from this module:
> `tests/test_performance_monitor.py:5` does
> `from personal_index.performance_monitor import MetricSample, MetricStats,
> PerformanceMonitor`, and the validator deep tests
> `tests/deep/test_zero_cap_eviction_sweep_adversarial.py:31` and
> `tests/deep/test_url_history_adversarial.py:267` import `PerformanceMonitor`.

## Public surface

### `MetricSample` (dataclass, line 16)

A single metric data point. Fields (lines 19-22):

| field | type | default |
|-------|------|---------|
| `name` | str | (required) |
| `value` | float | (required) |
| `timestamp` | float | `field(default_factory=time.time)` |
| `tags` | dict | `field(default_factory=dict)` |

### `MetricStats` (dataclass, line 26)

Aggregated statistics for one metric name. Raw fields (lines 29-34):

| field | type | default |
|-------|------|---------|
| `name` | str | (required) |
| `count` | int | `0` |
| `total` | float | `0.0` |
| `min_val` | float | `float("inf")` |
| `max_val` | float | `float("-inf")` |
| `sum_sq` | float | `0.0` |

Derived properties (all read-only, computed on access):

| property | line | formula | guard path |
|----------|------|---------|------------|
| `mean` | 37 | `total / count` | `count == 0` → `0.0` |
| `stddev` | 42 | `sqrt(max(0.0, sum_sq/count - mean**2))` (population) | `count < 2` → `0.0` |
| `p50` | 55 | `mean` (approximation) | — |
| `p95` | 60 | `mean * 1.5` (approximation) | — |
| `p99` | 65 | `mean * 2.0` (approximation) | — |

Note: `p50`/`p95`/`p99` are **documented approximations** of the mean, not true
percentiles — the module keeps no ordered value list, so it cannot compute a
real quantile. `stddev` is the **population** standard deviation (divides by
`count`, not `count - 1`).

### `PerformanceMonitor` (class, line 70)

Constructor `__init__(self, window_size: int = 1000)` (line 73) stores three
private dicts:

| attribute | line | type | purpose |
|-----------|------|------|---------|
| `_samples` | 74 | `dict[str, list[MetricSample]]` | per-name sample ring, bounded by `window_size` |
| `_stats` | 75 | `dict[str, MetricStats]` | per-name lifetime aggregate (NOT bounded) |
| `_timers` | 77 | `dict[str, float]` | declared + cleared on `reset`, **never written** (ARCH-89) |

Methods:

| method | line | behavior |
|--------|------|----------|
| `record(name, value, tags=None)` | 79 | appends a `MetricSample` to `_samples[name]`, trims `_samples[name]` to the last `window_size` (or `[]` if `window_size <= 0`), then **unconditionally** increments the `_stats[name]` aggregate (count/total/min/max/sum_sq) |
| `timer(name)` | 98 | returns a `TimerContext` for the name |
| `get_stats(name)` | 102 | returns `_stats.get(name)` → `MetricStats \| None` |
| `get_all_stats()` | 106 | returns a shallow copy `dict(self._stats)` |
| `reset()` | 110 | clears `_samples`, `_stats`, and `_timers` |
| `get_recent_samples(name, count=10)` | 116 | returns the last `abs(count)` samples (or all, if `count == 0`) |

### `TimerContext` (class, line 121)

Context manager for timing a block. `__enter__` (line 129) records
`time.time()`; `__exit__` (line 133) computes `elapsed = time.time() - start`
and calls `monitor.record(name, elapsed)` (only if `start` was set). The
`elapsed` property (line 139) returns `0.0` if the timer has not been entered.
`__exit__` swallows no exceptions (returns `None`).

## Contract holes

### ARCH-89 (confirmed contract) — `window_size` bounds `_samples` but NOT `_stats`: `get_stats()` is a lifetime aggregate, not a windowed one

`record` (lines 79-96) applies `window_size` to **only one** of the two
per-name stores. The sample ring is trimmed (lines 84-87):

    if self._window_size <= 0:
        self._samples[name] = []
    elif len(samples) > self._window_size:
        self._samples[name] = samples[-self._window_size :]

but the aggregate is updated **unconditionally, with no window check**
(lines 92-96):

    stats.count += 1
    stats.total += value
    stats.min_val = min(stats.min_val, value)
    stats.max_val = max(stats.max_val, value)
    stats.sum_sq += value * value

So after recording `N > window_size` values for a name, the two public
readers intentionally disagree about "how many values":

- `get_recent_samples(name)` returns the last `window_size` samples
  (bounded), and
- `get_stats(name).count` returns `N` (the **lifetime** count), with
  `mean` / `stddev` / `min_val` / `max_val` / `sum_sq` all computed over all
  `N` values, not the retained window.

**Confirmed contract (no behavior change):** `window_size` bounds **only**
the `_samples` ring; the `_stats` aggregate is a **lifetime** aggregate,
independent of `window_size`. `get_stats()` is therefore NOT a windowed
reader — it is a lifetime count/mean/min/max over every value recorded for
the name, for the life of the monitor. `min_val`/`max_val` in particular can
reflect a value that has already been evicted from `_samples` — the "window"
no longer contains the value that produced the min/max. This is by design:
making `_stats` windowed would change `count`/`mean`/`min`/`max` for every
existing caller, a behavioral change that is out of scope.

**Witness:** the validator deep test
`tests/deep/test_zero_cap_eviction_sweep_adversarial.py` (lines 49-53 for
`window_size=0`, lines 90-94 for `window_size=2`) pins the bounded
`get_recent_samples` length (the guard path); the implementer's pinning test
`tests/test_performance_monitor.py::test_stats_are_lifetime_not_windowed`
pins the lifetime `get_stats().count` side of the same asymmetry.

### Secondary — `_timers` (line 77) is a declared, cleared, but never-written field

`_timers` is initialized to `{}` (line 77) and cleared by `reset()` (line
114), but `grep -n _timers personal_index/performance_monitor.py` returns
exactly **2** hits — the declaration and the clear — with **no write**
anywhere in the module. It is a dead private field (no public reader, no
writer). It is folded into ARCH-89's docs update (document it as unused /
reserved) rather than ticketed separately, since it is a private field with no
public contract surface.
