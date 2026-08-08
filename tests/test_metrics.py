"""Tests for system metrics collection."""

import time
import pytest
from personal_index.metrics import MetricsCollector, SystemMetrics


class TestSystemMetrics:
    def test_default_values(self):
        m = SystemMetrics()
        assert m.cpu_percent == 0.0
        assert m.process_pid > 0
        assert m.uptime_seconds == 0.0

    def test_to_dict(self):
        m = SystemMetrics(uptime_seconds=60.5)
        d = m.to_dict()
        assert d["uptime_seconds"] == 60.5
        assert "timestamp" in d
        assert "pid" in d


class TestMetricsCollector:
    def test_increment_counter(self):
        mc = MetricsCollector()
        mc.increment_counter("requests")
        mc.increment_counter("requests")
        assert mc._counters["requests"] == 2

    def test_increment_counter_value(self):
        mc = MetricsCollector()
        mc.increment_counter("bytes", 1024)
        assert mc._counters["bytes"] == 1024

    def test_set_gauge(self):
        mc = MetricsCollector()
        mc.set_gauge("cpu_usage", 45.5)
        assert mc._gauges["cpu_usage"] == 45.5

    def test_record_histogram(self):
        mc = MetricsCollector()
        mc.record_histogram("latency", 0.1)
        mc.record_histogram("latency", 0.2)
        assert len(mc._histograms["latency"]) == 2

    def test_histogram_stats(self):
        mc = MetricsCollector()
        for v in [1.0, 2.0, 3.0, 4.0, 5.0]:
            mc.record_histogram("test", v)
        stats = mc.get_histogram_stats("test")
        assert stats is not None
        assert stats["count"] == 5
        assert stats["min"] == 1.0
        assert stats["max"] == 5.0
        assert stats["mean"] == 3.0

    def test_histogram_stats_empty(self):
        mc = MetricsCollector()
        assert mc.get_histogram_stats("nonexistent") is None

    def test_collect_system_metrics(self):
        mc = MetricsCollector()
        metrics = mc.collect_system_metrics()
        assert metrics.process_pid > 0
        assert metrics.uptime_seconds >= 0

    def test_get_report(self):
        mc = MetricsCollector()
        mc.increment_counter("hits", 5)
        mc.set_gauge("temp", 25.0)
        report = mc.get_report()
        assert report["counters"]["hits"] == 5
        assert report["gauges"]["temp"] == 25.0

    def test_reset(self):
        mc = MetricsCollector()
        mc.increment_counter("test", 1)
        mc.reset()
        assert mc._counters == {}

    def test_uptime(self):
        mc = MetricsCollector()
        time.sleep(0.05)
        report = mc.get_report()
        assert report["uptime_seconds"] >= 0.05

    def test_snapshot_count(self):
        mc = MetricsCollector()
        mc.collect_system_metrics()
        mc.collect_system_metrics()
        report = mc.get_report()
        assert report["snapshot_count"] == 2
