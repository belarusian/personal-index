"""Tests for health report module."""

from __future__ import annotations

import sys
from unittest.mock import patch, MagicMock

import pytest
from personal_index.content_health import (
    HealthCheckResult,
    HealthReport,
)


class TestHealthCheckResult:
    def test_default_values(self):
        r = HealthCheckResult(check_name="test", status="ok")
        assert r.message == ""
        assert r.details == {}

    def test_custom_details(self):
        r = HealthCheckResult(
            check_name="test",
            status="ok",
            message="ok",
            details={"key": "value"},
        )
        assert r.details["key"] == "value"


class TestHealthReport:
    def test_is_healthy_all_healthy(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(check_name="a", status="ok"),
                HealthCheckResult(check_name="b", status="ok"),
            ]
        )
        assert report.overall_status == "ok"

    def test_is_healthy_with_warning(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(check_name="a", status="ok"),
                HealthCheckResult(check_name="b", status="warning"),
            ]
        )
        assert report.overall_status == "warning"

    def test_is_healthy_with_error(self):
        report = HealthReport(
            checks=[
                HealthCheckResult(check_name="a", status="ok"),
                HealthCheckResult(check_name="b", status="error"),
            ]
        )
        assert report.overall_status == "error"

    def test_to_dict(self):
        report = HealthReport(
            timestamp="2024-01-01",
            checks=[HealthCheckResult(check_name="a", status="ok")],
        )
        d = report.to_dict()
        assert d["timestamp"] == "2024-01-01"
        assert d["overall_status"] == "ok"
        assert len(d["checks"]) == 1

    def test_empty_report(self):
        report = HealthReport()
        assert report.overall_status == "ok"
        assert report.checks == []
