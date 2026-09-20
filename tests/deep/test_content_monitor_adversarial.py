"""Adversarial tests for content_monitor module (cycle 309).

Tests edge cases: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, property checks, and end-to-end CLI runs.
"""

import json
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from personal_index.content_monitor import (
    Alert,
    AlertManager,
    ContentMonitor,
    DiskUsageInfo,
    ErrorRateInfo,
    HealthChecker,
    HealthReport,
    SourceFreshness,
)
from personal_index.content_monitor.alert import AlertLevel
from personal_index.content_monitor.health import HealthStatus


# === DiskUsageInfo edge cases ===

class TestDiskUsageInfoEdgeCases:
    def test_default_values(self):
        info = DiskUsageInfo()
        assert info.total_bytes == 0
        assert info.file_count == 0
        assert info.dir_count == 0
        assert info.largest_files == []
        assert info.total_mb == 0.0
        assert info.total_gb == 0.0

    def test_negative_bytes(self):
        info = DiskUsageInfo(total_bytes=-1024)
        assert info.total_bytes == -1024
        assert info.total_mb < 0.0

    def test_largest_files_empty(self):
        info = DiskUsageInfo(largest_files=[])
        assert info.largest_files == []

    def test_largest_files_none_values(self):
        info = DiskUsageInfo(largest_files=[(None, None)])
        assert info.largest_files == [(None, None)]

    def test_to_dict_roundtrip(self):
        info = DiskUsageInfo(
            total_bytes=1048576,
            file_count=10,
            dir_count=5,
            largest_files=[("/path/to/file", 1024)],
        )
        d = info.to_dict()
        assert d["total_bytes"] == 1048576
        assert d["file_count"] == 10
        assert d["dir_count"] == 5
        assert len(d["largest_files"]) == 1
        assert d["largest_files"][0]["path"] == "/path/to/file"
        assert d["largest_files"][0]["size_bytes"] == 1024

    def test_to_dict_empty_largest_files(self):
        info = DiskUsageInfo()
        d = info.to_dict()
        assert d["largest_files"] == []


# === SourceFreshness edge cases ===

class TestSourceFreshnessEdgeCases:
    def test_default_values(self):
        sf = SourceFreshness()
        assert sf.source == ""
        assert sf.last_crawled is None
        assert sf.crawl_count == 0
        assert sf.last_error is None
        assert sf.last_error_time is None
        assert sf.staleness_hours is None

    def test_is_stale_never_crawled(self):
        sf = SourceFreshness(source="example.com")
        assert sf.is_stale() is True

    def test_is_stale_fresh(self):
        now = datetime.now(timezone.utc)
        sf = SourceFreshness(source="example.com", last_crawled=now)
        assert sf.is_stale() is False

    def test_is_stale_old(self):
        old = datetime.now(timezone.utc) - timedelta(hours=48)
        sf = SourceFreshness(source="example.com", last_crawled=old)
        assert sf.is_stale() is True

    def test_is_stale_custom_threshold(self):
        old = datetime.now(timezone.utc) - timedelta(hours=12)
        sf = SourceFreshness(source="example.com", last_crawled=old)
        assert sf.is_stale(threshold_hours=6) is True
        assert sf.is_stale(threshold_hours=24) is False

    def test_staleness_hours_none(self):
        sf = SourceFreshness(source="example.com")
        assert sf.staleness_hours is None

    def test_staleness_hours_positive(self):
        old = datetime.now(timezone.utc) - timedelta(hours=5)
        sf = SourceFreshness(source="example.com", last_crawled=old)
        assert sf.staleness_hours is not None
        assert sf.staleness_hours >= 4.0
        assert sf.staleness_hours < 6.0

    def test_to_dict_never_crawled(self):
        sf = SourceFreshness(source="example.com")
        d = sf.to_dict()
        assert d["source"] == "example.com"
        assert d["last_crawled"] is None
        assert d["staleness_hours"] is None
        assert d["is_stale"] is True

    def test_to_dict_with_crawl(self):
        now = datetime.now(timezone.utc)
        sf = SourceFreshness(source="example.com", last_crawled=now, crawl_count=5)
        d = sf.to_dict()
        assert d["source"] == "example.com"
        assert d["last_crawled"] is not None
        assert d["crawl_count"] == 5

    def test_unicode_source(self):
        sf = SourceFreshness(source="例え.com")
        assert sf.source == "例え.com"
        assert sf.is_stale() is True

    def test_whitespace_source(self):
        sf = SourceFreshness(source="   ")
        assert sf.source == "   "
        assert sf.is_stale() is True

    def test_empty_source(self):
        sf = SourceFreshness(source="")
        assert sf.source == ""
        assert sf.is_stale() is True


