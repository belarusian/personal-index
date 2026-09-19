"""Adversarial deep tests for personal_index/performance_monitor.py.

Cycle 288 — first deep-probe of the never-probed module `performance_monitor`
(143 lines: `MetricSample` dataclass, `MetricStats` dataclass with
mean/stddev/p50/p95/p99 properties, `PerformanceMonitor` with record/timer/
get_stats/get_all_stats/reset/get_recent_samples, `TimerContext` context
manager).

Covers the documented contracts:
  - PerformanceMonitor.record: appends sample, updates cumulative stats,
    windowing by window_size.
  - PerformanceMonitor.timer: context manager that records elapsed time.
  - PerformanceMonitor.get_stats: returns MetricStats or None.
  - PerformanceMonitor.get_all_stats: returns dict of all stats.
  - PerformanceMonitor.reset: clears all samples, stats, timers.
  - PerformanceMonitor.get_recent_samples: returns last N samples.
  - MetricStats.mean/stddev/p50/p95/p99: arithmetic properties.
  - TimerContext.elapsed: seconds since start (0.0 if not started).

Plus: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, property checks, and an end-to-end programmatic
run through the public API.
"""

from __future__ import annotations

import time

import pytest

from personal_index.performance_monitor import (
    MetricSample,
    MetricStats,
    PerformanceMonitor,
)


# ---------------------------------------------------------------------------
# MetricSample dataclass

class TestMetricSample:
    def test_basic_construction(self):
        s = MetricSample(name="cpu", value=42.0)
        assert s.name == "cpu"
        assert s.value == 42.0
        assert isinstance(s.timestamp, float)
        assert s.tags == {}

    def test_with_tags(self):
        s = MetricSample(name="mem", value=1.5, tags={"host": "a", "env": "prod"})
        assert s.tags == {"host": "a", "env": "prod"}

    def test_empty_name(self):
        s = MetricSample(name="", value=0.0)
        assert s.name == ""

    def test_unicode_name(self):
        s = MetricSample(name="métric-日本語", value=1.0)
        assert s.name == "métric-日本語"

    def test_negative_value(self):
        s = MetricSample(name="delta", value=-3.14)
        assert s.value == -3.14

    def test_zero_value(self):
        s = MetricSample(name="zero", value=0.0)
        assert s.value == 0.0

    def test_very_large_value(self):
        s = MetricSample(name="big", value=1e18)
        assert s.value == 1e18

    def test_very_small_value(self):
        s = MetricSample(name="tiny", value=1e-18)
        assert s.value == 1e-18

    def test_inf_value(self):
        s = MetricSample(name="inf", value=float("inf"))
        assert s.value == float("inf")

    def test_nan_value(self):
        s = MetricSample(name="nan", value=float("nan"))
        assert s.value != s.value  # NaN != NaN

    def test_tags_isolation(self):
        """Each MetricSample gets its own default tags dict."""
        s1 = MetricSample(name="a", value=1.0)
        s2 = MetricSample(name="b", value=2.0)
        s1.tags["x"] = 1
        assert s2.tags == {}


# ---------------------------------------------------------------------------
# MetricStats dataclass + properties

class TestMetricStats:
    def test_default_construction(self):
        st = MetricStats(name="x")
        assert st.count == 0
        assert st.total == 0.0
        assert st.min_val == float("inf")
        assert st.max_val == float("-inf")
        assert st.sum_sq == 0.0

    def test_mean_zero_count(self):
        st = MetricStats(name="x")
        assert st.mean == 0.0

    def test_stddev_zero_count(self):
        st = MetricStats(name="x")
        assert st.stddev == 0.0

    def test_stddev_one_sample(self):
        st = MetricStats(name="x", count=1, total=5.0, sum_sq=25.0)
        assert st.stddev == 0.0

    def test_stddev_two_identical(self):
        st = MetricStats(name="x", count=2, total=10.0, sum_sq=50.0)
        assert st.stddev == 0.0

    def test_stddev_known_values(self):
        # values: 2, 4, 4, 4, 5, 5, 7, 9 -> mean=5, pop stddev=2
        st = MetricStats(name="x", count=8, total=40.0, sum_sq=232.0)
        assert st.mean == pytest.approx(5.0)
        assert st.stddev == pytest.approx(2.0)

    def test_p50_is_mean(self):
        st = MetricStats(name="x", count=4, total=20.0, sum_sq=100.0)
        assert st.p50 == st.mean

    def test_p95_is_mean_times_1_5(self):
        st = MetricStats(name="x", count=4, total=20.0, sum_sq=100.0)
        assert st.p95 == st.mean * 1.5

    def test_p99_is_mean_times_2(self):
        st = MetricStats(name="x", count=4, total=20.0, sum_sq=100.0)
        assert st.p99 == st.mean * 2.0

    def test_stddev_clamped_non_negative(self):
        """Floating-point can make variance slightly negative; must clamp to 0."""
        # Construct a case where sum_sq/count - mean^2 is tiny negative
        st = MetricStats(name="x", count=2, total=2.0, sum_sq=2.0)
        # mean=1, variance = 2/2 - 1 = 0
        assert st.stddev == 0.0

    def test_mean_with_negative_values(self):
        st = MetricStats(name="x", count=2, total=-10.0, sum_sq=50.0)
        assert st.mean == pytest.approx(-5.0)


