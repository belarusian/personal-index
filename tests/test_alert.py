"""Tests for alert management."""

from personal_index.content_monitor.alert import (
    Alert,
    AlertLevel,
    AlertManager,
)


class TestAlert:
    def test_creation(self):
        a = Alert(alert_id="a1", level=AlertLevel.INFO, message="test", source="test")
        assert a.acknowledged is False
        assert a.data == {}


class TestAlertManager:
    def test_add_alert(self):
        mgr = AlertManager()
        alert = mgr.add_alert(AlertLevel.INFO, "message", "source")
        assert alert.message == "message"
        assert len(mgr.alerts) == 1

    def test_add_alert_with_data(self):
        mgr = AlertManager()
        alert = mgr.add_alert(AlertLevel.WARNING, "msg", "src", data={"key": "val"})
        assert alert.data["key"] == "val"

    def test_get_alerts_all(self):
        mgr = AlertManager()
        mgr.add_alert(AlertLevel.INFO, "a", "src")
        mgr.add_alert(AlertLevel.ERROR, "b", "src")
        assert len(mgr.get_alerts()) == 2

    def test_get_alerts_by_level(self):
        mgr = AlertManager()
        mgr.add_alert(AlertLevel.INFO, "a", "src")
        mgr.add_alert(AlertLevel.ERROR, "b", "src")
        errors = mgr.get_alerts(level=AlertLevel.ERROR)
        assert len(errors) == 1

    def test_get_alerts_unacknowledged(self):
        mgr = AlertManager()
        mgr.add_alert(AlertLevel.INFO, "a", "src")
        a2 = mgr.add_alert(AlertLevel.ERROR, "b", "src")
        mgr.acknowledge(a2.alert_id)
        pending = mgr.get_alerts(acknowledged=False)
        assert len(pending) == 1

    def test_acknowledge(self):
        mgr = AlertManager()
        a = mgr.add_alert(AlertLevel.INFO, "msg", "src")
        assert mgr.acknowledge(a.alert_id) is True
        assert a.acknowledged is True

    def test_acknowledge_missing(self):
        mgr = AlertManager()
        assert mgr.acknowledge("missing") is False

    def test_clear_acknowledged(self):
        mgr = AlertManager()
        a1 = mgr.add_alert(AlertLevel.INFO, "a", "src")
        a2 = mgr.add_alert(AlertLevel.ERROR, "b", "src")
        mgr.acknowledge(a1.alert_id)
        cleared = mgr.clear_acknowledged()
        assert cleared == 1
        assert len(mgr.alerts) == 1

    def test_pending_count(self):
        mgr = AlertManager()
        mgr.add_alert(AlertLevel.INFO, "a", "src")
        a2 = mgr.add_alert(AlertLevel.ERROR, "b", "src")
        mgr.acknowledge(a2.alert_id)
        assert mgr.pending_count == 1

    def test_max_alerts_enforced(self):
        mgr = AlertManager(max_alerts=3)
        for i in range(5):
            mgr.add_alert(AlertLevel.INFO, f"msg{i}", "src")
        assert len(mgr.alerts) == 3