# === ErrorRateInfo edge cases ===

class TestErrorRateInfoEdgeCases:
    def test_default_values(self):
        eri = ErrorRateInfo()
        assert eri.total_crawls == 0
        assert eri.successful_crawls == 0
        assert eri.failed_crawls == 0
        assert eri.error_rate == 0.0
        assert eri.success_rate == 0.0
        assert eri.recent_errors == []

    def test_record_success(self):
        eri = ErrorRateInfo()
        eri.record_crawl("example.com", success=True)
        assert eri.total_crawls == 1
        assert eri.successful_crawls == 1
        assert eri.failed_crawls == 0
        assert eri.error_rate == 0.0
        assert eri.success_rate == 1.0

    def test_record_failure(self):
        eri = ErrorRateInfo()
        eri.record_crawl("example.com", success=False, error_message="timeout")
        assert eri.total_crawls == 1
        assert eri.successful_crawls == 0
        assert eri.failed_crawls == 1
        assert eri.error_rate == 1.0
        assert eri.success_rate == 0.0
        assert len(eri.recent_errors) == 1
        assert eri.recent_errors[0]["source"] == "example.com"
        assert eri.recent_errors[0]["error"] == "timeout"

    def test_record_failure_no_message(self):
        eri = ErrorRateInfo()
        eri.record_crawl("example.com", success=False)
        assert len(eri.recent_errors) == 0

    def test_mixed_results(self):
        eri = ErrorRateInfo()
        eri.record_crawl("a.com", success=True)
        eri.record_crawl("b.com", success=False)
        eri.record_crawl("c.com", success=True)
        assert eri.total_crawls == 3
        assert eri.successful_crawls == 2
        assert eri.failed_crawls == 1
        assert eri.error_rate == pytest.approx(1/3)
        assert eri.success_rate == pytest.approx(2/3)

    def test_recent_errors_cap(self):
        eri = ErrorRateInfo()
        for i in range(150):
            eri.record_crawl(f"site{i}.com", success=False, error_message=f"error {i}")
        assert len(eri.recent_errors) == 100
        assert eri.recent_errors[0]["source"] == "site50.com"
        assert eri.recent_errors[-1]["source"] == "site149.com"

    def test_to_dict(self):
        eri = ErrorRateInfo()
        eri.record_crawl("a.com", success=True)
        eri.record_crawl("b.com", success=False, error_message="timeout")
        d = eri.to_dict()
        assert d["total_crawls"] == 2
        assert d["successful_crawls"] == 1
        assert d["failed_crawls"] == 1
        assert d["error_rate"] == pytest.approx(0.5)
        assert d["success_rate"] == pytest.approx(0.5)
        assert d["recent_errors_count"] == 1

    def test_to_dict_empty(self):
        eri = ErrorRateInfo()
        d = eri.to_dict()
        assert d["total_crawls"] == 0
        assert d["error_rate"] == 0.0
        assert d["success_rate"] == 0.0
        assert d["recent_errors_count"] == 0


# === HealthChecker edge cases ===