# ---------------------------------------------------------------------------
# PerformanceMonitor.record

class TestRecord:
    def test_basic_record(self):
        m = PerformanceMonitor()
        m.record("cpu", 42.0)
        st = m.get_stats("cpu")
        assert st is not None
        assert st.count == 1
        assert st.total == pytest.approx(42.0)
        assert st.min_val == pytest.approx(42.0)
        assert st.max_val == pytest.approx(42.0)

    def test_record_with_tags(self):
        m = PerformanceMonitor()
        m.record("cpu", 1.0, tags={"host": "a"})
        samples = m.get_recent_samples("cpu")
        assert len(samples) == 1
        assert samples[0].tags == {"host": "a"}

    def test_record_none_tags(self):
        m = PerformanceMonitor()
        m.record("cpu", 1.0, tags=None)
        samples = m.get_recent_samples("cpu")
        assert samples[0].tags == {}

    def test_record_empty_name(self):
        m = PerformanceMonitor()
        m.record("", 1.0)
        st = m.get_stats("")
        assert st is not None
        assert st.count == 1

    def test_record_unicode_name(self):
        m = PerformanceMonitor()
        m.record("métric-日本語", 3.14)
        st = m.get_stats("métric-日本語")
        assert st is not None
        assert st.count == 1

    def test_record_multiple_accumulates(self):
        m = PerformanceMonitor()
        for v in [1.0, 2.0, 3.0]:
            m.record("x", v)
        st = m.get_stats("x")
        assert st.count == 3
        assert st.total == pytest.approx(6.0)
        assert st.min_val == pytest.approx(1.0)
        assert st.max_val == pytest.approx(3.0)
        assert st.sum_sq == pytest.approx(14.0)

    def test_record_negative_value(self):
        m = PerformanceMonitor()
        m.record("delta", -5.0)
        st = m.get_stats("delta")
        assert st.min_val == pytest.approx(-5.0)
        assert st.max_val == pytest.approx(-5.0)

    def test_record_zero_value(self):
        m = PerformanceMonitor()
        m.record("z", 0.0)
        st = m.get_stats("z")
        assert st.total == 0.0
        assert st.mean == 0.0

    def test_record_very_large(self):
        m = PerformanceMonitor()
        m.record("big", 1e18)
        st = m.get_stats("big")
        assert st.total == pytest.approx(1e18)

    def test_record_very_small(self):
        m = PerformanceMonitor()
        m.record("tiny", 1e-18)
        st = m.get_stats("tiny")
        assert st.total == pytest.approx(1e-18)

    def test_record_inf_value(self):
        m = PerformanceMonitor()
        m.record("inf", float("inf"))
        st = m.get_stats("inf")
        assert st.max_val == float("inf")
        assert st.mean == float("inf")

    def test_record_nan_value(self):
        m = PerformanceMonitor()
        m.record("nan", float("nan"))
        st = m.get_stats("nan")
        # NaN poisons total; mean is NaN
        assert st.mean != st.mean  # NaN

    def test_record_duplicate_values(self):
        m = PerformanceMonitor()
        for _ in range(100):
            m.record("dup", 5.0)
        st = m.get_stats("dup")
        assert st.count == 100
        assert st.mean == pytest.approx(5.0)
        assert st.stddev == 0.0


# ---------------------------------------------------------------------------
# PerformanceMonitor windowing

class TestWindowing:
    def test_window_size_default_1000(self):
        m = PerformanceMonitor()
        for i in range(1001):
            m.record("x", float(i))
        samples = m.get_recent_samples("x", count=10000)
        assert len(samples) == 1000

    def test_window_size_custom(self):
        m = PerformanceMonitor(window_size=5)
        for i in range(10):
            m.record("x", float(i))
        samples = m.get_recent_samples("x", count=100)
        assert len(samples) == 5
        # Should be the LAST 5: values 5,6,7,8,9
        assert samples[0].value == 5.0
        assert samples[-1].value == 9.0

    def test_window_size_zero_clears_samples(self):
        m = PerformanceMonitor(window_size=0)
        m.record("x", 1.0)
        samples = m.get_recent_samples("x", count=100)
        assert len(samples) == 0
        # But stats still accumulate
        st = m.get_stats("x")
        assert st.count == 1

    def test_window_size_negative_clears_samples(self):
        m = PerformanceMonitor(window_size=-1)
        m.record("x", 1.0)
        samples = m.get_recent_samples("x", count=100)
        assert len(samples) == 0
        st = m.get_stats("x")
        assert st.count == 1

    def test_window_stats_are_cumulative_not_windowed(self):
        """Stats accumulate over ALL records, not just the window."""
        m = PerformanceMonitor(window_size=3)
        for i in range(10):
            m.record("x", float(i))
        st = m.get_stats("x")
        assert st.count == 10  # all 10, not just last 3
        assert st.total == pytest.approx(45.0)


