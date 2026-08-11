"""Tests for content monitor module."""

import pytest

from personal_index.content_monitor.alert import Alert, AlertLevel, AlertManager
from personal_index.content_monitor.health import HealthChecker, HealthStatus
from personal_index.content_monitor.monitor import ContentMonitor


class TestAlertManager:
    def test_add_alert(self) -> None:
        manager = AlertManager()
        alert = manager.add_alert(
            level=AlertLevel.INFO,
            message="Test alert",
            source="test",
        )
        assert alert.level == AlertLevel.INFO
        assert len(manager.alerts) == 1

    def test_get_alerts_by_level(self) -> None:
        manager = AlertManager()
        manager.add_alert(AlertLevel.INFO, "info", "test")
        manager.add_alert(AlertLevel.ERROR, "error", "test")
        errors = manager.get_alerts(level=AlertLevel.ERROR)
        assert len(errors) == 1

    def test_acknowledge(self) -> None:
        manager = AlertManager()
        alert = manager.add_alert(AlertLevel.INFO, "test", "test")
        assert manager.acknowledge(alert.alert_id) is True
        assert alert.acknowledged is True

    def test_clear_acknowledged(self) -> None:
        manager = AlertManager()
        alert = manager.add_alert(AlertLevel.INFO, "test", "test")
        manager.acknowledge(alert.alert_id)
        cleared = manager.clear_acknowledged()
        assert cleared == 1
        assert len(manager.alerts) == 0

    def test_pending_count(self) -> None:
        manager = AlertManager()
        manager.add_alert(AlertLevel.INFO, "test", "test")
        assert manager.pending_count == 1

    def test_max_alerts(self) -> None:
        manager = AlertManager(max_alerts=2)
        manager.add_alert(AlertLevel.INFO, "a", "test")
        manager.add_alert(AlertLevel.INFO, "b", "test")
        manager.add_alert(AlertLevel.INFO, "c", "test")
        assert len(manager.alerts) == 2


class TestHealthChecker:
    def test_healthy(self) -> None:
        checker = HealthChecker()
        items = [{"id": "1", "score": 0.8}]
        status = checker.check(items)
        assert status.healthy is True
        assert status.score == 1.0

    def test_unhealthy_no_items(self) -> None:
        checker = HealthChecker(min_items=1)
        status = checker.check([])
        assert status.healthy is False

    def test_duplicates_detected(self) -> None:
        checker = HealthChecker()
        items = [{"id": "1"}, {"id": "1"}]
        status = checker.check(items)
        assert status.healthy is False

    def test_missing_scores(self) -> None:
        checker = HealthChecker()
        items = [{"id": "1"}]
        status = checker.check(items)
        assert status.healthy is False


class TestContentMonitor:
    def test_check_health(self) -> None:
        monitor = ContentMonitor()
        items = [{"id": "1", "score": 0.8}]
        status = monitor.check_health(items)
        assert status.healthy is True

    def test_detect_changes_added(self) -> None:
        monitor = ContentMonitor()
        changes = monitor.detect_changes([{"id": "1"}])
        assert changes["added_count"] == 1

    def test_detect_changes_removed(self) -> None:
        monitor = ContentMonitor()
        monitor.detect_changes([{"id": "1"}])
        changes = monitor.detect_changes([])
        assert changes["removed_count"] == 1

    def test_detect_changes_modified(self) -> None:
        monitor = ContentMonitor()
        monitor.detect_changes([{"id": "1", "title": "Old"}])
        changes = monitor.detect_changes([{"id": "1", "title": "New"}])
        assert changes["modified_count"] == 1

    def test_get_status(self) -> None:
        monitor = ContentMonitor()
        status = monitor.get_status()
        assert "pending_alerts" in status
        assert "tracked_items" in status
