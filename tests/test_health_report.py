"""Tests for health report module."""

from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock

import pytest
from personal_index.health_report import (
    HealthCheckResult,
    HealthReport,
    HealthReporter,
)


class TestHealthCheckResult:
    def test_default_values(self):
        r = HealthCheckResult(name="test", status="healthy")
        assert r.message == ""
        assert r.details == {}

    def test_custom_details(self):
        r = HealthCheckResult(
            name="test",
            status="healthy",
            message="ok",
            details={"key": "value"},
        )
        assert r.details["key"] == "value"


class TestHealthReport:
    def test_is_healthy_all_healthy(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(name="a", status="healthy"),
                HealthCheckResult(name="b", status="healthy"),
            ]
        )
        assert report.is_healthy is True

    def test_is_healthy_with_degraded(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(name="a", status="healthy"),
                HealthCheckResult(name="b", status="degraded"),
            ]
        )
        assert report.is_healthy is False

    def test_is_healthy_with_unhealthy(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(name="a", status="healthy"),
                HealthCheckResult(name="b", status="unhealthy"),
            ]
        )
        assert report.is_healthy is False

    def test_is_degraded(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(name="a", status="healthy"),
                HealthCheckResult(name="b", status="degraded"),
            ]
        )
        assert report.is_degraded is True

    def test_is_degraded_not_when_unhealthy(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(name="a", status="healthy"),
                HealthCheckResult(name="b", status="unhealthy"),
            ]
        )
        assert report.is_degraded is False

    def test_to_dict(self):
        report = HealthReport(
            timestamp="2024-01-01",
            version="1.0",
            checks=[HealthCheckResult(name="a", status="healthy")],
            summary="1 healthy",
        )
        d = report.to_dict()
        assert d["timestamp"] == "2024-01-01"
        assert d["version"] == "1.0"
        assert d["is_healthy"] is True
        assert len(d["checks"]) == 1

    def test_empty_report(self):
        report = HealthReport()
        assert report.is_healthy is True
        assert report.checks == []


class TestHealthReporter:
    def test_generate_report_returns_report(self):
        reporter = HealthReporter(version="1.0.0")
        report = reporter.generate_report()
        assert isinstance(report, HealthReport)
        assert report.version == "1.0.0"
        assert len(report.checks) >= 5

    def test_generate_report_with_extra_checks(self):
        def custom_check():
            return HealthCheckResult(name="custom", status="healthy", message="ok")

        reporter = HealthReporter()
        report = reporter.generate_report(extra_checks=[custom_check])
        names = [c.name for c in report.checks]
        assert "custom" in names

    def test_generate_report_extra_check_raises(self):
        def bad_check():
            raise ValueError("boom")

        reporter = HealthReporter()
        report = reporter.generate_report(extra_checks=[bad_check])
        bad = [c for c in report.checks if c.name == "bad_check"]
        assert len(bad) == 1
        assert bad[0].status == "unhealthy"
        assert "boom" in bad[0].message

    def test_python_version_check(self):
        reporter = HealthReporter()
        result = reporter._check_python_version()
        assert result.name == "python_version"
        assert result.status in ("healthy", "degraded")

    def test_disk_space_check(self):
        reporter = HealthReporter()
        result = reporter._check_disk_space()
        assert result.name == "disk_space"
        assert "pct_free" in result.details

    def test_timezone_check(self):
        reporter = HealthReporter()
        result = reporter._check_timezone()
        assert result.name == "timezone"
        assert result.status == "healthy"

    def test_writable_home_check(self):
        reporter = HealthReporter()
        result = reporter._check_writable_home()
        assert result.name == "writable_home"
        assert result.status == "healthy"

    def test_memory_check_without_psutil(self):
        reporter = HealthReporter()
        with patch.dict(sys.modules, {"psutil": None}):
            # Force ImportError
            import importlib
            mod = sys.modules.get("psutil")
            if mod is not None:
                del sys.modules["psutil"]
            result = reporter._check_memory()
            assert result.name == "memory"
            assert result.status == "healthy"

    def test_summary_counts(self):
        reporter = HealthReporter()
        report = reporter.generate_report()
        parts = report.summary.split(", ")
        assert len(parts) == 3
