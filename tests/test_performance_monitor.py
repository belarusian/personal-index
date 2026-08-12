"""Tests for the performance monitor module."""

import time

from personal_index.performance_monitor import (
    MetricSample,
    MetricStats,
    PerformanceMonitor,
)


class TestMetricSample:
    def test_creation(self):
        sample = MetricSample(name="test", value=1.5)
        assert sample.name == "test"
        assert sample.value == 1.5
        assert sample.tags == {}


class TestMetricStats:
    def test_default_values(self):
        stats = MetricStats(name="test")
        assert stats.count == 0
        assert stats.mean == 0.0
        assert stats.stddev == 0.0

    def test_mean(self):
        stats = MetricStats(name="test")
        stats.count = 4
        stats.total = 20.0
        assert stats.mean == 5.0

    def test_stddev(self):
        # Values 4 and 6: mean=5, variance=1, stddev=1
        stats = MetricStats(name="test")
        stats.count = 2
        stats.total = 10.0
        stats.sum_sq = 52.0  # 4^2 + 6^2 = 16 + 36 = 52
        assert stats.stddev > 0

    def test_min_max(self):
        stats = MetricStats(name="test")
        stats.min_val = 1.0
        stats.max_val = 10.0
        assert stats.min_val == 1.0
        assert stats.max_val == 10.0


class TestPerformanceMonitor:
    def test_record_metric(self):
        monitor = PerformanceMonitor()
        monitor.record("response_time", 0.5)
        stats = monitor.get_stats("response_time")
        assert stats is not None
        assert stats.count == 1
        assert stats.mean == 0.5

    def test_record_multiple(self):
        monitor = PerformanceMonitor()
        for v in [1.0, 2.0, 3.0]:
            monitor.record("latency", v)
        stats = monitor.get_stats("latency")
        assert stats.count == 3
        assert stats.mean == 2.0
        assert stats.min_val == 1.0
        assert stats.max_val == 3.0

    def test_record_with_tags(self):
        monitor = PerformanceMonitor()
        monitor.record("request", 0.1, tags={"method": "GET"})
        samples = monitor.get_recent_samples("request")
        assert len(samples) == 1
        assert samples[0].tags["method"] == "GET"

    def test_unknown_metric(self):
        monitor = PerformanceMonitor()
        assert monitor.get_stats("nonexistent") is None

    def test_timer_context(self):
        monitor = PerformanceMonitor()
        with monitor.timer("operation"):
            time.sleep(0.01)
        stats = monitor.get_stats("operation")
        assert stats is not None
        assert stats.count == 1
        assert stats.mean >= 0.01

    def test_reset(self):
        monitor = PerformanceMonitor()
        monitor.record("test", 1.0)
        monitor.reset()
        assert monitor.get_stats("test") is None

    def test_window_size(self):
        monitor = PerformanceMonitor(window_size=5)
        for i in range(10):
            monitor.record("val", float(i))
        samples = monitor.get_recent_samples("val")
        assert len(samples) == 5

    def test_get_all_stats(self):
        monitor = PerformanceMonitor()
        monitor.record("a", 1.0)
        monitor.record("b", 2.0)
        all_stats = monitor.get_all_stats()
        assert "a" in all_stats
        assert "b" in all_stats

    def test_stddev_calculation(self):
        monitor = PerformanceMonitor()
        values = [10.0, 20.0, 30.0]
        for v in values:
            monitor.record("data", v)
        stats = monitor.get_stats("data")
        assert stats.stddev > 0
        assert stats.mean == 20.0

    def test_recent_samples_limit(self):
        monitor = PerformanceMonitor()
        for i in range(20):
            monitor.record("seq", float(i))
        samples = monitor.get_recent_samples("seq", count=5)
        assert len(samples) == 5
        assert samples[0].value == 15.0