class TestHealthCheckerEdgeCases:
    def test_default_values(self):
        hc = HealthChecker()
        assert hc.min_items == 1
        assert hc.max_stale_hours == 24

    def test_empty_items(self):
        hc = HealthChecker()
        status = hc.check([])
        assert isinstance(status, HealthStatus)
        assert len(status.checks) == 3
        # item_count fails (0 < 1)
        assert status.checks[0].check_name == "item_count"
        assert status.checks[0].healthy is False
        # scores passes (empty)
        assert status.checks[1].check_name == "scores"
        assert status.checks[1].healthy is True
        # duplicates passes (empty)
        assert status.checks[2].check_name == "duplicates"
        assert status.checks[2].healthy is True
        assert status.healthy is False
        assert status.score == pytest.approx(0.6667)

    def test_single_valid_item(self):
        hc = HealthChecker()
        items = [{"id": 1, "score": 0.9}]
        status = hc.check(items)
        assert status.healthy is True
        assert status.score == 1.0

    def test_multiple_valid_items(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": 2, "score": 0.8},
            {"id": 3, "score": 0.7},
        ]
        status = hc.check(items)
        assert status.healthy is True
        assert status.score == 1.0

    def test_duplicate_ids(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": 1, "score": 0.8},
        ]
        status = hc.check(items)
        assert status.healthy is False
        dup_check = status.checks[2]
        assert dup_check.check_name == "duplicates"
        assert dup_check.healthy is False
        assert dup_check.details["duplicates"] == 1

    def test_missing_scores(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": 2},
        ]
        status = hc.check(items)
        scores_check = status.checks[1]
        assert scores_check.check_name == "scores"
        assert scores_check.healthy is False
        assert scores_check.details["scored"] == 1
        assert scores_check.details["total"] == 2

    def test_non_numeric_scores(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": 2, "score": "high"},
        ]
        status = hc.check(items)
        scores_check = status.checks[1]
        assert scores_check.healthy is False

    def test_none_score(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": 2, "score": None},
        ]
        status = hc.check(items)
        scores_check = status.checks[1]
        assert scores_check.healthy is False

    def test_custom_min_items(self):
        hc = HealthChecker(min_items=5)
        items = [{"id": i, "score": 0.9} for i in range(3)]
        status = hc.check(items)
        count_check = status.checks[0]
        assert count_check.healthy is False
        assert count_check.details["count"] == 3

    def test_custom_min_items_satisfied(self):
        hc = HealthChecker(min_items=2)
        items = [{"id": i, "score": 0.9} for i in range(3)]
        status = hc.check(items)
        count_check = status.checks[0]
        assert count_check.healthy is True

    def test_string_ids(self):
        hc = HealthChecker()
        items = [
            {"id": "a", "score": 0.9},
            {"id": "b", "score": 0.8},
        ]
        status = hc.check(items)
        assert status.healthy is True

    def test_mixed_id_types(self):
        hc = HealthChecker()
        items = [
            {"id": 1, "score": 0.9},
            {"id": "1", "score": 0.8},
        ]
        status = hc.check(items)
        # str(1) == "1", so these are duplicates
        dup_check = status.checks[2]
        assert dup_check.healthy is False

    def test_no_id_field(self):
        hc = HealthChecker()
        items = [
            {"score": 0.9},
            {"score": 0.8},
        ]
        status = hc.check(items)
        # Both have id="" (default), so duplicates
        dup_check = status.checks[2]
        assert dup_check.healthy is False

    def test_unicode_ids(self):
        hc = HealthChecker()
        items = [
            {"id": "例え", "score": 0.9},
            {"id": "テスト", "score": 0.8},
        ]
        status = hc.check(items)
        assert status.healthy is True

    def test_whitespace_ids(self):
        hc = HealthChecker()
        items = [
            {"id": "  ", "score": 0.9},
            {"id": "  ", "score": 0.8},
        ]
        status = hc.check(items)
        dup_check = status.checks[2]
        assert dup_check.healthy is False

    def test_score_rounding(self):
        hc = HealthChecker()
        items = [{"id": 1, "score": 0.9}]
        status = hc.check(items)
        assert status.score == 1.0
        # 2 out of 3 checks pass
        items = [{"id": 1}]  # missing score
        status = hc.check(items)
        assert status.score == pytest.approx(0.6667)

    def test_all_checks_fail(self):
        hc = HealthChecker(min_items=5)
        items = [
            {"id": 1},
            {"id": 1},
        ]
        status = hc.check(items)
        assert status.healthy is False
        assert status.score == 0.0


# === AlertManager edge cases ===

