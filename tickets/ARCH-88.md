# ARCH-88: `SystemMetrics.memory_total_mb` is a public, serialized field that `collect_system_metrics` never populates — and the docstring is silent about it

Status: OPEN
Component: `personal_index/metrics.py` — `SystemMetrics.memory_total_mb` (line 21); the `to_dict()` serialization (line 40); `MetricsCollector.collect_system_metrics` (lines 90-124) and its docstring (lines 91-98)
Umbrella: ARCH-2 (#983)
Issue: #<n>
Docs: `docs/metrics.md` (Contract Hole, ARCH-88)

## Problem
`SystemMetrics` is a `@dataclass` with 11 public fields. `memory_total_mb`
(line 21, `float = 0.0`) is one of them, and `to_dict()` (line 40) serializes
it: `"memory_total_mb": round(self.memory_total_mb, 2)`. But
`collect_system_metrics` (lines 90-124) — the ONLY method that produces a
populated snapshot — **never writes `memory_total_mb`**. It sets exactly:
`uptime_seconds` (line 106, at construction), `memory_used_mb` (line 111, via
`resource.getrusage` → `ru_maxrss / 1024`), and the three `disk_*` fields
(lines 117-119, via `os.statvfs`). `grep -c memory_total_mb
personal_index/metrics.py` returns exactly **2**, both of them the declaration
(line 21) and the `to_dict` serialization (line 40) — there is **no write**
anywhere in the module, and no other module references the field
(`grep -rn memory_total_mb personal_index/ --include='*.py' | grep -v
personal_index/metrics.py` is empty).

So in any snapshot produced by the documented collection path,
`memory_total_mb` is **always `0.0`** — a public, serialized field that is
dead in the production path.

The hole is **compounded by the docstring**. `collect_system_metrics`'s
docstring (lines 91-98) reads:

    Populates exactly these fields on the returned SystemMetrics:
    uptime_seconds (time since collector start), memory_used_mb (via
    resource.getrusage, left at 0.0 if the resource module is unavailable),
    and disk_total_mb / disk_free_mb / disk_used_mb (via os.statvfs on
    target_path, left at 0.0 if statvfs raises OSError). cpu_percent is
    NOT collected and remains at its dataclass default of 0.0.

It enumerates the populated fields and **explicitly flags `cpu_percent` as
"NOT collected and remains at its dataclass default of 0.0"** — but it is
**completely silent about `memory_total_mb`**. A reader who trusts the
"exactly these fields" enumeration has no way to know that `memory_total_mb`
is a serialized-but-never-populated field; the one field that IS flagged
(`cpu_percent`) makes the omission of `memory_total_mb` look like an
oversight rather than a documented guard. This is the same "public field never
populated / docstring omits a field" class as ARCH-86
(`StatsCollector.interest_store` never read, `CrawlStats` never produced) and
ARCH-87 (`UrlFilterRule.is_blacklist` never read).

The hole is **masked by the tests**: `tests/deep/test_metrics_adversarial.py`
pins the `to_dict` key set (line 52) and the 2-decimal rounding of
`memory_total_mb` (lines 60, 68) by constructing `SystemMetrics` **directly**
with `memory_total_mb=2.999` — it never asserts what
`collect_system_metrics` leaves the field at. `tests/test_metrics.py`
(`TestCollectSystemMetricsCpuPinning`, lines 133-143) pins the `cpu_percent`
guard path (`assert metrics.cpu_percent == 0.0`) but **not** the
`memory_total_mb` guard path. So the suite stays green whether or not
`collect_system_metrics` ever sets `memory_total_mb`.

## Public contract (recommended)
Pick **ONE** resolution and state it as the public contract. The recommended
resolution is **(a) keep the field, document it as uncollected, and pin it**
(mirroring the existing `cpu_percent` treatment):

- Keep `memory_total_mb` on `SystemMetrics` (line 21) and in `to_dict()`
  (line 40) — the field is part of the serialized snapshot shape that
  `tests/deep/test_metrics_adversarial.py::test_exact_key_set` (line 52)
  pins, so removing it would break that deep test.
- Amend the `collect_system_metrics` docstring (lines 91-98) to add, alongside
  the existing `cpu_percent` sentence, an explicit statement that
  `memory_total_mb` is **NOT collected** and remains at its dataclass default
  of `0.0` — e.g. "cpu_percent and memory_total_mb are NOT collected and
  remain at their dataclass defaults of 0.0." so the "exactly these fields"
  enumeration is no longer silent about a serialized field.
- All returned values are **exactly as today**: `collect_system_metrics`
  already leaves `memory_total_mb` at `0.0`, so no behavior changes; only the
  docstring gains the missing guard-path statement.

Resolution **(b)** — remove the dead field (`memory_total_mb`) from
`SystemMetrics` and `to_dict()` — is the alternative; it is NOT recommended
because it changes the serialized snapshot key set that the validator-owned
deep test `tests/deep/test_metrics_adversarial.py::test_exact_key_set`
(line 52) and `test_float_fields_rounded_to_two_decimals` (lines 59, 68)
pin, so it would require the VALIDATOR to amend those deep tests (a
`tests/deep/**` change the architect cannot make). If (b) is chosen, the
ticket must restate the exact new field set and the deep-test changes.
**The implementer must not do both.**

## Acceptance criteria
1. After resolution (a): the `collect_system_metrics` docstring explicitly
   states that `memory_total_mb` is NOT collected and remains at its
   dataclass default of `0.0` (alongside the existing `cpu_percent`
   statement) — the "exactly these fields" enumeration is no longer silent
   about a serialized field.
2. `SystemMetrics` still has the `memory_total_mb` field (line 21) and
   `to_dict()` still serializes it (line 40) — the serialized snapshot key
   set is unchanged (the existing `test_exact_key_set` /
   `test_float_fields_rounded_to_two_decimals` deep tests stay green).
3. `collect_system_metrics` returns the **same** values as today for the same
   inputs (all existing `tests/test_metrics.py` and
   `tests/deep/test_metrics_adversarial.py` assertions on returned values
   stay green) — the fix is docstring-only, no behavior change.
4. The `cpu_percent` guard path is still pinned (`assert
   metrics.cpu_percent == 0.0` in `TestCollectSystemMetricsCpuPinning` stays
   green).
5. The `docs/metrics.md` "Contract hole (ARCH-88)" section is updated to
   reflect the resolved contract (field documented as uncollected) in the
   SAME PR.

## Pinning tests to add (tests/test_metrics.py)
- **memory_total_mb guard-path pin (the hole):** in a new test (or extended
  `TestCollectSystemMetricsCpuPinning`), call
  `mc.collect_system_metrics()` and assert
  `metrics.memory_total_mb == 0.0` — pins the corrected docstring claim
  against the actual returned object, not the docstring wording. Include it
  ALONGSIDE the existing `cpu_percent == 0.0` assertion so one returned
  object pins both uncollected-field guard paths.
- **Returned-values-unchanged pin:** the existing `collect_system_metrics`
  value assertions (`uptime_seconds >= 0.0`, `disk_total_mb >= 0.0`,
  `disk_free_mb >= 0.0`, `disk_used_mb >= 0.0`, `process_pid > 0`) stay green
  against the same call — pins that the docstring-only change did not alter
  any populated field.

## Docs (SAME PR)
`docs/metrics.md` (new, spec) + the `metrics.md` index entry in
`docs/README.md` ship in the same PR as this ticket.