# ---------------------------------------------------------------------------
# PerformanceMonitor.get_stats / get_all_stats

class TestGetStats:
    def test_unknown_metric_returns_none(self):
        m = PerformanceMonitor()
        assert m.get_stats("nonexistent") is None

    def test_get_all_stats_empty(self):
        m = PerformanceMonitor()
        assert m.get_all_stats() == {}

    def test_get_all_stats_multiple(self):
        m = PerformanceMonitor()
        m.record("a", 1.0)
        m.record("b", 2.0)
        m.record("a", 3.0)
        all_st = m.get_all_stats()
        assert set(all_st.keys()) == {"a", "b"}
        assert all_st["a"].count == 2
        assert all_st["b"].count == 1

    def test_get_all_stats_returns_shallow_copy(self):
        """dict is a new dict (key mutations don't propagate), but MetricStats
        objects are shared references (shallow copy)."""
        m = PerformanceMonitor()
        m.record("a", 1.0)
        all_st = m.get_all_stats()
        # Adding a key to the returned dict does NOT affect internal state
        all_st["fake"] = MetricStats(name="fake")
        assert "fake" not in m.get_all_stats()
        # But the MetricStats objects are shared (shallow copy)
        all_st["a"].count = 999
        assert m.get_stats("a").count == 999


# ---------------------------------------------------------------------------
# PerformanceMonitor.reset

class TestReset:
    def test_reset_clears_everything(self):
        m = PerformanceMonitor()
        m.record("a", 1.0)
        m.record("b", 2.0)
        m.reset()
        assert m.get_stats("a") is None
        assert m.get_stats("b") is None
        assert m.get_all_stats() == {}
        assert m.get_recent_samples("a") == []

    def test_reset_idempotent(self):
        m = PerformanceMonitor()
        m.reset()
        m.reset()
        assert m.get_all_stats() == {}

    def test_record_after_reset(self):
        m = PerformanceMonitor()
        m.record("a", 1.0)
        m.reset()
        m.record("a", 2.0)
        st = m.get_stats("a")
        assert st.count == 1
        assert st.total == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# PerformanceMonitor.get_recent_samples

class TestGetRecentSamples:
    def test_unknown_metric_returns_empty(self):
        m = PerformanceMonitor()
        assert m.get_recent_samples("nope") == []

    def test_default_count_10(self):
        m = PerformanceMonitor()
        for i in range(15):
            m.record("x", float(i))
        samples = m.get_recent_samples("x")
        assert len(samples) == 10
        # Last 10: values 5..14
        assert samples[0].value == 5.0
        assert samples[-1].value == 14.0

    def test_count_zero_returns_all(self):
        """count=0 is falsy -> returns all samples (documented behavior)."""
        m = PerformanceMonitor()
        for i in range(5):
            m.record("x", float(i))
        samples = m.get_recent_samples("x", count=0)
        assert len(samples) == 5

    def test_count_negative_uses_abs(self):
        m = PerformanceMonitor()
        for i in range(10):
            m.record("x", float(i))
        samples = m.get_recent_samples("x", count=-3)
        assert len(samples) == 3
        assert samples[0].value == 7.0
        assert samples[-1].value == 9.0

    def test_count_larger_than_samples(self):
        m = PerformanceMonitor()
        for i in range(3):
            m.record("x", float(i))
        samples = m.get_recent_samples("x", count=100)
        assert len(samples) == 3

    def test_count_one(self):
        m = PerformanceMonitor()
        m.record("x", 1.0)
        m.record("x", 2.0)
        samples = m.get_recent_samples("x", count=1)
        assert len(samples) == 1
        assert samples[0].value == 2.0


# ---------------------------------------------------------------------------
# TimerContext