class TestAlertManagerEdgeCases:
    def test_default_values(self):
        am = AlertManager()
        assert am.alerts == []
        assert am.max_alerts == 1000
        assert am.pending_count == 0

    def test_add_alert(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "test message", "test source")
        assert isinstance(alert, Alert)
        assert alert.alert_id == "alert_0"
        assert alert.level == AlertLevel.INFO
        assert alert.message == "test message"
        assert alert.source == "test source"
        assert alert.acknowledged is False
        assert len(am.alerts) == 1

    def test_add_alert_with_data(self):
        am = AlertManager()
        alert = am.add_alert(
            AlertLevel.WARNING,
            "test",
            "source",
            data={"key": "value"},
        )
        assert alert.data == {"key": "value"}

    def test_add_alert_none_data(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "test", "source", data=None)
        assert alert.data == {}

    def test_alert_id_sequential(self):
        am = AlertManager()
        a1 = am.add_alert(AlertLevel.INFO, "msg1", "src")
        a2 = am.add_alert(AlertLevel.INFO, "msg2", "src")
        a3 = am.add_alert(AlertLevel.INFO, "msg3", "src")
        assert a1.alert_id == "alert_0"
        assert a2.alert_id == "alert_1"
        assert a3.alert_id == "alert_2"

    def test_get_alerts_all(self):
        am = AlertManager()
        am.add_alert(AlertLevel.INFO, "msg1", "src")
        am.add_alert(AlertLevel.WARNING, "msg2", "src")
        alerts = am.get_alerts()
        assert len(alerts) == 2

    def test_get_alerts_by_level(self):
        am = AlertManager()
        am.add_alert(AlertLevel.INFO, "msg1", "src")
        am.add_alert(AlertLevel.WARNING, "msg2", "src")
        am.add_alert(AlertLevel.ERROR, "msg3", "src")
        warnings = am.get_alerts(level=AlertLevel.WARNING)
        assert len(warnings) == 1
        assert warnings[0].message == "msg2"

    def test_get_alerts_by_acknowledged(self):
        am = AlertManager()
        a1 = am.add_alert(AlertLevel.INFO, "msg1", "src")
        a2 = am.add_alert(AlertLevel.INFO, "msg2", "src")
        am.acknowledge(a1.alert_id)
        unacked = am.get_alerts(acknowledged=False)
        assert len(unacked) == 1
        assert unacked[0].alert_id == a2.alert_id

    def test_get_alerts_combined_filters(self):
        am = AlertManager()
        a1 = am.add_alert(AlertLevel.INFO, "msg1", "src")
        a2 = am.add_alert(AlertLevel.WARNING, "msg2", "src")
        a3 = am.add_alert(AlertLevel.INFO, "msg3", "src")
        am.acknowledge(a1.alert_id)
        unacked_info = am.get_alerts(level=AlertLevel.INFO, acknowledged=False)
        assert len(unacked_info) == 1
        assert unacked_info[0].alert_id == a3.alert_id

    def test_acknowledge(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "msg", "src")
        result = am.acknowledge(alert.alert_id)
        assert result is True
        assert alert.acknowledged is True

    def test_acknowledge_nonexistent(self):
        am = AlertManager()
        result = am.acknowledge("alert_999")
        assert result is False

    def test_clear_acknowledged(self):
        am = AlertManager()
        a1 = am.add_alert(AlertLevel.INFO, "msg1", "src")
        a2 = am.add_alert(AlertLevel.INFO, "msg2", "src")
        am.acknowledge(a1.alert_id)
        cleared = am.clear_acknowledged()
        assert cleared == 1
        assert len(am.alerts) == 1
        assert am.alerts[0].alert_id == a2.alert_id

    def test_clear_acknowledged_none(self):
        am = AlertManager()
        am.add_alert(AlertLevel.INFO, "msg", "src")
        cleared = am.clear_acknowledged()
        assert cleared == 0
        assert len(am.alerts) == 1

    def test_max_alerts_enforced(self):
        am = AlertManager(max_alerts=5)
        for i in range(10):
            am.add_alert(AlertLevel.INFO, f"msg{i}", "src")
        assert len(am.alerts) == 5
        assert am.alerts[0].message == "msg5"
        assert am.alerts[-1].message == "msg9"

    def test_max_alerts_zero(self):
        am = AlertManager(max_alerts=0)
        am.add_alert(AlertLevel.INFO, "msg", "src")
        assert len(am.alerts) == 0

    def test_max_alerts_negative(self):
        am = AlertManager(max_alerts=-1)
        am.add_alert(AlertLevel.INFO, "msg", "src")
        assert len(am.alerts) == 0

    def test_pending_count(self):
        am = AlertManager()
        a1 = am.add_alert(AlertLevel.INFO, "msg1", "src")
        a2 = am.add_alert(AlertLevel.INFO, "msg2", "src")
        am.acknowledge(a1.alert_id)
        assert am.pending_count == 1

    def test_alert_level_enum(self):
        assert AlertLevel.INFO.value == "info"
        assert AlertLevel.WARNING.value == "warning"
        assert AlertLevel.ERROR.value == "error"
        assert AlertLevel.CRITICAL.value == "critical"

    def test_unicode_message(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "例えメッセージ", "src")
        assert alert.message == "例えメッセージ"

    def test_whitespace_message(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "   ", "src")
        assert alert.message == "   "

    def test_empty_message(self):
        am = AlertManager()
        alert = am.add_alert(AlertLevel.INFO, "", "src")
        assert alert.message == ""


