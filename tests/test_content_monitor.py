"""Comprehensive tests for the content_monitor module."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personal_index.content_monitor import (
    ContentMonitor,
    DiskUsageInfo,
    ErrorRateInfo,
    HealthReport,
    SourceFreshness,
)


# ---------------------------------------------------------------------------
# DiskUsageInfo tests
# ---------------------------------------------------------------------------

class TestDiskUsageInfo:
    """Tests for DiskUsageInfo dataclass."""

    def test_default_values(self) -> None:
        info = DiskUsageInfo()
        assert info.total_bytes == 0
        assert info.file_count == 0
        assert info.dir_count == 0
        assert info.largest_files == []

    def test_total_mb(self) -> None:
        info = DiskUsageInfo(total_bytes=1024 * 1024)
        assert info.total_mb == 1.0

    def test_total_gb(self) -> None:
        info = DiskUsageInfo(total_bytes=1024 * 1024 * 1024)
        assert info.total_gb == 1.0

    def test_to_dict(self) -> None:
        info = DiskUsageInfo(
            total_bytes=2048,
            file_count=5,
            dir_count=2,
            largest_files=[("/a/b.txt", 1024), ("/a/c.txt", 512)],
        )
        d = info.to_dict()
        assert d["total_bytes"] == 2048
        assert d["total_mb"] == pytest.approx(0.002, abs=0.001)
        assert d["file_count"] == 5
        assert d["dir_count"] == 2
        assert len(d["largest_files"]) == 2
        assert d["largest_files"][0]["path"] == "/a/b.txt"
        assert d["largest_files"][0]["size_bytes"] == 1024

    def test_to_dict_empty(self) -> None:
        info = DiskUsageInfo()
        d = info.to_dict()
        assert d["total_bytes"] == 0
        assert d["largest_files"] == []


# ---------------------------------------------------------------------------
# SourceFreshness tests
# ---------------------------------------------------------------------------

class TestSourceFreshness:
    """Tests for SourceFreshness dataclass."""

    def test_default_values(self) -> None:
        sf = SourceFreshness()
        assert sf.source == ""
        assert sf.last_crawled is None
        assert sf.crawl_count == 0
        assert sf.last_error is None
        assert sf.last_error_time is None

    def test_staleness_hours_none_when_never_crawled(self) -> None:
        sf = SourceFreshness(source="example.com")
        assert sf.staleness_hours is None

    def test_staleness_hours_calculated(self) -> None:
        two_hours_ago = datetime.now(timezone.utc) - timedelta(hours=2)
        sf = SourceFreshness(source="example.com", last_crawled=two_hours_ago)
        assert sf.staleness_hours is not None
        assert sf.staleness_hours > 1.9
        assert sf.staleness_hours < 2.1

    def test_is_stale_true_when_never_crawled(self) -> None:
        sf = SourceFreshness(source="example.com")
        assert sf.is_stale() is True

    def test_is_stale_true_when_over_threshold(self) -> None:
        yesterday = datetime.now(timezone.utc) - timedelta(hours=48)
        sf = SourceFreshness(source="example.com", last_crawled=yesterday)
        assert sf.is_stale(threshold_hours=24.0) is True

    def test_is_stale_false_when_recent(self) -> None:
        an_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        sf = SourceFreshness(source="example.com", last_crawled=an_hour_ago)
        assert sf.is_stale(threshold_hours=24.0) is False

    def test_to_dict(self) -> None:
        now = datetime.now(timezone.utc)
        sf = SourceFreshness(
            source="example.com",
            last_crawled=now,
            crawl_count=10,
            last_error="timeout",
            last_error_time=now,
        )
        d = sf.to_dict()
        assert d["source"] == "example.com"
        assert d["last_crawled"] == now.isoformat()
        assert d["crawl_count"] == 10
        assert d["last_error"] == "timeout"
        assert d["is_stale"] is False

    def test_to_dict_none_values(self) -> None:
        sf = SourceFreshness(source="example.com")
        d = sf.to_dict()
        assert d["last_crawled"] is None
        assert d["last_error"] is None
        assert d["last_error_time"] is None
        assert d["staleness_hours"] is None
        assert d["is_stale"] is True


# ---------------------------------------------------------------------------
# ErrorRateInfo tests
# ---------------------------------------------------------------------------

class TestErrorRateInfo:
    """Tests for ErrorRateInfo dataclass."""

    def test_default_values(self) -> None:
        er = ErrorRateInfo()
        assert er.total_crawls == 0
        assert er.successful_crawls == 0
        assert er.failed_crawls == 0
        assert er.error_rate == 0.0
        assert er.recent_errors == []

    def test_success_rate_zero_when_no_crawls(self) -> None:
        er = ErrorRateInfo()
        assert er.success_rate == 0.0

    def test_record_successful_crawl(self) -> None:
        er = ErrorRateInfo()
        er.record_crawl("example.com", success=True)
        assert er.total_crawls == 1
        assert er.successful_crawls == 1
        assert er.failed_crawls == 0
        assert er.error_rate == 0.0
        assert er.success_rate == 1.0

    def test_record_failed_crawl(self) -> None:
        er = ErrorRateInfo()
        er.record_crawl("example.com", success=False, error_message="timeout")
        assert er.total_crawls == 1
        assert er.successful_crawls == 0
        assert er.failed_crawls == 1
        assert er.error_rate == 1.0
        assert er.success_rate == 0.0
        assert len(er.recent_errors) == 1
        assert er.recent_errors[0]["source"] == "example.com"
        assert er.recent_errors[0]["error"] == "timeout"

    def test_record_mixed_crawls(self) -> None:
        er = ErrorRateInfo()
        er.record_crawl("a.com", success=True)
        er.record_crawl("b.com", success=True)
        er.record_crawl("c.com", success=False, error_message="404")
        assert er.total_crawls == 3
        assert er.successful_crawls == 2
        assert er.failed_crawls == 1
        assert er.error_rate == pytest.approx(1 / 3, abs=0.001)
        assert er.success_rate == pytest.approx(2 / 3, abs=0.001)

    def test_recent_errors_capped_at_100(self) -> None:
        er = ErrorRateInfo()
        for i in range(150):
            er.record_crawl(f"source{i}.com", success=False, error_message="err")
        assert len(er.recent_errors) == 100

    def test_to_dict(self) -> None:
        er = ErrorRateInfo()
        er.record_crawl("a.com", success=True)
        er.record_crawl("b.com", success=False, error_message="timeout")
        d = er.to_dict()
        assert d["total_crawls"] == 2
        assert d["successful_crawls"] == 1
        assert d["failed_crawls"] == 1
        assert d["error_rate"] == pytest.approx(0.5)
        assert d["success_rate"] == pytest.approx(0.5)
        assert d["recent_errors_count"] == 1

    def test_record_no_error_message(self) -> None:
        er = ErrorRateInfo()
        er.record_crawl("a.com", success=False)
        assert er.failed_crawls == 1
        assert len(er.recent_errors) == 0  # No error message means no record


# ---------------------------------------------------------------------------
# HealthReport tests
# ---------------------------------------------------------------------------

class TestHealthReport:
    """Tests for HealthReport dataclass."""

    def test_default_values(self) -> None:
        report = HealthReport()
        assert report.overall_status == "unknown"
        assert report.warnings == []
        assert report.critical_issues == []
        assert report.score == 1.0
        assert report.disk_usage is None
        assert report.source_freshness == {}
        assert report.error_rates is None

    def test_to_dict_with_all_data(self) -> None:
        disk = DiskUsageInfo(total_bytes=1024, file_count=5, dir_count=1)
        freshness = {"example.com": SourceFreshness(source="example.com", crawl_count=10)}
        errors = ErrorRateInfo(total_crawls=100, successful_crawls=95, failed_crawls=5, error_rate=0.05)
        report = HealthReport(
            disk_usage=disk,
            source_freshness=freshness,
            error_rates=errors,
            overall_status="healthy",
            score=0.95,
            warnings=["minor warning"],
            critical_issues=[],
        )
        d = report.to_dict()
        assert d["overall_status"] == "healthy"
        assert d["score"] == 0.95
        assert "disk_usage" in d
        assert "source_freshness" in d
        assert "error_rates" in d
        assert d["warnings"] == ["minor warning"]

    def test_to_dict_without_optional_data(self) -> None:
        report = HealthReport()
        d = report.to_dict()
        assert "disk_usage" not in d
        assert "source_freshness" not in d
        assert "error_rates" not in d

    def test_to_summary_string(self) -> None:
        disk = DiskUsageInfo(total_bytes=1024 * 1024, file_count=10, dir_count=2)
        report = HealthReport(
            disk_usage=disk,
            overall_status="healthy",
            score=1.0,
        )
        summary = report.to_summary_string()
        assert "Health Report" in summary
        assert "healthy" in summary
        assert "Disk Usage" in summary
        assert "1.00 MB" in summary

    def test_to_summary_string_with_warnings(self) -> None:
        report = HealthReport(
            overall_status="degraded",
            score=0.8,
            warnings=["disk high"],
            critical_issues=["error rate high"],
        )
        summary = report.to_summary_string()
        assert "Warnings" in summary
        assert "disk high" in summary
        assert "Critical Issues" in summary
        assert "error rate high" in summary

    def test_to_summary_string_with_sources(self) -> None:
        now = datetime.now(timezone.utc)
        freshness = {
            "a.com": SourceFreshness(source="a.com", last_crawled=now, crawl_count=5),
            "b.com": SourceFreshness(source="b.com"),  # never crawled
        }
        report = HealthReport(source_freshness=freshness)
        summary = report.to_summary_string()
        assert "Source Freshness" in summary
        assert "a.com" in summary
        assert "b.com" in summary
        assert "STALE" in summary
        assert "OK" in summary

    def test_to_summary_string_with_errors(self) -> None:
        errors = ErrorRateInfo(total_crawls=100, successful_crawls=90, failed_crawls=10, error_rate=0.1)
        report = HealthReport(error_rates=errors)
        summary = report.to_summary_string()
        assert "Error Rates" in summary
        assert "100" in summary


# ---------------------------------------------------------------------------
# ContentMonitor tests
# ---------------------------------------------------------------------------

class TestContentMonitor:
    """Tests for ContentMonitor class."""

    def test_init_defaults(self) -> None:
        monitor = ContentMonitor()
        assert monitor.max_staleness_hours == 24.0
        assert monitor.max_error_rate == 0.1
        assert monitor.max_disk_mb == 1024.0
        assert monitor.source_freshness == {}

    def test_init_custom_params(self) -> None:
        monitor = ContentMonitor(
            index_dir="/tmp/test_index",
            max_staleness_hours=48.0,
            max_error_rate=0.2,
            max_disk_mb=2048.0,
        )
        assert monitor.index_dir == Path("/tmp/test_index")
        assert monitor.max_staleness_hours == 48.0
        assert monitor.max_error_rate == 0.2
        assert monitor.max_disk_mb == 2048.0

    def test_init_with_path_object(self) -> None:
        monitor = ContentMonitor(index_dir=Path("/tmp/test"))
        assert isinstance(monitor.index_dir, Path)

    # -- get_disk_usage --

    def test_get_disk_usage_nonexistent_dir(self) -> None:
        monitor = ContentMonitor(index_dir="/nonexistent/path/xyz")
        info = monitor.get_disk_usage()
        assert info.total_bytes == 0
        assert info.file_count == 0

    def test_get_disk_usage_empty_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ContentMonitor(index_dir=tmpdir)
            info = monitor.get_disk_usage()
            assert info.total_bytes == 0
            assert info.file_count == 0
            assert info.dir_count == 0

    def test_get_disk_usage_with_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create some files
            Path(tmpdir, "file1.txt").write_text("hello" * 100)
            Path(tmpdir, "file2.txt").write_text("world" * 200)
            subdir = Path(tmpdir, "sub")
            subdir.mkdir()
            Path(subdir, "file3.txt").write_text("data" * 50)

            monitor = ContentMonitor(index_dir=tmpdir)
            info = monitor.get_disk_usage()

            assert info.total_bytes > 0
            assert info.file_count == 3
            assert info.dir_count == 1
            assert len(info.largest_files) == 3

    def test_get_disk_usage_top_n(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            for i in range(10):
                Path(tmpdir, f"file{i}.txt").write_text("x" * (i * 100))

            monitor = ContentMonitor(index_dir=tmpdir)
            info = monitor.get_disk_usage(top_n=3)
            assert len(info.largest_files) == 3
            # Largest should be file9
            assert info.largest_files[0][1] == 900

    # -- record_crawl --

    def test_record_crawl_success(self) -> None:
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("example.com", success=True, timestamp=now)

        assert "example.com" in monitor.source_freshness
        sf = monitor.source_freshness["example.com"]
        assert sf.last_crawled == now
        assert sf.crawl_count == 1
        assert sf.last_error is None

    def test_record_crawl_failure(self) -> None:
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("example.com", success=False, error_message="timeout", timestamp=now)

        sf = monitor.source_freshness["example.com"]
        assert sf.crawl_count == 1
        assert sf.last_error == "timeout"
        assert sf.last_error_time == now

    def test_record_crawl_updates_error_rates(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=False, error_message="404")

        assert monitor.error_rates.total_crawls == 2
        assert monitor.error_rates.successful_crawls == 1
        assert monitor.error_rates.failed_crawls == 1

    def test_record_crawl_multiple_sources(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=True)
        monitor.record_crawl("a.com", success=False, error_message="fail")

        assert monitor.source_freshness["a.com"].crawl_count == 2
        assert monitor.source_freshness["b.com"].crawl_count == 1

    def test_record_crawl_success_clears_previous_error(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=False, error_message="fail")
        assert monitor.source_freshness["a.com"].last_error == "fail"

        monitor.record_crawl("a.com", success=True)
        assert monitor.source_freshness["a.com"].last_error is None

    # -- get_source_freshness --

    def test_get_source_freshness_all(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=True)

        result = monitor.get_source_freshness()
        assert len(result) == 2
        assert "a.com" in result
        assert "b.com" in result

    def test_get_source_freshness_specific(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=True)

        result = monitor.get_source_freshness("a.com")
        assert len(result) == 1
        assert "a.com" in result
        assert "b.com" not in result

    def test_get_source_freshness_missing_source(self) -> None:
        monitor = ContentMonitor()
        result = monitor.get_source_freshness("nonexistent.com")
        assert result == {}

    # -- get_stale_sources --

    def test_get_stale_sources_empty(self) -> None:
        monitor = ContentMonitor()
        assert monitor.get_stale_sources() == []

    def test_get_stale_sources_never_crawled(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=False)  # never successful
        stale = monitor.get_stale_sources()
        assert len(stale) == 1
        assert stale[0].source == "a.com"

    def test_get_stale_sources_over_threshold(self) -> None:
        monitor = ContentMonitor()
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        monitor.record_crawl("a.com", success=True, timestamp=old_time)

        stale = monitor.get_stale_sources()
        assert len(stale) == 1

    def test_get_stale_sources_custom_threshold(self) -> None:
        monitor = ContentMonitor()
        old_time = datetime.now(timezone.utc) - timedelta(hours=12)
        monitor.record_crawl("a.com", success=True, timestamp=old_time)

        # With 24h threshold, not stale
        stale = monitor.get_stale_sources(threshold_hours=24.0)
        assert len(stale) == 0

        # With 6h threshold, stale
        stale = monitor.get_stale_sources(threshold_hours=6.0)
        assert len(stale) == 1

    # -- get_error_rates --

    def test_get_error_rates(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=False, error_message="err")

        rates = monitor.get_error_rates()
        assert rates.total_crawls == 2
        assert rates.error_rate == pytest.approx(0.5)

    # -- generate_health_report --

    def test_health_report_healthy(self) -> None:
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("a.com", success=True, timestamp=now)
        monitor.record_crawl("b.com", success=True, timestamp=now)

        report = monitor.generate_health_report()
        assert report.overall_status == "healthy"
        assert report.score == 1.0
        assert report.warnings == []
        assert report.critical_issues == []

    def test_health_report_no_data(self) -> None:
        monitor = ContentMonitor()
        report = monitor.generate_health_report()
        assert report.overall_status == "no_data"

    def test_health_report_stale_warning(self) -> None:
        monitor = ContentMonitor()
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        monitor.record_crawl("a.com", success=True, timestamp=old_time)

        report = monitor.generate_health_report()
        assert report.overall_status == "degraded"
        assert len(report.warnings) > 0
        assert "stale" in report.warnings[0].lower()

    def test_health_report_high_error_rate(self) -> None:
        monitor = ContentMonitor(max_error_rate=0.1)
        for i in range(10):
            monitor.record_crawl(f"src{i}.com", success=True)
        for i in range(10):
            monitor.record_crawl(f"fail{i}.com", success=False, error_message="err")

        report = monitor.generate_health_report()
        assert report.overall_status == "critical"
        assert len(report.critical_issues) > 0
        assert "error rate" in report.critical_issues[0].lower()

    def test_health_report_disk_critical(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a large file to exceed threshold
            large_file = Path(tmpdir, "big.bin")
            large_file.write_bytes(b"x" * int(2048 * 1024 * 1024))  # 2GB virtual

            # We can't actually write 2GB, so we mock getsize
            monitor = ContentMonitor(index_dir=tmpdir, max_disk_mb=0.001)
            # Even a tiny file will exceed 0.001 MB threshold
            Path(tmpdir, "tiny.txt").write_text("hello")

            report = monitor.generate_health_report()
            assert report.overall_status == "critical"
            assert len(report.critical_issues) > 0

    def test_health_report_disk_warning(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            Path(tmpdir, "file.txt").write_text("hello")
            monitor = ContentMonitor(index_dir=tmpdir, max_disk_mb=100.0)
            # File is tiny, so no warning
            report = monitor.generate_health_report()
            assert "disk" not in " ".join(report.warnings).lower() or report.overall_status in ("healthy", "no_data")

    def test_health_report_majority_stale_critical(self) -> None:
        monitor = ContentMonitor()
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        now = datetime.now(timezone.utc)
        # 3 stale, 1 fresh -> majority stale
        monitor.record_crawl("a.com", success=True, timestamp=old_time)
        monitor.record_crawl("b.com", success=True, timestamp=old_time)
        monitor.record_crawl("c.com", success=True, timestamp=old_time)
        monitor.record_crawl("d.com", success=True, timestamp=now)

        report = monitor.generate_health_report()
        assert report.overall_status == "critical"
        assert len(report.critical_issues) > 0

    def test_health_report_score_clamped(self) -> None:
        monitor = ContentMonitor(max_error_rate=0.01, max_disk_mb=0.001)
        # Cause multiple issues to try to drive score below 0
        for i in range(20):
            monitor.record_crawl(f"fail{i}.com", success=False, error_message="err")
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        for i in range(10):
            monitor.record_crawl(f"stale{i}.com", success=True, timestamp=old_time)

        report = monitor.generate_health_report()
        assert report.score >= 0.0
        assert report.score <= 1.0

    def test_health_report_to_dict(self) -> None:
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("a.com", success=True, timestamp=now)
        report = monitor.generate_health_report()
        d = report.to_dict()
        assert "timestamp" in d
        assert "overall_status" in d
        assert "score" in d
        assert "disk_usage" in d
        assert "source_freshness" in d
        assert "error_rates" in d

    # -- reset --

    def test_reset(self) -> None:
        monitor = ContentMonitor()
        monitor.record_crawl("a.com", success=True)
        monitor.record_crawl("b.com", success=False, error_message="err")

        monitor.reset()
        assert monitor.source_freshness == {}
        assert monitor.error_rates.total_crawls == 0

    # -- get_summary --

    def test_get_summary(self) -> None:
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("a.com", success=True, timestamp=now)
        monitor.record_crawl("b.com", success=False, error_message="err")

        summary = monitor.get_summary()
        assert "disk_usage_mb" in summary
        assert "file_count" in summary
        assert summary["total_sources"] == 2
        assert summary["total_crawls"] == 2
        assert "error_rate" in summary
        assert "success_rate" in summary

    def test_get_summary_stale_sources(self) -> None:
        monitor = ContentMonitor()
        old_time = datetime.now(timezone.utc) - timedelta(hours=48)
        monitor.record_crawl("stale.com", success=True, timestamp=old_time)

        summary = monitor.get_summary()
        assert summary["stale_sources"] == 1
        assert "stale.com" in summary["stale_source_names"]


# ---------------------------------------------------------------------------
# Integration-style tests
# ---------------------------------------------------------------------------

class TestContentMonitorIntegration:
    """Integration tests for ContentMonitor workflows."""

    def test_full_monitoring_workflow(self) -> None:
        """Test a complete monitoring workflow."""
        with tempfile.TemporaryDirectory() as tmpdir:
            monitor = ContentMonitor(index_dir=tmpdir)

            # Simulate crawls
            now = datetime.now(timezone.utc)
            monitor.record_crawl("rss.example.com", success=True, timestamp=now)
            monitor.record_crawl("blog.example.com", success=True, timestamp=now)
            monitor.record_crawl("feed.example.com", success=False, error_message="timeout", timestamp=now)

            # Check freshness
            freshness = monitor.get_source_freshness()
            assert len(freshness) == 3

            # Check error rates
            rates = monitor.get_error_rates()
            assert rates.total_crawls == 3
            assert rates.failed_crawls == 1

            # Generate report
            report = monitor.generate_health_report()
            assert report.overall_status in ("healthy", "degraded")
            assert report.score > 0

            # Summary
            summary = monitor.get_summary()
            assert summary["total_sources"] == 3

    def test_monitoring_over_time(self) -> None:
        """Test monitoring data accumulates correctly over time."""
        monitor = ContentMonitor()

        # First batch
        t1 = datetime.now(timezone.utc)
        monitor.record_crawl("a.com", success=True, timestamp=t1)
        monitor.record_crawl("b.com", success=True, timestamp=t1)

        # Second batch
        t2 = t1 + timedelta(hours=1)
        monitor.record_crawl("a.com", success=True, timestamp=t2)
        monitor.record_crawl("c.com", success=False, error_message="err", timestamp=t2)

        # Verify accumulation
        assert monitor.source_freshness["a.com"].crawl_count == 2
        assert monitor.source_freshness["b.com"].crawl_count == 1
        assert monitor.source_freshness["c.com"].crawl_count == 1
        assert monitor.error_rates.total_crawls == 4

    def test_disk_usage_with_nested_dirs(self) -> None:
        """Test disk usage calculation with nested directory structure."""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create nested structure
            Path(tmpdir, "level1", "level2", "level3").mkdir(parents=True)
            Path(tmpdir, "root.txt").write_text("root")
            Path(tmpdir, "level1", "l1.txt").write_text("level1" * 10)
            Path(tmpdir, "level1", "level2", "l2.txt").write_text("level2" * 20)
            Path(tmpdir, "level1", "level2", "level3", "l3.txt").write_text("level3" * 30)

            monitor = ContentMonitor(index_dir=tmpdir)
            info = monitor.get_disk_usage()

            assert info.file_count == 4
            assert info.dir_count >= 3  # level1, level2, level3
            assert info.total_bytes > 0

    def test_health_report_summary_string(self) -> None:
        """Test that health report generates a valid summary string."""
        monitor = ContentMonitor()
        now = datetime.now(timezone.utc)
        monitor.record_crawl("a.com", success=True, timestamp=now)
        monitor.record_crawl("b.com", success=False, error_message="timeout", timestamp=now)

        report = monitor.generate_health_report()
        summary = report.to_summary_string()

        assert "Health Report" in summary
        assert "a.com" in summary
        assert "b.com" in summary
        assert "Error Rates" in summary
        assert "Source Freshness" in summary
