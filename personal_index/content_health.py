"""Content health monitoring for personal-index.

Checks the health and quality of indexed content, identifying
issues like broken links, low-quality content, and stale entries.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class HealthStatus(Enum):
    """Health status of a content item."""
    HEALTHY = "healthy"
    WARNING = "warning"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Severity of a health issue."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class HealthIssue:
    """A health issue found in content."""
    url: str
    title: str
    issue_type: str
    severity: IssueSeverity
    message: str
    suggestion: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "issue_type": self.issue_type,
            "severity": self.severity.value,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class HealthCheckResult:
    """Result of a health check on content."""
    url: str
    title: str
    status: HealthStatus
    issues: list[HealthIssue] = field(default_factory=list)
    score: float = 100.0
    checks_passed: int = 0
    checks_total: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "url": self.url,
            "title": self.title,
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
            "score": self.score,
            "checks_passed": self.checks_passed,
            "checks_total": self.checks_total,
        }


@dataclass
class HealthReport:
    """Overall health report for all indexed content."""
    total_items: int = 0
    healthy_count: int = 0
    warning_count: int = 0
    unhealthy_count: int = 0
    unknown_count: int = 0
    total_issues: int = 0
    results: list[HealthCheckResult] = field(default_factory=list)
    overall_score: float = 100.0

    @property
    def health_percentage(self) -> float:
        """Percentage of healthy items."""
        if self.total_items == 0:
            return 100.0
        return (self.healthy_count / self.total_items) * 100

    def summary(self) -> str:
        """Generate a human-readable summary."""
        lines = [
            "Content Health Report",
            "=" * 40,
            f"Total items: {self.total_items}",
            f"Healthy: {self.healthy_count}",
            f"Warnings: {self.warning_count}",
            f"Unhealthy: {self.unhealthy_count}",
            f"Overall score: {self.overall_score:.1f}/100",
            f"Health percentage: {self.health_percentage:.1f}%",
        ]
        return "\n".join(lines)


@dataclass
class ContentHealthCheck:
    """Configuration for content health checks."""
    min_content_length: int = 50
    min_title_length: int = 3
    max_title_length: int = 200
    require_tags: bool = False
    min_tags: int = 1
    require_score: bool = False
    min_score: float = 0.0


class ContentHealthChecker:
    """Checks health and quality of indexed content.

    Validates content items against configurable rules and
    generates health reports.
    """

    def __init__(self, config: ContentHealthCheck | None = None):
        self.config = config or ContentHealthCheck()

    def check_item(
        self,
        url: str,
        title: str,
        content: str = "",
        tags: list[str] | None = None,
        score: float = 0.0,
        status_code: int = 200,
    ) -> HealthCheckResult:
        """Check health of a single content item.

        Args:
            url: Content URL.
            title: Content title.
            content: Content text.
            tags: Content tags.
            score: Content score.
            status_code: HTTP status code.

        Returns:
            HealthCheckResult with status and issues.
        """
        issues: list[HealthIssue] = []
        checks_total = 0
        checks_passed = 0

        # Check 1: URL validity
        checks_total += 1
        if url and len(url) > 5:
            checks_passed += 1
        else:
            issues.append(HealthIssue(
                url=url, title=title,
                issue_type="invalid_url",
                severity=IssueSeverity.HIGH,
                message="URL is missing or too short",
                suggestion="Ensure content has a valid URL",
            ))

        # Check 2: Title presence
        checks_total += 1
        if title and len(title) >= self.config.min_title_length:
            checks_passed += 1
        else:
            issues.append(HealthIssue(
                url=url, title=title,
                issue_type="missing_title",
                severity=IssueSeverity.MEDIUM,
                message=f"Title is missing or too short (min {self.config.min_title_length} chars)",
                suggestion="Add a descriptive title",
            ))

        # Check 3: Title length
        checks_total += 1
        if len(title) <= self.config.max_title_length:
            checks_passed += 1
        else:
            issues.append(HealthIssue(
                url=url, title=title,
                issue_type="title_too_long",
                severity=IssueSeverity.LOW,
                message=f"Title exceeds {self.config.max_title_length} characters",
                suggestion="Shorten the title",
            ))

        # Check 4: Content length
        checks_total += 1
        if len(content) >= self.config.min_content_length:
            checks_passed += 1
        else:
            issues.append(HealthIssue(
                url=url, title=title,
                issue_type="low_content",
                severity=IssueSeverity.MEDIUM,
                message=f"Content is too short ({len(content)} chars, min {self.config.min_content_length})",
                suggestion="Ensure content has sufficient text",
            ))

        # Check 5: Tags (if required)
        if self.config.require_tags:
            checks_total += 1
            if tags and len(tags) >= self.config.min_tags:
                checks_passed += 1
            else:
                issues.append(HealthIssue(
                    url=url, title=title,
                    issue_type="missing_tags",
                    severity=IssueSeverity.LOW,
                    message=f"Content has no tags (min {self.config.min_tags} required)",
                    suggestion="Add relevant tags for better organization",
                ))

        # Check 6: Score (if required)
        if self.config.require_score:
            checks_total += 1
            if score >= self.config.min_score:
                checks_passed += 1
            else:
                issues.append(HealthIssue(
                    url=url, title=title,
                    issue_type="low_score",
                    severity=IssueSeverity.LOW,
                    message=f"Score is below minimum ({score} < {self.config.min_score})",
                    suggestion="Review content quality or adjust scoring",
                ))

        # Check 7: Status code
        checks_total += 1
        if 200 <= status_code < 400:
            checks_passed += 1
        else:
            issues.append(HealthIssue(
                url=url, title=title,
                issue_type="bad_status",
                severity=IssueSeverity.HIGH,
                message=f"HTTP status code {status_code}",
                suggestion="Check if the URL is still accessible",
            ))

        # Calculate score
        score_val = (checks_passed / checks_total * 100) if checks_total > 0 else 0.0

        # Determine status
        if any(i.severity == IssueSeverity.CRITICAL for i in issues) or any(i.severity == IssueSeverity.HIGH for i in issues):
            status = HealthStatus.UNHEALTHY
        elif any(i.severity == IssueSeverity.MEDIUM for i in issues) or issues:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY

        return HealthCheckResult(
            url=url,
            title=title,
            status=status,
            issues=issues,
            score=score_val,
            checks_passed=checks_passed,
            checks_total=checks_total,
        )

    def check_all(
        self,
        items: list[dict[str, Any]],
    ) -> HealthReport:
        """Check health of all content items.

        Args:
            items: List of content item dicts with keys:
                url, title, content, tags, score, status_code.

        Returns:
            HealthReport with overall health status.
        """
        results = []
        for item in items:
            result = self.check_item(
                url=item.get("url", ""),
                title=item.get("title", ""),
                content=item.get("content", ""),
                tags=item.get("tags", []),
                score=item.get("score", 0.0),
                status_code=item.get("status_code", 200),
            )
            results.append(result)

        healthy = sum(1 for r in results if r.status == HealthStatus.HEALTHY)
        warnings = sum(1 for r in results if r.status == HealthStatus.WARNING)
        unhealthy = sum(1 for r in results if r.status == HealthStatus.UNHEALTHY)
        unknown = sum(1 for r in results if r.status == HealthStatus.UNKNOWN)
        total_issues = sum(len(r.issues) for r in results)

        avg_score = (
            sum(r.score for r in results) / len(results)
            if results else 100.0
        )

        return HealthReport(
            total_items=len(results),
            healthy_count=healthy,
            warning_count=warnings,
            unhealthy_count=unhealthy,
            unknown_count=unknown,
            total_issues=total_issues,
            results=results,
            overall_score=avg_score,
        )