class TestTimerContext:
    def test_basic_timing(self):
        m = PerformanceMonitor()
        with m.timer("op"):
            time.sleep(0.01)
        st = m.get_stats("op")
        assert st is not None
        assert st.count == 1
        assert st.total >= 0.005  # at least 5ms

    def test_elapsed_before_enter(self):
        m = PerformanceMonitor()
        t = m.timer("op")
        assert t.elapsed == 0.0

    def test_elapsed_during_context(self):
        m = PerformanceMonitor()
        t = m.timer("op")
        with t:
            time.sleep(0.01)
            elapsed = t.elapsed
            assert elapsed >= 0.005

    def test_nested_timers_same_name(self):
        m = PerformanceMonitor()
        with m.timer("op"):
            with m.timer("op"):
                time.sleep(0.005)
        st = m.get_stats("op")
        assert st.count == 2

    def test_timer_with_exception(self):
        m = PerformanceMonitor()
        with pytest.raises(ValueError):
            with m.timer("op"):
                raise ValueError("boom")
        # Timer still records elapsed time
        st = m.get_stats("op")
        assert st is not None
        assert st.count == 1

    def test_timer_unicode_name(self):
        m = PerformanceMonitor()
        with m.timer("op-日本語"):
            pass
        st = m.get_stats("op-日本語")
        assert st is not None
        assert st.count == 1

    def test_timer_empty_name(self):
        m = PerformanceMonitor()
        with m.timer(""):
            pass
        st = m.get_stats("")
        assert st is not None
        assert st.count == 1


# ---------------------------------------------------------------------------
# Idempotence / property checks

class TestIdempotenceAndProperties:
    def test_record_is_additive(self):
        """Recording the same value N times: total = value * N."""
        m = PerformanceMonitor()
        for _ in range(50):
            m.record("x", 2.0)
        st = m.get_stats("x")
        assert st.total == pytest.approx(100.0)
        assert st.mean == pytest.approx(2.0)

    def test_stddev_property_invariant(self):
        """stddev >= 0 always (clamped)."""
        m = PerformanceMonitor()
        import random
        random.seed(42)
        for _ in range(100):
            m.record("x", random.gauss(0, 1))
        st = m.get_stats("x")
        assert st.stddev >= 0.0

    def test_min_leq_mean_leq_max(self):
        m = PerformanceMonitor()
        for v in [3.0, 1.0, 4.0, 1.0, 5.0, 9.0, 2.0, 6.0, 5.0, 3.0]:
            m.record("x", v)
        st = m.get_stats("x")
        assert st.min_val <= st.mean <= st.max_val

    def test_sum_sq_geq_total_squared_over_count(self):
        """By Cauchy-Schwarz: sum_sq >= total^2 / count."""
        m = PerformanceMonitor()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            m.record("x", v)
        st = m.get_stats("x")
        assert st.sum_sq >= st.total ** 2 / st.count - 1e-9

    def test_reset_then_record_is_clean(self):
        m = PerformanceMonitor()
        m.record("x", 100.0)
        m.reset()
        m.record("x", 1.0)
        st = m.get_stats("x")
        assert st.count == 1
        assert st.total == pytest.approx(1.0)
        assert st.min_val == pytest.approx(1.0)
        assert st.max_val == pytest.approx(1.0)


# ---------------------------------------------------------------------------
# End-to-end programmatic run (no CLI exists for this module)

class TestEndToEnd:
    def test_full_lifecycle(self):
        """Simulate a realistic monitoring session end-to-end."""
        m = PerformanceMonitor(window_size=100)

        # Record some metrics
        for i in range(20):
            m.record("request_latency", float(i) * 0.1, tags={"endpoint": f"/api/{i}"})

        # Use a timer
        with m.timer("db_query"):
            time.sleep(0.005)

        # Check stats
        lat = m.get_stats("request_latency")
        assert lat is not None
        assert lat.count == 20
        assert lat.min_val == pytest.approx(0.0)
        assert lat.max_val == pytest.approx(1.9)
        assert lat.mean == pytest.approx(0.95)

        db = m.get_stats("db_query")
        assert db is not None
        assert db.count == 1
        assert db.total >= 0.004

        # get_all_stats
        all_st = m.get_all_stats()
        assert "request_latency" in all_st
        assert "db_query" in all_st

        # get_recent_samples
        recent = m.get_recent_samples("request_latency", count=5)
        assert len(recent) == 5
        assert recent[-1].value == pytest.approx(1.9)

        # Reset
        m.reset()
        assert m.get_all_stats() == {}

        # Re-record after reset
        m.record("request_latency", 0.5)
        assert m.get_stats("request_latency").count == 1

    def test_many_metrics(self):
        """Record 1000 distinct metric names."""
        m = PerformanceMonitor()
        for i in range(1000):
            m.record(f"metric_{i}", float(i))
        all_st = m.get_all_stats()
        assert len(all_st) == 1000
        assert all_st["metric_999"].total == pytest.approx(999.0)

    def test_high_frequency_recording(self):
        """Record 10000 samples rapidly; window should cap at 1000."""
        m = PerformanceMonitor(window_size=1000)
        for i in range(10000):
            m.record("hot", float(i))
        samples = m.get_recent_samples("hot", count=10000)
        assert len(samples) == 1000
        # Stats still cumulative
        st = m.get_stats("hot")
        assert st.count == 10000
