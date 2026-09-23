# ARCH-89: `PerformanceMonitor.record` applies `window_size` to `_samples` but NOT `_stats` — `get_stats()` is a silent lifetime aggregate, not a windowed one

Status: RESOLVED (confirmed Option a — keep the lifetime aggregate, document it, no behavior change; architect, cycle 294) (implementer cycle 362: pinning witness test_stats_are_lifetime_not_windowed added to tests/test_performance_monitor.py — implementer path, no code change, no docs/** or tests/deep/** touched; IMPLEMENTED #1816@70171992)
Component: `personal_index/performance_monitor.py` — `PerformanceMonitor.record` (lines 79-96); the sample-ring trim (lines 84-87) vs the unconditional aggregate update (lines 92-96); `PerformanceMonitor.__init__` `window_size` param (line 73); `get_stats` (line 102) / `get_recent_samples` (line 116)
Umbrella: ARCH-2 (#983)
Issue: #1467
Docs: `docs/performance-monitor.md` (Contract Hole, ARCH-89)

## Problem
`PerformanceMonitor.__init__(self, window_size: int = 1000)` (line 73) takes a
parameter named `window_size`, which reads as "the monitor keeps a bounded
window of samples". `record` (lines 79-96) honors that name for **only one**
of the two per-name stores it maintains.

The sample ring IS bounded (lines 84-87):

    if self._window_size <= 0:
        self._samples[name] = []
    elif len(samples) > self._window_size:
        self._samples[name] = samples[-self._window_size :]

But the aggregate is updated **unconditionally, with no window check at all**
(lines 92-96):

    stats.count += 1
    stats.total += value
    stats.min_val = min(stats.min_val, value)
    stats.max_val = max(stats.max_val, value)
    stats.sum_sq += value * value

So after recording `N > window_size` values for a name, the two public readers
disagree about "how many values exist":

- `get_recent_samples(name)` (line 116) returns the last `window_size`
  samples — bounded.
- `get_stats(name)` (line 102) returns a `MetricStats` whose `count == N`
  (the **lifetime** count), and whose `mean` / `stddev` / `min_val` /
  `max_val` / `sum_sq` are all computed over all `N` values, not the retained
  window.

This is an **asymmetric, undocumented** behavior. The parameter is named
`window_size` (implying a bounded window), yet the aggregate silently grows
without bound for the life of the monitor. `min_val`/`max_val` in particular
can reflect a value that has already been evicted from `_samples` — the
"window" no longer contains the value that produced the min/max.

Evidence (one-line proof the aggregate is unbounded):

    grep -n 'window_size\|stats\.' personal_index/performance_monitor.py

shows the `window_size` guard (lines 84-87) sits in the `_samples` block only;
the `stats.*` updates (lines 92-96) have no `window_size` reference anywhere
between them and the method end. `grep -c window_size personal_index/
performance_monitor.py` returns **3** (the `__init__` param line 73, the
`<= 0` guard line 84, the `> self._window_size` guard line 86) — all three in
the sample-ring path, none in the aggregate path.

The asymmetry is **untested**. The existing `test_window_size`
(`tests/test_performance_monitor.py:96`) records 10 values with
`window_size=5` and asserts **only** `len(samples) == 5` — it never asserts on
`get_stats().count`. The validator deep test
`tests/deep/test_zero_cap_eviction_sweep_adversarial.py` (lines 49-53 for
`window_size=0`, lines 90-94 for `window_size=2`) likewise pins only
`get_recent_samples` length, never the stats count. So nothing witnesses that
`get_stats().count` keeps growing past the window.

## Public contract (what the implementer must preserve / document)
- `record(name, value, tags=None)` (line 79): appends one `MetricSample` to
  `_samples[name]`; trims `_samples[name]` to the last `window_size` (or `[]`
  if `window_size <= 0`); then increments the `_stats[name]` aggregate
  (count/total/min_val/max_val/sum_sq) **unconditionally**.
- `get_recent_samples(name, count=10)` (line 116): returns the last
  `abs(count)` samples, or all if `count == 0`. Bounded by `window_size`.
- `get_stats(name)` (line 102): returns the **lifetime** `MetricStats`
  aggregate (count/total/min_val/max_val/sum_sq + derived mean/stddev/p50/
  p95/p99), independent of `window_size`.
- Guard inputs: `window_size <= 0` → sample ring always `[]` but stats still
  accumulate; `count == 0` in `get_recent_samples` → all samples; unknown name
  in `get_stats` → `None`.

## Acceptance criteria
1. `docs/performance-monitor.md` states, in the `PerformanceMonitor` section,
   that `_stats` is a **lifetime** aggregate independent of `window_size`
   (which bounds only `_samples`), and that `min_val`/`max_val` may reflect
   values already evicted from the sample ring. (Already drafted in this PR —
   the implementer ships the same docs page in the SAME PR.)
2. A pinning test is added (see below) that witnesses the asymmetry.
3. No behavior change: `record` / `get_stats` / `get_recent_samples` keep
   their current semantics. The fix is docs + a pinning test, NOT a code
   change.

## Pinning tests to add (implementer owns tests/**)
Add ONE test to `tests/test_performance_monitor.py` (the implementer's path —
the architect does not write tests/**). It must record `N > window_size`
values and assert BOTH sides of the asymmetry in one returned object:

    def test_stats_are_lifetime_not_windowed(self):
        monitor = PerformanceMonitor(window_size=3)
        for i in range(10):
            monitor.record("m", float(i))
        # sample ring is bounded by window_size
        assert len(monitor.get_recent_samples("m")) == 3
        # ...but the aggregate is a LIFETIME count over all 10 values
        stats = monitor.get_stats("m")
        assert stats.count == 10
        assert stats.min_val == 0.0   # value 0 was evicted from the ring
        assert stats.max_val == 9.0
        assert stats.mean == 4.5      # (0+...+9)/10, not the window mean

This single test pins both the bounded sample ring (the guard path the deep
test already covers) AND the unbounded lifetime aggregate (the new contract),
so the asymmetry is witnessed as a documented contract rather than a surprise.
It does NOT contradict the validator deep test
`tests/deep/test_zero_cap_eviction_sweep_adversarial.py`, which pins only
`get_recent_samples` length (never `get_stats().count`).

## Docs update (SAME PR)
`docs/performance-monitor.md` is authored in this PR (the architect's page).
The implementer's PR must ship the same page unchanged (or with the
`_timers` note if they choose to remove the dead field — see below).

## Secondary (folded in, not separately ticketed)
`_timers` (line 77) is declared `{}` and cleared by `reset()` (line 114) but
**never written** — `grep -n _timers personal_index/performance_monitor.py`
returns exactly 2 hits (declaration + clear), no write. It is a dead private
field with no public contract surface, so it is documented as unused/reserved
in the page rather than ticketed. If the implementer prefers to remove it,
that is a private-field cleanup (no public contract change) and is acceptable
as long as `reset()` still clears `_samples` and `_stats`.

## Design decision (architect, cycle 294)
**Chosen resolution: Option (a) — keep the lifetime aggregate, document it,
no behavior change.** `window_size` bounds **only** the `_samples` ring;
`_stats` stays a **lifetime** aggregate independent of `window_size`, and
`get_stats()` stays a lifetime count/mean/min/max over every recorded value
for the name. `min_val`/`max_val` may reflect values already evicted from the
sample ring — by design. All returned values are **exactly as today**: the fix
is docs-only, no behavior change.

Option (b) — make `_stats` windowed — is **rejected**: it changes
`count`/`mean`/`min`/`max` for every existing caller (a behavioral change the
implementer must not make silently) and would require the VALIDATOR to amend
the deep tests that pin the current aggregate.

`docs/performance-monitor.md` (the ARCH-89 section restated as the confirmed
contract, with the pinning tests named as the witness) and the
`performance-monitor.md` index line in `docs/README.md` are reconciled in the
SAME PR. The pinning witness is
`tests/test_performance_monitor.py::test_stats_are_lifetime_not_windowed`
(implementer-owned, `tests/**` — the architect does not write tests/**), which
records `N > window_size` values and asserts BOTH `len(get_recent_samples())
== window_size` AND `get_stats().count == N` (with `min_val`/`max_val` over
the full N) on the same returned object; it does not contradict the validator
deep test `tests/deep/test_zero_cap_eviction_sweep_adversarial.py`, which pins
only `get_recent_samples` length. Status is **RESOLVED** for the implementer.
