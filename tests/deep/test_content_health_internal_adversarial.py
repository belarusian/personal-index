"""Adversarial regression-armor pins for content_health internal helpers.

Cycle 373: pins the dataclass serialization (to_dict/from_dict round-trips),
HealthReport.summary/health_percentage, and the private _build_report /
_determine_status / _check_from_dict helpers that the existing
test_content_health_adversarial.py does NOT directly exercise.

All pins are regression armor (they must PASS). Contract source:
personal_index/content_health.py docstrings.
"""

from __future__ import annotations

import json


from personal_index.content_health import (
    ContentHealthChecker,
    HealthCheckResult,
    HealthIssue,
    HealthReport,
    HealthStatus,
    IssueSeverity,
)


def _issue(sev: IssueSeverity = IssueSeverity.LOW) -> HealthIssue:
    return HealthIssue(
        url="http://example.com",
        title="T",
        issue_type="t",
        severity=sev,
        message="m",
        suggestion="s",
    )


def _result(status: HealthStatus = HealthStatus.HEALTHY) -> HealthCheckResult:
    return HealthCheckResult(
        url="http://example.com",
        title="T",
        status=status,
        issues=[_issue()],
        score=50.0,
        checks_passed=1,
        checks_total=2,
    )


# ── HealthIssue serialization ──────────────────────────────────────────
class TestHealthIssueRoundTrip:
    def test_full_round_trip(self) -> None:
        hi = _issue(IssueSeverity.HIGH)
        assert HealthIssue.from_dict(hi.to_dict()) == hi

    def test_suggestion_defaults_empty(self) -> None:
        d = _issue().to_dict()
        del d["suggestion"]
        assert HealthIssue.from_dict(d).suggestion == ""

    def test_severity_mapped_back_to_enum(self) -> None:
        d = _issue(IssueSeverity.CRITICAL).to_dict()
        assert d["severity"] == "critical"
        assert HealthIssue.from_dict(d).severity is IssueSeverity.CRITICAL

    def test_round_trip_through_json(self) -> None:
        hi = _issue(IssueSeverity.MEDIUM)
        assert HealthIssue.from_dict(json.loads(json.dumps(hi.to_dict()))) == hi


# ── HealthCheckResult serialization ────────────────────────────────────
class TestHealthCheckResultRoundTrip:
    def test_full_round_trip(self) -> None:
        r = _result(HealthStatus.WARNING)
        assert HealthCheckResult.from_dict(r.to_dict()) == r

    def test_missing_optional_fields_default(self) -> None:
        d = {"url": "u", "title": "t", "status": "healthy"}
        r = HealthCheckResult.from_dict(d)
        assert r.issues == []
        assert r.score == 100.0
        assert r.checks_passed == 0
        assert r.checks_total == 0

    def test_nested_issues_rebuilt(self) -> None:
        r = _result()
        r2 = HealthCheckResult.from_dict(r.to_dict())
        assert isinstance(r2.issues[0], HealthIssue)
        assert r2.issues[0].severity is IssueSeverity.LOW


# ── HealthReport serialization + summary ───────────────────────────────
class TestHealthReportRoundTrip:
    def _report(self) -> HealthReport:
        return HealthReport(
            total_items=2,
            healthy_count=1,
            warning_count=1,
            unhealthy_count=0,
            unknown_count=0,
            total_issues=1,
            results=[_result(HealthStatus.HEALTHY), _result(HealthStatus.WARNING)],
            overall_score=50.0,
        )

    def test_full_round_trip(self) -> None:
        rep = self._report()
        assert HealthReport.from_dict(rep.to_dict()) == rep

    def test_missing_fields_default(self) -> None:
        rep = HealthReport.from_dict({})
        assert rep.total_items == 0
        assert rep.overall_score == 100.0
        assert rep.results == []

    def test_health_percentage_empty_is_100(self) -> None:
        assert HealthReport().health_percentage == 100.0

    def test_health_percentage_computed(self) -> None:
        rep = self._report()
        assert rep.health_percentage == 50.0

    def test_summary_lines(self) -> None:
        rep = self._report()
        lines = rep.summary().split("\n")
        assert lines[0] == "Content Health Report"
        assert lines[1] == "=" * 40
        assert lines[2] == "Total items: 2"
        assert lines[3] == "Healthy: 1"
        assert lines[4] == "Warnings: 1"
        assert lines[5] == "Unhealthy: 0"
        assert lines[6] == "Overall score: 50.0/100"
        assert lines[7] == "Health percentage: 50.0%"