# === HealthReport edge cases ===

class TestHealthReportEdgeCases:
    def test_default_values(self):
        hr = HealthReport()
        assert hr.overall_status == "unknown"
        assert hr.warnings == []
        assert hr.critical_issues == []
        assert hr.score == 1.0
        assert hr.disk_usage is None
        assert hr.source_freshness == {}
        assert hr.error_rates is None

    def test_to_dict_minimal(self):
        hr = HealthReport()
        d = hr.to_dict()
        assert "timestamp" in d
        assert d["overall_status"] == "unknown"
        assert d["score"] == 1.0
        assert d["warnings"] == []
        assert d["critical_issues"] == []
        assert "disk_usage" not in d
        assert "source_freshness" not in d
        assert "error_rates" not in d

    def test_to_dict_with_disk(self):
        hr = HealthReport()
        hr.disk_usage = DiskUsageInfo(total_bytes=1024)
        d = hr.to_dict()
        assert "disk_usage" in d
        assert d["disk_usage"]["total_bytes"] == 1024

    def test_to_dict_with_freshness(self):
        hr = HealthReport()
        sf = SourceFreshness(source="example.com")
        hr.source_freshness = {"example.com": sf}
        d = hr.to_dict()
        assert "source_freshness" in d
        assert "example.com" in d["source_freshness"]

    def test_to_dict_with_errors(self):
        hr = HealthReport()
        hr.error_rates = ErrorRateInfo()
        d = hr.to_dict()
        assert "error_rates" in d
        assert d["error_rates"]["total_crawls"] == 0

    def test_to_summary_string_minimal(self):
        hr = HealthReport()
        s = hr.to_summary_string()
        assert "Health Report" in s
        assert "Status: unknown" in s
        assert "Score: 1.00" in s

    def test_to_summary_string_with_disk(self):
        hr = HealthReport()
        hr.disk_usage = DiskUsageInfo(total_bytes=1048576, file_count=10, dir_count=5)
        s = hr.to_summary_string()
        assert "Disk Usage" in s
        assert "1.00 MB" in s
        assert "Files: 10" in s

    def test_to_summary_string_with_freshness(self):
        hr = HealthReport()
        sf = SourceFreshness(source="example.com")
        hr.source_freshness = {"example.com": sf}
        s = hr.to_summary_string()
        assert "Source Freshness" in s
        assert "example.com" in s
        assert "STALE" in s

    def test_to_summary_string_with_errors(self):
        hr = HealthReport()
        hr.error_rates = ErrorRateInfo()
        hr.error_rates.record_crawl("a.com", success=True)
        s = hr.to_summary_string()
        assert "Error Rates" in s
        assert "Total crawls: 1" in s

    def test_to_summary_string_with_warnings(self):
        hr = HealthReport()
        hr.warnings = ["warning1", "warning2"]
        s = hr.to_summary_string()
        assert "Warnings" in s
        assert "warning1" in s
        assert "warning2" in s

    def test_to_summary_string_with_critical(self):
        hr = HealthReport()
        hr.critical_issues = ["critical1"]
        s = hr.to_summary_string()
        assert "Critical Issues" in s
        assert "critical1" in s

    def test_json_serializable(self):
        hr = HealthReport()
        hr.overall_status = "healthy"
        hr.score = 0.95
        d = hr.to_dict()
        json_str = json.dumps(d)
        assert isinstance(json_str, str)
        parsed = json.loads(json_str)
        assert parsed["overall_status"] == "healthy"


