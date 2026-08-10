"""Tests for content health module."""

from __future__ import annotations

import pytest

from personal_index.content_health import (
    HealthCheckResult,
    HealthChecker,
    HealthReport,
    check_health,
    get_health_report,
)


class TestHealthCheckResult:
    """Tests for HealthCheckResult dataclass."""

    def test_create_result(self):
        r = HealthCheckResult(check_name="test", status="ok", message="All good")
        assert r.check_name == "test"
        assert r.status == "ok"
        assert r.message == "All good"

    def test_to_dict(self):
        r = HealthCheckResult(check_name="test", status="ok", message="Good", details={"key": 1})
        d = r.to_dict()
        assert d["check"] == "test"
        assert d["status"] == "ok"
        assert d["details"]["key"] == 1

    def test_default_details(self):
        r = HealthCheckResult(check_name="test", status="ok")
        assert r.details == {}


class TestHealthReport:
    """Tests for HealthReport dataclass."""

    def test_create_report(self):
        report = HealthReport()
        assert report.overall_status == "ok"
        assert report.timestamp

    def test_overall_ok(self):
        checks = [
            HealthCheckResult(check_name="a", status="ok"),
            HealthCheckResult(check_name="b", status="ok"),
        ]
        report = HealthReport(checks=checks)
        assert report.overall_status == "ok"

    def test_overall_warning(self):
        checks = [
            HealthCheckResult(check_name="a", status="ok"),
            HealthCheckResult(check_name="b", status="warning"),
        ]
        report = HealthReport(checks=checks)
        assert report.overall_status == "warning"

    def test_overall_error(self):
        checks = [
            HealthCheckResult(check_name="a", status="ok"),
            HealthCheckResult(check_name="b", status="error"),
        ]
        report = HealthReport(checks=checks)
        assert report.overall_status == "error"

    def test_to_dict(self):
        checks = [HealthCheckResult(check_name="test", status="ok")]
        report = HealthReport(checks=checks)
        d = report.to_dict()
        assert "timestamp" in d
        assert d["overall_status"] == "ok"
        assert len(d["checks"]) == 1

    def test_summary(self):
        checks = [HealthCheckResult(check_name="test", status="ok", message="Good")]
        report = HealthReport(checks=checks)
        summary = report.summary()
        assert "test" in summary
        assert "Good" in summary


class TestHealthChecker:
    """Tests for HealthChecker class."""

    def setup_method(self):
        self.tmp_dir = None

    def test_check_python_version(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_python_version()
        assert result.check_name == "python_version"
        assert result.status in ("ok", "warning")

    def test_check_data_directory_exists(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_data_directory()
        assert result.status == "ok"

    def test_check_data_directory_missing(self, tmp_path):
        missing = str(tmp_path / "nonexistent")
        checker = HealthChecker(data_dir=missing)
        result = checker.check_data_directory()
        assert result.status == "warning"

    def test_check_disk_space(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_disk_space()
        assert result.check_name == "disk_space"
        assert result.status in ("ok", "warning")

    def test_check_storage_integrity_missing(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_storage_integrity()
        assert result.status == "warning"

    def test_check_storage_integrity_exists(self, tmp_path):
        db_path = tmp_path / "storage.db"
        db_path.write_text("fake db")
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_storage_integrity()
        assert result.status == "ok"

    def test_check_config_file_missing(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_config_file()
        assert result.status == "warning"

    def test_check_config_file_empty(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("")
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_config_file()
        assert result.status == "warning"

    def test_check_config_file_valid(self, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("key: value")
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_config_file()
        assert result.status == "ok"

    def test_check_database_missing(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_database()
        assert result.status == "warning"

    def test_check_database_valid(self, tmp_path):
        import sqlite3
        db_path = tmp_path / "storage.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE test (id INTEGER)")
        conn.close()
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_database()
        assert result.status == "ok"

    def test_check_permissions(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_permissions()
        assert result.status == "ok"

    def test_check_dependencies(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        result = checker.check_dependencies()
        assert result.status == "ok"

    def test_run_all(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        report = checker.run_all()
        assert len(report.checks) == 8
        assert report.overall_status in ("ok", "warning")

    def test_run_all_returns_report(self, tmp_path):
        checker = HealthChecker(data_dir=str(tmp_path))
        report = checker.run_all()
        assert isinstance(report, HealthReport)
        assert report.to_dict()


class TestCheckHealth:
    """Tests for check_health function."""

    def test_check_health_missing_dir(self, tmp_path):
        result = check_health(str(tmp_path / "nonexistent"))
        assert result["status"] in ("healthy", "degraded", "unhealthy")
        assert "score" in result
        assert "last_check" in result

    def test_check_health_returns_dict(self, tmp_path):
        result = check_health(str(tmp_path))
        assert isinstance(result, dict)
        assert "status" in result
        assert "score" in result


class TestGetHealthReport:
    """Tests for get_health_report function."""

    def test_get_health_report_returns_dict(self, tmp_path):
        result = get_health_report(str(tmp_path))
        assert isinstance(result, dict)
        assert "timestamp" in result
        assert "overall_status" in result
        assert "checks" in result

    def test_get_health_report_has_checks(self, tmp_path):
        result = get_health_report(str(tmp_path))
        assert len(result["checks"]) >= 1
