# `personal_index.metrics` — spec

System metrics collection and reporting. Two public types, no I/O beyond
`os.statvfs` / `resource.getrusage`, no persistence, no network.

> **Module identity (near-name disambiguation):** this page documents
> `personal_index/metrics.py` — the `SystemMetrics` dataclass + the
> `MetricsCollector` class (counters / gauges / histograms / system
> snapshots). It is **distinct from** `personal_index/stats.py`
> (`docs/stats.md` — `StatsCollector` / `IndexStats` / `CrawlStats`, a
> read-only index aggregate) and from `personal_index/analytics.py`
> (`docs/analytics.md` — `AnalyticsTracker`, an event log). Both test files
> import from this module: `tests/test_metrics.py:5` and
> `tests/deep/test_metrics_adversarial.py:42` do
> `from personal_index.metrics import MetricsCollector, SystemMetrics`.

## Public surface

### `SystemMetrics` (dataclass, line 15)

A snapshot of system metrics. Fields (lines 18-28):

| field | type | default | populated by `collect_system_metrics`? |
|-------|------|---------|----------------------------------------|
| `timestamp` | float | `field(default_factory=time.time)` | no (set at construction) |
| `cpu_percent` | float | `0.0` | **no** — never collected, stays `0.0` |
| `memory_used_mb` | float | `0.0` | yes (via `resource.getrusage`) |
| `memory_total_mb` | float | `0.0` | **no** — never collected, stays `0.0` (ARCH-88) |
| `disk_used_mb` | float | `0.0` | yes (via `os.statvfs`) |
| `disk_total_mb` | float | `0.0` | yes (via `os.statvfs`) |
| `disk_free_mb` | float | `0.0` | yes (via `os.statvfs`) |
| `python_version` | str | `field(default_factory=platform.python_version)` | no (set at construction) |
| `platform_info` | str | `field(default_factory=platform.platform)` | no (set at construction) |
| `process_pid` | int | `field(default_factory=os.getpid)` | no (set at construction) |
| `uptime_seconds` | float | `0.0` | yes (time since collector start) |

`to_dict()` (lines 30-49) serializes all 11 fields to a dict with exactly
these keys: `timestamp`, `cpu_percent`, `memory_used_mb`, `memory_total_mb`,
`disk_used_mb`, `disk_total_mb`, `disk_free_mb`, `python_version`,
`platform` (from `platform_info`), `pid` (from `process_pid`),
`uptime_seconds`. The six float fields (`memory_used_mb`, `memory_total_mb`,
`disk_used_mb`, `disk_total_mb`, `disk_free_mb`, `uptime_seconds`) are
rounded to 2 decimals; `timestamp`, `cpu_percent`, `python_version`,
`platform`, `pid` are passed through unrounded. `to_dict()` is a pure read —
it does not mutate the dataclass (pinned by
`tests/deep/test_metrics_adversarial.py:86-89`).

### `MetricsCollector` (class, line 52)

`__init__(self, start_time: float | None = None)` (line 54): stores
`self._start_time = start_time or time.time()` — a falsy `start_time` (e.g.
`0`) falls back to `time.time()` (pinned by
`tests/deep/test_metrics_adversarial.py`). Initializes four private stores:
`_counters: dict[str, int]`, `_gauges: dict[str, float]`,
`_histograms: dict[str, list[float]]`, `_snapshots: list[SystemMetrics]`.

Methods:

- `increment_counter(name, value=1)` (line 61): `self._counters[name] =
  self._counters.get(name, 0) + value`. Accumulates; creates the counter on
  first use; accepts negative and zero increments (no guard).
- `set_gauge(name, value)` (line 70): `self._gauges[name] = value`. Last
  write wins; stores `0.0` (a falsy value) correctly.
- `record_histogram(name, value)` (line 79): appends `value` to
  `self._histograms[name]`, creating the list on first use. Accepts
  empty-name and unicode-name keys.
