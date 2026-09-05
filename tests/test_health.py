"""Tests for health checking."""

from personal_index.content_monitor.health import (
    HealthChecker,
    HealthCheck,
)


class TestHealthCheck:
    def test_creation(self):
        hc = HealthCheck(check_name="test", healthy=True)
        assert hc.healthy is True
        assert hc.message == ""
        assert hc.details == {}


class TestHealthChecker:
    def test_healthy_items(self):
        checker = HealthChecker()
        items = [{"id": "1", "score": 0.9}]
        status = checker.check(items)
        assert status.healthy is True
        assert status.score == 1.0

    def test_empty_items(self):
        checker = HealthChecker(min_items=1)
        status = checker.check([])
        assert status.healthy is False

    def test_enough_items(self):
        checker = HealthChecker(min_items=2)
        items = [{"id": "1", "score": 0.5}, {"id": "2", "score": 0.6}]
        status = checker.check(items)
        checks = {c.check_name: c for c in status.checks}
        assert checks["item_count"].healthy is True

    def test_not_enough_items(self):
        checker = HealthChecker(min_items=5)
        items = [{"id": "1", "score": 0.5}]
        status = checker.check(items)
        checks = {c.check_name: c for c in status.checks}
        assert checks["item_count"].healthy is False

    def test_unscored_items(self):
        checker = HealthChecker()
        items = [{"id": "1"}]
        status = checker.check(items)
        checks = {c.check_name: c for c in status.checks}
        assert checks["scores"].healthy is False

    def test_no_duplicates(self):
        checker = HealthChecker()
        items = [{"id": "1", "score": 0.5}, {"id": "2", "score": 0.6}]
        status = checker.check(items)
        checks = {c.check_name: c for c in status.checks}
        assert checks["duplicates"].healthy is True

    def test_duplicates_detected(self):
        checker = HealthChecker()
        items = [{"id": "1", "score": 0.5}, {"id": "1", "score": 0.6}]
        status = checker.check(items)
        checks = {c.check_name: c for c in status.checks}
        assert checks["duplicates"].healthy is False

    def test_score_calculation(self):
        checker = HealthChecker()
        items = [{"id": "1"}]
        status = checker.check(items)
        assert 0.0 <= status.score <= 1.0

    def test_all_checks_present(self):
        checker = HealthChecker()
        status = checker.check([{"id": "1", "score": 0.5}])
        names = [c.check_name for c in status.checks]
        assert "item_count" in names
        assert "scores" in names
        assert "duplicates" in names


class TestCheckPinning:
    def test_all_healthy_normal_case(self):
        checker = HealthChecker(min_items=1)
        items = [{"id": "1", "score": 0.9}, {"id": "2", "score": 0.8}]
        status = checker.check(items)
        # returned object fields: all three checks healthy -> healthy True,
        # score is the fraction of healthy checks (3/3) rounded to 4 places.
        assert status.healthy is True
        assert status.score == 1.0
        assert [c.check_name for c in status.checks] == [
            "item_count", "scores", "duplicates",
        ]
        assert all(c.healthy for c in status.checks)

    def test_empty_items_guard_path(self):
        checker = HealthChecker(min_items=1)
        status = checker.check([])
        # guard path: empty items -> item_count fails (0 < min_items),
        # scores passes (empty list), duplicates passes -> not all healthy,
        # score is the fraction healthy (2/3) rounded to 4 places.
        assert status.healthy is False
        assert status.score == round(2 / 3, 4)
        checks = {c.check_name: c for c in status.checks}
        assert checks["item_count"].healthy is False
        assert checks["scores"].healthy is True
        assert checks["duplicates"].healthy is True
