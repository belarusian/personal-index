"""Adversarial deep tests for personal_index.metrics (MetricsCollector + SystemMetrics).

Contract source: personal_index/metrics.py docstrings. These tests pin the
documented behavior against adversarial inputs:

  * SystemMetrics.to_dict - exact key set, 2-decimal rounding of the float
    fields, and that the dataclass defaults (cpu_percent=0.0, etc.) survive.
  * MetricsCollector.increment_counter - accumulation, negative and zero
    increments, and that the counter is created on first use.
  * MetricsCollector.set_gauge - overwrite semantics (last write wins),
    including 0.0 (a falsy value that must still be stored).
  * MetricsCollector.record_histogram - append semantics, empty-name and
    unicode-name keys, and that get_histogram_stats returns None for a
    missing name AND for a name whose list is empty.
  * MetricsCollector.get_histogram_stats - the percentile indexing
    (p50 = sorted[n//2], p95 = sorted[int(n*0.95)], p99 = sorted[int(n*0.99)])
    must never index out of range for any n >= 1, and must be monotonic
    (min <= p50 <= p95 <= p99 <= max) for sorted data.
  * MetricsCollector.collect_system_metrics - the documented guard path:
    a bad target_path leaves disk_* at 0.0 (OSError swallowed), uptime is
    non-negative, cpu_percent stays at the 0.0 default, and the snapshot is
    appended exactly once.
  * MetricsCollector.get_report - exact key set, and that it reflects the
    live counters/gauges/histograms and snapshot count.
  * MetricsCollector.reset - clears all four stores and is idempotent.
  * MetricsCollector(start_time=0) - the falsy 0 falls back to time.time()
    (documented `start_time or time.time()`), so uptime is non-negative.

Plus one end-to-end run through the installed CLI (`python -m personal_index`)
to confirm the package imports and runs cleanly.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time

import pytest

from personal_index.metrics import MetricsCollector, SystemMetrics


# ---------------------------------------------------------------------------
# SystemMetrics.to_dict
# ---------------------------------------------------------------------------
class TestSystemMetricsToDict:
    def test_exact_key_set(self):
        d = SystemMetrics().to_dict()
        assert set(d.keys()) == {
            "timestamp", "cpu_percent", "memory_used_mb", "memory_total_mb",
            "disk_used_mb", "disk_total_mb", "disk_free_mb",
            "python_version", "platform", "pid", "uptime_seconds",
        }

    def test_float_fields_rounded_to_two_decimals(self):
        sm = SystemMetrics(
            memory_used_mb=1.234567,
            memory_total_mb=2.999,
            disk_used_mb=3.14159,
            disk_total_mb=4.0005,
            disk_free_mb=5.5555,
            uptime_seconds=6.999,
        )
        d = sm.to_dict()
        assert d["memory_used_mb"] == 1.23
        assert d["memory_total_mb"] == 3.0
        assert d["disk_used_mb"] == 3.14
        assert d["disk_total_mb"] == 4.0
        assert d["disk_free_mb"] == 5.56
        assert d["uptime_seconds"] == 7.0

    def test_cpu_percent_default_survives(self):
        """cpu_percent is NOT collected; to_dict must carry the 0.0 default."""
        d = SystemMetrics().to_dict()
        assert d["cpu_percent"] == 0.0

    def test_negative_values_rounded(self):
        sm = SystemMetrics(disk_used_mb=-1.005, uptime_seconds=-2.345)
        d = sm.to_dict()
        assert d["disk_used_mb"] == -1.0  # round(-1.005, 2)
        assert d["uptime_seconds"] == -2.35

    def test_to_dict_does_not_mutate_source(self):
        sm = SystemMetrics(memory_used_mb=1.5)
        before = sm.memory_used_mb
        sm.to_dict()
        assert sm.memory_used_mb == before


# ---------------------------------------------------------------------------
# increment_counter
# ---------------------------------------------------------------------------
class TestIncrementCounter:
    def test_accumulates(self):
        mc = MetricsCollector()
        mc.increment_counter("c")
        mc.increment_counter("c")
        mc.increment_counter("c", 5)
        assert mc._counters["c"] == 7

    def test_negative_increment(self):
        mc = MetricsCollector()
        mc.increment_counter("c", 10)
        mc.increment_counter("c", -3)
        assert mc._counters["c"] == 7

    def test_zero_increment_no_change(self):
        mc = MetricsCollector()
        mc.increment_counter("c", 5)
        mc.increment_counter("c", 0)
        assert mc._counters["c"] == 5

    def test_created_on_first_use(self):
        mc = MetricsCollector()
        assert "c" not in mc._counters
        mc.increment_counter("c")
        assert mc._counters["c"] == 1

    def test_empty_and_whitespace_and_unicode_names(self):
        mc = MetricsCollector()
        mc.increment_counter("")
        mc.increment_counter("   ")
        mc.increment_counter("café")
        assert mc._counters[""] == 1
        assert mc._counters["   "] == 1
        assert mc._counters["café"] == 1


# ---------------------------------------------------------------------------
# set_gauge
# ---------------------------------------------------------------------------
class TestSetGauge:
    def test_last_write_wins(self):
        mc = MetricsCollector()
        mc.set_gauge("g", 1.0)
        mc.set_gauge("g", 2.0)
        assert mc._gauges["g"] == 2.0

    def test_zero_value_stored(self):
        """0.0 is falsy but must still be stored (no `or` fallback here)."""
        mc = MetricsCollector()
        mc.set_gauge("g", 5.0)
        mc.set_gauge("g", 0.0)
        assert mc._gauges["g"] == 0.0

    def test_negative_value_stored(self):
        mc = MetricsCollector()
        mc.set_gauge("g", -1.5)
        assert mc._gauges["g"] == -1.5

    def test_empty_and_unicode_names(self):
        mc = MetricsCollector()
        mc.set_gauge("", 1.0)
        mc.set_gauge("héllo", 2.0)
        assert mc._gauges[""] == 1.0
        assert mc._gauges["héllo"] == 2.0


# ---------------------------------------------------------------------------
# record_histogram + get_histogram_stats
# ---------------------------------------------------------------------------
class TestHistogram:
    def test_append_semantics(self):
        mc = MetricsCollector()
        mc.record_histogram("h", 1.0)
        mc.record_histogram("h", 2.0)
        mc.record_histogram("h", 3.0)
        assert mc._histograms["h"] == [1.0, 2.0, 3.0]

    def test_missing_name_returns_none(self):
        mc = MetricsCollector()
        assert mc.get_histogram_stats("nope") is None

    def test_empty_list_returns_none(self):
        mc = MetricsCollector()
        mc.record_histogram("h", 1.0)
        mc._histograms["h"] = []
        assert mc.get_histogram_stats("h") is None

    def test_single_value_all_percentiles_equal(self):
        mc = MetricsCollector()
        mc.record_histogram("h", 42.0)
        s = mc.get_histogram_stats("h")
        assert s["count"] == 1
        assert s["min"] == 42.0
        assert s["max"] == 42.0
        assert s["mean"] == 42.0
        assert s["p50"] == 42.0
        assert s["p95"] == 42.0
        assert s["p99"] == 42.0

    def test_two_values(self):
        mc = MetricsCollector()
        for v in (0.0, 1.0):
            mc.record_histogram("h", v)
        s = mc.get_histogram_stats("h")
        assert s["count"] == 2
        assert s["min"] == 0.0
        assert s["max"] == 1.0
        assert s["mean"] == 0.5
        assert s["p50"] == 1.0  # sorted[2//2] = sorted[1]
        assert s["p95"] == 1.0
        assert s["p99"] == 1.0

    @pytest.mark.parametrize("n", [1, 2, 3, 10, 20, 99, 100, 101, 199, 200,
                                   999, 1000, 1001, 10000])
    def test_percentile_indexing_never_out_of_range(self, n):
        """For any n >= 1, int(n*0.95) and int(n*0.99) must be < n."""
        mc = MetricsCollector()
        for i in range(n):
            mc.record_histogram("h", float(i))
        s = mc.get_histogram_stats("h")
        assert s is not None
        assert s["count"] == n
        # min/max must be the true extremes
        assert s["min"] == 0.0
        assert s["max"] == float(n - 1)
        # percentiles must be actual data values (in [0, n-1])
        assert 0.0 <= s["p50"] <= float(n - 1)
        assert 0.0 <= s["p95"] <= float(n - 1)
        assert 0.0 <= s["p99"] <= float(n - 1)

    def test_percentiles_monotonic_on_sorted_data(self):
        """min <= p50 <= p95 <= p99 <= max for ascending data."""
        mc = MetricsCollector()
        for i in range(1000):
            mc.record_histogram("h", float(i))
        s = mc.get_histogram_stats("h")
        assert s["min"] <= s["p50"] <= s["p95"] <= s["p99"] <= s["max"]

    def test_unsorted_input_sorted_before_stats(self):
        mc = MetricsCollector()
        for v in (5.0, 1.0, 3.0, 2.0, 4.0):
            mc.record_histogram("h", v)
        s = mc.get_histogram_stats("h")
        assert s["min"] == 1.0
        assert s["max"] == 5.0
        assert s["mean"] == 3.0

    def test_negative_values(self):
        mc = MetricsCollector()
        for v in (-10.0, -5.0, 0.0, 5.0, 10.0):
            mc.record_histogram("h", v)
        s = mc.get_histogram_stats("h")
        assert s["min"] == -10.0
        assert s["max"] == 10.0
        assert s["mean"] == 0.0
        assert s["p50"] == 0.0

    def test_empty_and_unicode_names(self):
        mc = MetricsCollector()
        mc.record_histogram("", 1.0)
        mc.record_histogram("héllo", 2.0)
        assert mc.get_histogram_stats("")["count"] == 1
        assert mc.get_histogram_stats("héllo")["count"] == 1


# ---------------------------------------------------------------------------
# collect_system_metrics
# ---------------------------------------------------------------------------
class TestCollectSystemMetrics:
    def test_bad_path_leaves_disk_zero(self):
        """Documented guard: OSError on statvfs -> disk_* stay at 0.0."""
        mc = MetricsCollector()
        m = mc.collect_system_metrics("/nonexistent/path/xyz")
        assert m.disk_total_mb == 0.0
        assert m.disk_free_mb == 0.0
        assert m.disk_used_mb == 0.0

    def test_cpu_percent_stays_default(self):
        """cpu_percent is NOT collected; must remain the 0.0 default."""
        mc = MetricsCollector()
        m = mc.collect_system_metrics("/")
        assert m.cpu_percent == 0.0

    def test_uptime_non_negative(self):
        mc = MetricsCollector()
        m = mc.collect_system_metrics("/")
        assert m.uptime_seconds >= 0.0

    def test_snapshot_appended_exactly_once(self):
        mc = MetricsCollector()
        mc.collect_system_metrics("/")
        assert len(mc._snapshots) == 1
        mc.collect_system_metrics("/")
        assert len(mc._snapshots) == 2

    def test_valid_path_populates_disk(self):
        mc = MetricsCollector()
        m = mc.collect_system_metrics("/")
        # On a normal filesystem the root path should report a positive total.
        assert m.disk_total_mb >= 0.0
        # used + free should reconcile with total (within rounding).
        if m.disk_total_mb > 0:
            assert abs((m.disk_used_mb + m.disk_free_mb) - m.disk_total_mb) < 1.0


# ---------------------------------------------------------------------------
# get_report
# ---------------------------------------------------------------------------
class TestGetReport:
    def test_exact_key_set(self):
        rep = MetricsCollector().get_report()
        assert set(rep.keys()) == {
            "uptime_seconds", "counters", "gauges", "histograms",
            "snapshot_count",
        }

    def test_reflects_live_state(self):
        mc = MetricsCollector(start_time=time.time() - 10)
        mc.increment_counter("x", 2)
        mc.set_gauge("y", 1.5)
        mc.record_histogram("h", 1.0)
        mc.record_histogram("h", 3.0)
        rep = mc.get_report()
        assert rep["counters"] == {"x": 2}
        assert rep["gauges"] == {"y": 1.5}
        assert rep["histograms"]["h"]["count"] == 2
        assert rep["snapshot_count"] == 0

    def test_report_is_a_copy_not_a_view(self):
        """Mutating the returned dict must not affect the collector."""
        mc = MetricsCollector()
        mc.increment_counter("x", 1)
        rep = mc.get_report()
        rep["counters"]["x"] = 999
        assert mc._counters["x"] == 1

    def test_report_after_reset_is_clean(self):
        mc = MetricsCollector()
        mc.increment_counter("a", 1)
        mc.set_gauge("b", 2.0)
        mc.record_histogram("c", 3.0)
        mc.reset()
        rep = mc.get_report()
        assert rep["counters"] == {}
        assert rep["gauges"] == {}
        assert rep["histograms"] == {}
        assert rep["snapshot_count"] == 0


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------
class TestReset:
    def test_clears_all_stores(self):
        mc = MetricsCollector()
        mc.increment_counter("a", 1)
        mc.set_gauge("b", 2.0)
        mc.record_histogram("c", 3.0)
        mc.collect_system_metrics("/")
        mc.reset()
        assert mc._counters == {}
        assert mc._gauges == {}
        assert mc._histograms == {}
        assert mc._snapshots == []

    def test_idempotent(self):
        mc = MetricsCollector()
        mc.increment_counter("a", 1)
        mc.reset()
        mc.reset()
        assert mc._counters == {}
        assert mc._gauges == {}
        assert mc._histograms == {}
        assert mc._snapshots == []


# ---------------------------------------------------------------------------
# start_time handling
# ---------------------------------------------------------------------------
class TestStartTime:
    def test_none_falls_back_to_now(self):
        before = time.time()
        mc = MetricsCollector(start_time=None)
        assert mc._start_time >= before

    def test_zero_falls_back_to_now(self):
        """Documented `start_time or time.time()`: 0 is falsy -> now."""
        before = time.time()
        mc = MetricsCollector(start_time=0)
        assert mc._start_time >= before
        # and uptime must be non-negative, not a huge negative number
        m = mc.collect_system_metrics("/")
        assert m.uptime_seconds >= 0.0

    def test_explicit_start_time_respected(self):
        t0 = time.time() - 100
        mc = MetricsCollector(start_time=t0)
        assert mc._start_time == t0
        m = mc.collect_system_metrics("/")
        assert m.uptime_seconds >= 99.0


# ---------------------------------------------------------------------------
# End-to-end through the installed CLI (package-level smoke: the metrics
# module is not directly exposed on the CLI, so this confirms the package
# imports and runs cleanly via the installed entry point).
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_status_runs_cleanly(self, tmp_path):
        data_dir = str(tmp_path / "data")
        env = dict(os.environ)
        r = subprocess.run(
            [sys.executable, "-m", "personal_index",
             "--data-dir", data_dir, "status"],
            capture_output=True, text=True, env=env,
        )
        assert r.returncode == 0, r.stderr
        assert "Personal Index Status" in r.stdout
        assert "Pages indexed:" in r.stdout
