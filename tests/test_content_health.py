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


class TestContentHealthCheckerDocstringClaim:
    """TICKET-366: pin the corrected class docstring claim.

    The class docstring now states the checker works on "content items passed
    to check_item/check_all" - not on any "indexed content" source. Witness the
    claim against the returned object: a fresh checker holds no content, and
    check_all surfaces exactly the items passed in (no hidden index backing it).
    """

    def test_fresh_checker_holds_no_content(self):
        """A fresh checker has no content of its own; check_all([]) is empty."""
        checker = ContentHealthChecker()
        report = checker.check_all([])
        assert report.total_items == 0
        assert report.results == []

    def test_check_all_surfaces_exactly_passed_items(self):
        """check_all returns exactly the items passed in, in order."""
        checker = ContentHealthChecker()
        items = [
            {"url": "https://a.example/1", "title": "Alpha", "content": "x" * 60},
            {"url": "https://b.example/2", "title": "Beta", "content": "y" * 60},
            {"url": "https://c.example/3", "title": "Gamma", "content": "z" * 60},
        ]
        report = checker.check_all(items)
        assert report.total_items == len(items)
        assert [r.url for r in report.results] == [it["url"] for it in items]


class TestCheckItemDocstringDefaults:
    """TICKET-444: pin the corrected check_item docstring against the returned
    HealthCheckResult object. The docstring now enumerates the 7 checks (5
    always-run + 2 conditional), the status determination, the score formula,
    and the returned fields. Witness both the normal case (default config: 5
    checks) and the guard path (require_tags/require_score: 7 checks)."""

    def test_check_item_default_config_pins_returned_fields(self):
        """Default config runs the 5 always-run checks; a fully-valid item is
        HEALTHY with score 100.0 and the returned object carries url/title/
        checks_passed/checks_total verbatim."""
        checker = ContentHealthChecker()
        result = checker.check_item(
            url="https://example.com/page",
            title="A Great Article About Python",
            content="This is a comprehensive article about Python programming that covers many topics.",
            tags=["python", "programming"],
            score=8.0,
            status_code=200,
        )
        # returned object fields carried verbatim
        assert result.url == "https://example.com/page"
        assert result.title == "A Great Article About Python"
        # default config: require_tags/require_score are False -> only 5 checks run
        assert result.checks_total == 5
        assert result.checks_passed == 5
        assert result.status == HealthStatus.HEALTHY
        assert result.score == 100.0
        assert result.issues == []

    def test_check_item_conditional_config_pins_guard_path(self):
        """Guard path: with require_tags/require_score set, the two conditional
        checks run (7 total) and a failing item surfaces the conditional issue
        types on the returned object."""
        config = ContentHealthCheck(
            require_tags=True,
            min_tags=2,
            require_score=True,
            min_score=5.0,
        )
        checker = ContentHealthChecker(config=config)
        result = checker.check_item(
            url="https://example.com/page",
            title="A Great Article About Python",
            content="This is a comprehensive article about Python programming that covers many topics.",
            tags=["python"],  # only 1 tag, min_tags=2 -> missing_tags
            score=1.0,  # below min_score=5.0 -> low_score
            status_code=200,
        )
        # both conditional checks now run -> 7 total
        assert result.checks_total == 7
        # the two conditional failures are surfaced on the returned object
        types = {i.issue_type for i in result.issues}
        assert "missing_tags" in types
        assert "low_score" in types
        # 5 always-run checks pass, 2 conditional fail
        assert result.checks_passed == 5
        assert result.score == 5 / 7 * 100
        # both issues are LOW severity -> WARNING (not UNHEALTHY)
        assert result.status == HealthStatus.WARNING
