"""Content validation module for personal-index.

Provides validation rules and validators for content items,
ensuring data quality and consistency.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ValidationError:
    """A single validation error.

    Attributes:
        field: The field that failed validation.
        message: Human-readable error message.
        severity: Error severity level.
        value: The invalid value.
    """

    field: str
    message: str
    severity: str = "error"
    value: Any = None


@dataclass
class ValidationResult:
    """Result of validating content items.

    Attributes:
        is_valid: Whether all items passed validation.
        errors: List of validation errors.
        warnings: List of validation warnings.
        items_valid: Number of valid items.
        items_invalid: Number of invalid items.
    """

    is_valid: bool = True
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    items_valid: int = 0
    items_invalid: int = 0

    def add_error(
        self,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation error."""
        self.errors.append(ValidationError(
            field=field, message=message, value=value,
        ))
        self.is_valid = False

    def add_warning(
        self,
        field: str,
        message: str,
        value: Any = None,
    ) -> None:
        """Add a validation warning."""
        self.warnings.append(ValidationError(
            field=field, message=message, severity="warning", value=value,
        ))

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "is_valid": self.is_valid,
            "error_count": len(self.errors),
            "warning_count": len(self.warnings),
            "items_valid": self.items_valid,
            "items_invalid": self.items_invalid,
            "errors": [
                {"field": e.field, "message": e.message}
                for e in self.errors
            ],
        }


class ContentValidator:
    """Validates content items against defined rules.

    Checks for required fields, valid URLs, proper date formats,
    and configurable custom rules.
    """

    def __init__(
        self,
        required_fields: list[str] | None = None,
        max_title_length: int = 500,
        max_url_length: int = 2048,
    ) -> None:
        self.required_fields = required_fields or ["id", "url"]
        self.max_title_length = max_title_length
        self.max_url_length = max_url_length

    def validate(
        self,
        items: list[dict[str, Any]],
    ) -> ValidationResult:
        """Validate a list of content items."""
        result = ValidationResult()

        for i, item in enumerate(items):
            item_valid = self._validate_item(item, i, result)
            if item_valid:
                result.items_valid += 1
            else:
                result.items_invalid += 1

        return result

    def _validate_item(
        self, item: dict[str, Any], index: int, result: ValidationResult
    ) -> bool:
        item_valid = True
        prefix = f"item[{index}]"
        item_valid = self._check_required_fields(item, prefix, result) and item_valid
        item_valid = self._validate_url(item, prefix, result) and item_valid
        self._validate_title(item, prefix, result)
        item_valid = self._validate_score(item, prefix, result) and item_valid
        item_valid = self._validate_dates(item, prefix, result) and item_valid
        return item_valid

    def _check_required_fields(
        self, item: dict[str, Any], prefix: str, result: ValidationResult
    ) -> bool:
        valid = True
        for field_name in self.required_fields:
            if field_name not in item:
                result.add_error(
                    f"{prefix}.{field_name}",
                    f"Required field '{field_name}' is missing",
                )
                valid = False
        return valid

    def _validate_url(
        self, item: dict[str, Any], prefix: str, result: ValidationResult
    ) -> bool:
        url = item.get("url", "")
        if not url:
            return True
        if not self._is_valid_url(url):
            result.add_error(f"{prefix}.url", f"Invalid URL: {url}", value=url)
            return False
        if len(url) > self.max_url_length:
            result.add_error(
                f"{prefix}.url", f"URL exceeds max length of {self.max_url_length}"
            )
            return False
        return True

    def _validate_title(
        self, item: dict[str, Any], prefix: str, result: ValidationResult
    ) -> None:
        title = item.get("title", "")
        if title and len(title) > self.max_title_length:
            result.add_warning(
                f"{prefix}.title",
                f"Title exceeds recommended length of {self.max_title_length}",
            )

    def _validate_score(
        self, item: dict[str, Any], prefix: str, result: ValidationResult
    ) -> bool:
        score = item.get("score")
        if score is None:
            return True
        if not isinstance(score, (int, float)):
            result.add_error(f"{prefix}.score", "Score must be a number")
            return False
        if not (0.0 <= score <= 1.0):
            result.add_warning(
                f"{prefix}.score", f"Score {score} is outside typical range [0, 1]"
            )
        return True

    def _validate_dates(
        self, item: dict[str, Any], prefix: str, result: ValidationResult
    ) -> bool:
        valid = True
        for date_field in ("published_at", "updated_at"):
            date_val = item.get(date_field)
            if date_val and not self._is_valid_date(date_val):
                result.add_error(
                    f"{prefix}.{date_field}", f"Invalid date format: {date_val}"
                )
                valid = False
        return valid

    def validate_single(self, item: dict[str, Any]) -> ValidationResult:
        """Validate a single content item."""
        return self.validate([item])

    def _is_valid_url(self, url: str) -> bool:
        """Check if a URL is valid."""
        if not url:
            return False
        return url.startswith(("http://", "https://"))

    def _is_valid_date(self, value: Any) -> bool:
        """Check if a value is a valid date."""
        if isinstance(value, datetime):
            return True
        if isinstance(value, str):
            try:
                datetime.fromisoformat(value)
                return True
            except ValueError:
                return False
        return False
