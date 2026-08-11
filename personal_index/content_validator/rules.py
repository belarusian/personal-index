"""Validation rules for content items."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass
class RuleResult:
    """Result of a validation rule check.

    Attributes:
        rule_name: Name of the rule.
        passed: Whether the rule passed.
        message: Description of the result.
        severity: Severity level (info, warning, error).
    """

    rule_name: str
    passed: bool
    message: str = ""
    severity: str = "info"


@dataclass
class ValidationRule:
    """A single validation rule.

    Attributes:
        name: Rule name.
        check: Callable that returns True if valid.
        message: Message on failure.
        severity: Severity level.
    """

    name: str
    check: Callable[[dict[str, Any]], bool]
    message: str = ""
    severity: str = "warning"

    def validate(self, item: dict[str, Any]) -> RuleResult:
        """Validate an item against this rule.

        Args:
            item: Content item to validate.

        Returns:
            RuleResult with validation outcome.
        """
        passed = self.check(item)
        return RuleResult(
            rule_name=self.name,
            passed=passed,
            message=self.message if not passed else "",
            severity=self.severity,
        )


def has_required_fields(
    fields: list[str],
) -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks for required fields.

    Args:
        fields: List of required field names.

    Returns:
        Callable that returns True if all fields present.
    """
    def check(item: dict[str, Any]) -> bool:
        return all(f in item for f in fields)
    return check


def has_min_length(
    field: str,
    min_length: int,
) -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks minimum string length.

    Args:
        field: Field name to check.
        min_length: Minimum required length.

    Returns:
        Callable that returns True if field meets length.
    """
    def check(item: dict[str, Any]) -> bool:
        value = item.get(field)
        if value is None:
            return False
        return len(str(value)) >= min_length
    return check


def has_valid_url(field: str) -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks URL validity.

    Args:
        field: Field name containing URL.

    Returns:
        Callable that returns True if URL is valid.
    """
    def check(item: dict[str, Any]) -> bool:
        url = item.get(field)
        if not url:
            return False
        url_str = str(url)
        return url_str.startswith(("http://", "https://"))
    return check


def has_valid_score() -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks score is in valid range.

    Returns:
        Callable that returns True if score is between 0 and 1.
    """
    def check(item: dict[str, Any]) -> bool:
        score = item.get("score")
        if score is None:
            return True
        return isinstance(score, (int, float)) and 0.0 <= score <= 1.0
    return check