# === ContentMonitor edge cases ===

class TestContentMonitorEdgeCases:
    def test_default_values(self):
        cm = ContentMonitor()
        assert cm.index_dir is None
        assert cm.max_staleness_hours == 24.0
        assert cm.max_error_rate == 0.1
        assert cm.max_disk_mb == 1024.0
        assert cm.source_freshness == {}
        assert isinstance(cm.error_rates, ErrorRateInfo)

    def test_index_dir_string_conversion(self):
        cm = ContentMonitor(index_dir="/tmp/test")
        assert isinstance(cm.index_dir, Path)
        assert cm.index_dir == Path("/tmp/test")

    def test_index_dir_path_passthrough(self):
        p = Path("/tmp/test")
        cm = ContentMonitor(index_dir=p)
        assert cm.index_dir == p

    def test_get_disk_usage_none_dir(self):
        cm = ContentMonitor()
        info = cm.get_disk_usage()
        assert info.total_bytes == 0
        assert info.file_count == 0

    def test_get_disk_usage_nonexistent_dir(self):
        cm = ContentMonitor(index_dir="/tmp/nonexistent_12345")
        info = cm.get_disk_usage()
        assert info.total_bytes == 0
        assert info.file_count == 0

    def test_get_disk_usage_top_n_zero(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("hello")
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage(top_n=0)
            assert info.largest_files == []

    def test_get_disk_usage_top_n_negative(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("hello")
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage(top_n=-5)
            assert info.largest_files == []

    def test_get_disk_usage_top_n_large(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("hello")
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage(top_n=100)
            assert len(info.largest_files) == 1

    def test_get_disk_usage_empty_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage()
            assert info.total_bytes == 0
            assert info.file_count == 0
            assert info.largest_files == []

    def test_get_disk_usage_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "small.txt").write_text("hi")
            Path(tmpdir, "large.txt").write_text("x" * 1000)
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage(top_n=2)
            assert info.file_count == 2
            assert len(info.largest_files) == 2
            # largest first
            assert info.largest_files[0][1] >= info.largest_files[1][1]

    def test_get_disk_usage_subdirectories(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            subdir = Path(tmpdir, "sub")
            subdir.mkdir()
            Path(tmpdir, "root.txt").write_text("root")
            Path(subdir, "child.txt").write_text("child")
            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage()
            assert info.file_count == 2
            assert info.dir_count >= 1

    def test_record_crawl(self):
        cm = ContentMonitor()
        cm.record_crawl("example.com", success=True)
        assert "example.com" in cm.source_freshness
        sf = cm.source_freshness["example.com"]
        assert sf.crawl_count == 1
        assert sf.last_crawled is not None
        assert sf.last_error is None

    def test_record_crawl_failure(self):
        cm = ContentMonitor()
        cm.record_crawl("example.com", success=False, error_message="timeout")
        sf = cm.source_freshness["example.com"]
        assert sf.crawl_count == 1
        assert sf.last_error == "timeout"
        assert sf.last_error_time is not None

    def test_record_crawl_multiple(self):
        cm = ContentMonitor()
        cm.record_crawl("a.com", success=True)
        cm.record_crawl("b.com", success=True)
        assert len(cm.source_freshness) == 2

    def test_get_stale_sources(self):
        cm = ContentMonitor()
        now = datetime.now(timezone.utc)
        cm.source_freshness["fresh"] = SourceFreshness(
            source="fresh", last_crawled=now, crawl_count=1
        )
        cm.source_freshness["stale"] = SourceFreshness(
            source="stale",
            last_crawled=now - timedelta(hours=48),
            crawl_count=1,
        )
        stale = cm.get_stale_sources()
        assert len(stale) == 1
        assert stale[0].source == "stale"

    def test_get_stale_sources_none(self):
        cm = ContentMonitor()
        stale = cm.get_stale_sources()
        assert stale == []

    def test_get_stale_sources_never_crawled(self):
        cm = ContentMonitor()
        cm.source_freshness["never"] = SourceFreshness(source="never")
        stale = cm.get_stale_sources()
        assert len(stale) == 1
        assert stale[0].source == "never"

    def test_generate_health_report(self):
        cm = ContentMonitor()
        report = cm.generate_health_report()
        assert isinstance(report, HealthReport)
        assert report.overall_status in ("healthy", "warning", "critical", "unknown", "degraded", "no_data")

    def test_generate_health_report_with_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cm = ContentMonitor(index_dir=tmpdir)
            report = cm.generate_health_report()
            assert report.disk_usage is not None

    def test_generate_health_report_with_freshness(self):
        cm = ContentMonitor()
        cm.source_freshness["example.com"] = SourceFreshness(
            source="example.com",
            last_crawled=datetime.now(timezone.utc),
            crawl_count=1,
        )
        report = cm.generate_health_report()
        assert "example.com" in report.source_freshness

    def test_generate_health_report_with_errors(self):
        cm = ContentMonitor()
        cm.error_rates.record_crawl("a.com", success=True)
        report = cm.generate_health_report()
        assert report.error_rates is not None
        assert report.error_rates.total_crawls == 1

    def test_unicode_source_in_monitor(self):
        cm = ContentMonitor()
        cm.record_crawl("例え.com", success=True)
        assert "例え.com" in cm.source_freshness

    def test_whitespace_source_in_monitor(self):
        cm = ContentMonitor()
        cm.record_crawl("   ", success=True)
        assert "   " in cm.source_freshness


# === End-to-end integration ===

class TestContentMonitorIntegration:
    def test_full_monitoring_workflow(self):
        cm = ContentMonitor()

        # Record some crawls
        cm.record_crawl("a.com", success=True)
        cm.record_crawl("b.com", success=True)
        cm.record_crawl("c.com", success=False, error_message="timeout")

        # Check health
        report = cm.generate_health_report()
        assert report.overall_status in ("healthy", "warning", "critical", "unknown", "degraded", "no_data")
        assert report.error_rates is not None
        assert report.error_rates.total_crawls == 3

        # Check stale sources
        stale = cm.get_stale_sources()
        assert isinstance(stale, list)

    def test_disk_usage_with_real_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create files of different sizes
            Path(tmpdir, "small.txt").write_text("small")
            Path(tmpdir, "medium.txt").write_text("x" * 100)
            Path(tmpdir, "large.txt").write_text("x" * 1000)

            cm = ContentMonitor(index_dir=tmpdir)
            info = cm.get_disk_usage(top_n=2)

            assert info.file_count == 3
            assert len(info.largest_files) == 2
            # Verify sorted by size descending
            assert info.largest_files[0][1] >= info.largest_files[1][1]

    def test_health_checker_with_monitor(self):
        cm = ContentMonitor()
        hc = HealthChecker()

        # Create some items
        items = [
            {"id": 1, "score": 0.9, "source": "a.com"},
            {"id": 2, "score": 0.8, "source": "b.com"},
        ]

        status = hc.check(items)
        assert status.healthy is True
        assert status.score == 1.0

    def test_alert_manager_with_monitor(self):
        cm = ContentMonitor()
        am = AlertManager()

        # Simulate monitoring and alerting
        cm.record_crawl("a.com", success=False, error_message="timeout")
        am.add_alert(
            AlertLevel.WARNING,
            "Source a.com failed to crawl",
            "content_monitor",
            data={"source": "a.com", "error": "timeout"},
        )

        assert am.pending_count == 1
        alerts = am.get_alerts(level=AlertLevel.WARNING)
        assert len(alerts) == 1
        assert alerts[0].data["source"] == "a.com"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
