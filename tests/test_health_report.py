"""Tests for health report generation."""

import pytest
from personal_index.health_report import (
    HealthReporter, HealthReport, HealthCheckResult, HealthStatus,
)


class TestHealthCheckResult:
    def test_creation(self):
        r = HealthCheckResult(name="disk", status=HealthStatus.HEALTHY, message="OK")
        assert r.name == "disk"
        assert r.status == HealthStatus.HEALTHY

    def test_to_dict(self):
        r = HealthCheckResult(name="cpu", status=HealthStatus.HEALTHY, duration_ms=5.5)
        d = r.to_dict()
        assert d["name"] == "cpu"
        assert d["status"] == "healthy"


class TestHealthReport:
    def test_default_values(self):
        r = HealthReport()
        assert r.overall_status == HealthStatus.HEALTHY
        assert r.check_count == 0

    def test_counts(self):
        r = HealthReport()
        r.checks.append(HealthCheckResult(name="a", status=HealthStatus.HEALTHY))
        r.checks.append(HealthCheckResult(name="b", status=HealthStatus.DEGRADED))
        r.checks.append(HealthCheckResult(name="c", status=HealthStatus.UNHEALTHY))
        assert r.healthy_count == 1
        assert r.degraded_count == 1
        assert r.unhealthy_count == 1

    def test_is_healthy(self):
        r = HealthReport(overall_status=HealthStatus.HEALTHY)
        assert r.is_healthy() is True
        r2 = HealthReport(overall_status=HealthStatus.UNHEALTHY)
        assert r2.is_healthy() is False

    def test_to_dict(self):
        r = HealthReport()
        r.checks.append(HealthCheckResult(name="test", status=HealthStatus.HEALTHY))
        d = r.to_dict()
        assert d["check_count"] == 1
        assert "checks" in d

    def test_to_summary(self):
        r = HealthReport()
        r.checks.append(HealthCheckResult(name="test", status=HealthStatus.HEALTHY, message="OK"))
        summary = r.to_summary()
        assert "HEALTHY" in summary
        assert "test" in summary

    def test_total_duration(self):
        r = HealthReport()
        r.checks.append(HealthCheckResult(name="a", status=HealthStatus.HEALTHY, duration_ms=10.0))
        r.checks.append(HealthCheckResult(name="b", status=HealthStatus.HEALTHY, duration_ms=20.0))
        assert r.total_duration_ms == 30.0


class TestHealthReporter:
    def test_register_check(self):
        reporter = HealthReporter()
        reporter.register_check("test", lambda: (HealthStatus.HEALTHY, "OK"))
        report = reporter.generate_report()
        assert report.check_count == 1

    def test_generate_report_healthy(self):
        reporter = HealthReporter()
        reporter.register_check("check1", lambda: HealthCheckResult(
            name="check1", status=HealthStatus.HEALTHY,
        ))
        report = reporter.generate_report()
        assert report.overall_status == HealthStatus.HEALTHY

    def test_generate_report_unhealthy(self):
        reporter = HealthReporter()
        reporter.register_check("bad", lambda: (HealthStatus.UNHEALTHY, "Failed"))
        report = reporter.generate_report()
        assert report.overall_status == HealthStatus.UNHEALTHY

    def test_generate_report_degraded(self):
        reporter = HealthReporter()
        reporter.register_check("slow", lambda: (HealthStatus.DEGRADED, "Slow"))
        report = reporter.generate_report()
        assert report.overall_status == HealthStatus.DEGRADED

    def test_check_exception(self):
        reporter = HealthReporter()
        reporter.register_check("crash", lambda: 1 / 0)
        report = reporter.generate_report()
        assert report.overall_status == HealthStatus.UNHEALTHY
        assert report.checks[0].status == HealthStatus.UNHEALTHY

    def test_empty_report(self):
        reporter = HealthReporter()
        report = reporter.generate_report()
        assert report.overall_status == HealthStatus.UNKNOWN

    def test_version(self):
        reporter = HealthReporter(version="1.0.0")
        report = reporter.generate_report()
        assert report.version == "1.0.0"
