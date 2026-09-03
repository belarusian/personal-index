"""Tests for content health monitoring module."""

from __future__ import annotations

from personal_index.content_health import (
    ContentHealthCheck,
    ContentHealthChecker,
    HealthCheckResult,
    HealthIssue,
    HealthReport,
    HealthStatus,
    IssueSeverity,
)


class TestHealthIssue:
    def test_to_dict(self):
        issue = HealthIssue(
            url="https://x.com",
            title="Test",
            issue_type="missing_title",
            severity=IssueSeverity.MEDIUM,
            message="Title too short",
            suggestion="Add title",
        )
        d = issue.to_dict()
        assert d["url"] == "https://x.com"
        assert d["severity"] == "medium"


class TestHealthCheckResult:
    def test_to_dict(self):
        result = HealthCheckResult(
            url="https://x.com",
            title="Test",
            status=HealthStatus.HEALTHY,
            issues=[],
            score=100.0,
            checks_passed=5,
            checks_total=5,
        )
        d = result.to_dict()
        assert d["status"] == "healthy"
        assert d["score"] == 100.0


class TestHealthReport:
    def test_summary(self):
        report = HealthReport(
            total_items=10,
            healthy_count=8,
            warning_count=2,
            unhealthy_count=0,
            overall_score=90.0,
        )
        summary = report.summary()
        assert "Total items: 10" in summary
        assert "Healthy: 8" in summary

    def test_health_percentage(self):
        report = HealthReport(
            total_items=10,
            healthy_count=7,
        )
        assert report.health_percentage == 70.0

    def test_health_percentage_empty(self):
        report = HealthReport()
        assert report.health_percentage == 100.0


class TestContentHealthChecker:
    def test_healthy_item(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="A Great Article About Python",
            content="This is a comprehensive article about Python programming that covers many topics.",
            tags=["python", "programming"],
            score=8.0,
            status_code=200,
        )
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert len(result.issues) == 0

    def test_missing_title(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="",
            content="Some content here that is long enough.",
            status_code=200,
        )
        assert result.status == HealthStatus.WARNING
        assert any(i.issue_type == "missing_title" for i in result.issues)

    def test_short_content(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="Title",
            content="Short",
            status_code=200,
        )
        assert any(i.issue_type == "low_content" for i in result.issues)

    def test_bad_status_code(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="Title",
            content="Content here that is long enough to pass.",
            status_code=404,
        )
        assert any(i.issue_type == "bad_status" for i in result.issues)
        assert result.status == HealthStatus.UNHEALTHY

    def test_title_too_long(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="A" * 250,
            content="Content here that is long enough to pass.",
            status_code=200,
        )
        assert any(i.issue_type == "title_too_long" for i in result.issues)

    def test_invalid_url(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="",
            title="Title",
            content="Content here that is long enough to pass.",
            status_code=200,
        )
        assert any(i.issue_type == "invalid_url" for i in result.issues)

    def test_check_all(self):
        checker = ContentHealthChecker()
        report = checker.check_all([
            {
                "url": "https://a.com",
                "title": "Good Page",
                "content": "This is good content that passes all checks easily.",
                "tags": ["tech"],
                "score": 8.0,
                "status_code": 200,
            },
            {
                "url": "https://b.com",
                "title": "",
                "content": "Short",
                "status_code": 404,
            },
        ])
        assert report.total_items == 2
        assert report.healthy_count == 1
        assert report.unhealthy_count == 1

    def test_check_all_empty(self):
        checker = ContentHealthChecker()
        report = checker.check_all([])
        assert report.total_items == 0
        assert report.overall_score == 100.0

    def test_custom_config(self):
        config = ContentHealthCheck(
            min_content_length=10,
            require_tags=True,
            min_tags=2,
        )
        checker = ContentHealthChecker(config=config)
        result = checker.check_item(
            url="https://example.com/page",
            title="Title",
            content="Short content",
            tags=["one"],
            status_code=200,
        )
        assert any(i.issue_type == "missing_tags" for i in result.issues)

    def test_score_calculation(self):
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="",
            content="Short",
            status_code=500,
        )
        # Multiple failures should reduce score
        assert result.score < 100.0


class TestModuleDocstringContract:
    def test_docstring_does_not_promise_stale_detection(self):
        """Regression: module docstring must not over-promise capabilities.

        The module performs no staleness/age/timestamp checks, so its
        docstring must not claim to detect 'stale entries' (TICKET-325).
        """
        import personal_index.content_health as ch

        doc = (ch.__doc__ or "").lower()
        assert "stale" not in doc
        assert "stale entries" not in doc