- `collect_system_metrics(target_path="/")` (line 90): builds a
  `SystemMetrics(uptime_seconds=time.time() - self._start_time)`, then:
  - `memory_used_mb` — `import resource; usage =
    resource.getrusage(resource.RUSAGE_SELF); metrics.memory_used_mb =
    usage.ru_maxrss / 1024` (lines 108-111). The `except ImportError: pass`
    guard leaves `memory_used_mb` at `0.0` if the `resource` module is
    unavailable (Windows). **Note:** `ru_maxrss` is in kilobytes on Linux
    but **bytes** on macOS, so the `/ 1024` (the "Convert KB to MB on
    macOS" comment at line 111) is correct on Linux and off by a factor of
    1024 on macOS — `memory_used_mb` is platform-dependent.
  - `disk_total_mb` / `disk_free_mb` / `disk_used_mb` — `stat =
    os.statvfs(target_path)`; `disk_total_mb = (stat.f_blocks *
    stat.f_frsize) / (1024*1024)`, `disk_free_mb = (stat.f_bfree *
    stat.f_frsize) / (1024*1024)`, `disk_used_mb = disk_total_mb -
    disk_free_mb` (lines 114-119). The `except OSError: pass` guard leaves
    all three at `0.0` if `statvfs` raises (bad `target_path`).
  - `cpu_percent` is **NOT collected** and remains at its dataclass default
    of `0.0`.
  - `memory_total_mb` is **NOT collected** and remains at its dataclass
    default of `0.0` (ARCH-88 — see Contract hole below).
  - Appends the snapshot to `self._snapshots` (exactly once per call) and
    returns it.
- `get_histogram_stats(name)` (line 126): returns `None` for a missing name
  **and** for a name whose list is empty (`if not values: return None`).
  Otherwise returns `{"count", "min", "max", "mean", "p50", "p95", "p99"}`
  where `p50 = sorted[n//2]`, `p95 = sorted[int(n*0.95)] if n > 1 else
  sorted[0]`, `p99 = sorted[int(n*0.99)] if n > 1 else sorted[0]`. The
  percentile indexing never indexes out of range for any `n >= 1` and is
  monotonic (`min <= p50 <= p95 <= p99 <= max`) for sorted data (pinned by
  `tests/deep/test_metrics_adversarial.py`).
- `get_report()` (line 150): returns `{"uptime_seconds" (rounded 2),
  "counters" (copy), "gauges" (copy), "histograms" (name -> stats dict),
  "snapshot_count"}`. Reflects the live stores.
- `reset()` (line 164): clears all four stores (`_counters`, `_gauges`,
  `_histograms`, `_snapshots`). Idempotent.

## Contract hole (ARCH-88)

`SystemMetrics.memory_total_mb` (line 21) is a public field that is
**serialized** by `to_dict()` (line 40) but **never populated** by
`collect_system_metrics` (lines 90-124). The method's docstring (lines 91-98)
states "Populates exactly these fields on the returned SystemMetrics:" and
lists `uptime_seconds`, `memory_used_mb`, and the three `disk_*` fields, then
explicitly calls out that `cpu_percent` "is NOT collected and remains at its
dataclass default of 0.0" — but it is **silent about `memory_total_mb`**.
The field is therefore a public, serialized field that is always `0.0` in any
snapshot produced by the documented collection path, and the docstring's
"exactly these fields" enumeration neither lists it nor flags it as
uncollected. This is the same "public field never populated / docstring
omits a field" class as ARCH-86 (`StatsCollector.interest_store` /
`CrawlStats`) and ARCH-87 (`UrlFilterRule.is_blacklist`).

The hole is **masked by the tests**: `tests/deep/test_metrics_adversarial.py`
pins the `to_dict` key set (line 52) and the 2-decimal rounding of
`memory_total_mb` (lines 60, 68) by constructing `SystemMetrics` directly
with `memory_total_mb=2.999` — it never asserts what
`collect_system_metrics` leaves the field at. `tests/test_metrics.py`
(`TestCollectSystemMetricsCpuPinning`, lines 133-143) pins the `cpu_percent`
guard path but not the `memory_total_mb` guard path. So the suite stays green
whether or not `collect_system_metrics` ever sets `memory_total_mb`.

See `tickets/ARCH-88.md` for the contract, acceptance criteria, and pinning
tests.
