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
    """Create a rule that checks a field's minimum string length.

    The returned callable returns True when the field is present and the
    length of its string form is at least ``min_length``.

    Contract:
        - A missing field (``item.get(field) is None``) returns False.
        - The value is coerced via ``str(value)``, so non-string values
          (e.g. ``12345``) are measured by the length of their string form.
        - The comparison is inclusive: ``len(str(value)) >= min_length``.

    Args:
        field: Field name to check.
        min_length: Minimum required length (inclusive).

    Returns:
        Callable that returns True if the field is present and its string
        form is at least ``min_length`` characters long.
    """
    def check(item: dict[str, Any]) -> bool:
        value = item.get(field)
        if value is None:
            return False
        return len(str(value)) >= min_length
    return check


def has_valid_url(field: str) -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks a field holds an http(s) URL.

    The returned callable returns True only when the field's string form
    starts with ``"http://"`` or ``"https://"``.

    Contract:
        - "Valid" means the string starts with ``http://`` or ``https://``
          ONLY; other schemes (``ftp://``, ``file://``, ...) fail.
        - An empty string fails.
        - A missing field fails.

    Args:
        field: Field name containing URL.

    Returns:
        Callable that returns True if the field's value starts with
        ``http://`` or ``https://``.
    """
    def check(item: dict[str, Any]) -> bool:
        url = item.get(field)
        if not url:
            return False
        url_str = str(url)
        return url_str.startswith(("http://", "https://"))
    return check


def has_valid_score() -> Callable[[dict[str, Any]], bool]:
    """Create a rule that checks the ``score`` field is in the valid range.

    The returned callable returns True when the ``score`` field is absent or
    is a number in the inclusive range ``[0.0, 1.0]``.

    Contract:
        - A missing score (``item.get("score") is None``) returns True
          (treated as valid).
        - The range is inclusive: both ``0`` and ``1`` pass.
        - Only ``int``/``float`` values pass; a string such as ``"0.5"``
          fails.
        - ``bool`` is a subclass of ``int``, so ``True``/``False`` pass.

    Returns:
        Callable that returns True if the score is absent or is an
        int/float in the inclusive range [0.0, 1.0].
    """
    def check(item: dict[str, Any]) -> bool:
        score = item.get("score")
        if score is None:
            return True
        return isinstance(score, (int, float)) and 0.0 <= score <= 1.0
    return check