# ── _determine_status ──────────────────────────────────────────────────
class TestDetermineStatus:
    def test_no_issues_healthy(self) -> None:
        assert ContentHealthChecker()._determine_status([]) is HealthStatus.HEALTHY

    def test_only_low_warning(self) -> None:
        assert ContentHealthChecker()._determine_status([_issue(IssueSeverity.LOW)]) is HealthStatus.WARNING

    def test_only_medium_warning(self) -> None:
        assert ContentHealthChecker()._determine_status([_issue(IssueSeverity.MEDIUM)]) is HealthStatus.WARNING

    def test_high_unhealthy(self) -> None:
        assert ContentHealthChecker()._determine_status([_issue(IssueSeverity.HIGH)]) is HealthStatus.UNHEALTHY

    def test_critical_unhealthy(self) -> None:
        assert ContentHealthChecker()._determine_status([_issue(IssueSeverity.CRITICAL)]) is HealthStatus.UNHEALTHY

    def test_mixed_high_and_low_unhealthy(self) -> None:
        issues = [_issue(IssueSeverity.LOW), _issue(IssueSeverity.HIGH)]
        assert ContentHealthChecker()._determine_status(issues) is HealthStatus.UNHEALTHY


# ── _build_report ──────────────────────────────────────────────────────
class TestBuildReport:
    def test_empty_results_defaults(self) -> None:
        rep = ContentHealthChecker()._build_report([])
        assert rep.total_items == 0
        assert rep.overall_score == 100.0
        assert rep.total_issues == 0

    def test_counts_aggregate(self) -> None:
        results = [
            _result(HealthStatus.HEALTHY),
            _result(HealthStatus.WARNING),
            _result(HealthStatus.UNHEALTHY),
        ]
        rep = ContentHealthChecker()._build_report(results)
        assert rep.total_items == 3
        assert rep.healthy_count == 1
        assert rep.warning_count == 1
        assert rep.unhealthy_count == 1
        assert rep.total_issues == 3

    def test_overall_score_is_mean(self) -> None:
        results = [
            HealthCheckResult(url="a", title="a", status=HealthStatus.HEALTHY, score=80.0),
            HealthCheckResult(url="b", title="b", status=HealthStatus.HEALTHY, score=60.0),
        ]
        rep = ContentHealthChecker()._build_report(results)
        assert rep.overall_score == 70.0


# ── _check_from_dict ───────────────────────────────────────────────────
class TestCheckFromDict:
    def test_missing_keys_default(self) -> None:
        r = ContentHealthChecker()._check_from_dict({})
        assert r.url == ""
        assert r.title == ""
        # empty url + empty title + empty content -> issues, not a crash
        assert r.status in (HealthStatus.WARNING, HealthStatus.UNHEALTHY)

    def test_full_item_healthy(self) -> None:
        item = {
            "url": "http://example.com",
            "title": "Good Title",
            "content": "x" * 60,
            "tags": [],
            "score": 0.0,
            "status_code": 200,
        }
        r = ContentHealthChecker()._check_from_dict(item)
        assert r.status is HealthStatus.HEALTHY
        assert r.issues == []

    def test_idempotent_double_call(self) -> None:
        c = ContentHealthChecker()
        item = {"url": "http://example.com", "title": "T", "content": "x" * 60}
        assert c._check_from_dict(item) == c._check_from_dict(item)
