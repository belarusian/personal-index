"""Content schema definition and validation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from personal_index.content_validator.rules import (
    RuleResult,
    ValidationRule,
    has_required_fields,
)


@dataclass
class ContentSchema:
    """Schema definition for content items.

    Attributes:
        name: Schema name.
        required_fields: Fields that must be present.
        optional_fields: Fields that may be present.
        field_types: Expected types for fields.
    """

    name: str = "default"
    required_fields: list[str] = field(default_factory=lambda: ["id", "title"])
    optional_fields: list[str] = field(default_factory=list)
    field_types: dict[str, type] = field(default_factory=dict)


@dataclass
class SchemaValidator:
    """Validates content items against a schema.

    Attributes:
        schema: The content schema.
        rules: Additional validation rules.
    """

    schema: ContentSchema = field(default_factory=ContentSchema)
    rules: list[ValidationRule] = field(default_factory=list)

    def validate(self, item: dict[str, Any]) -> list[RuleResult]:
        """Validate an item against the schema and rules.

        Args:
            item: Content item to validate.

        Returns:
            List of RuleResult objects.
        """
        results: list[RuleResult] = []

        # Check required fields
        results.append(
            ValidationRule(
                name="required_fields",
                check=has_required_fields(self.schema.required_fields),
                message=f"Missing required fields: {self.schema.required_fields}",
                severity="error",
            ).validate(item)
        )

        # Check field types
        for field_name, expected_type in self.schema.field_types.items():
            value = item.get(field_name)
            if value is not None and not isinstance(value, expected_type):
                results.append(
                    RuleResult(
                        rule_name=f"field_type_{field_name}",
                        passed=False,
                        message=f"Field '{field_name}' expected {expected_type.__name__}",
                        severity="error",
                    )
                )

        # Run custom rules
        for rule in self.rules:
            results.append(rule.validate(item))

        return results

    def is_valid(self, item: dict[str, Any]) -> bool:
        """Check if an item passes all validations.

        Args:
            item: Content item to validate.

        Returns:
            True if all validations pass.
        """
        results = self.validate(item)
        return all(r.passed for r in results)

    def validate_batch(
        self,
        items: list[dict[str, Any]],
    ) -> dict[str, list[RuleResult]]:
        """Validate multiple items.

        Args:
            items: List of content items.

        Returns:
            Dict mapping item ID to validation results.
        """
        results: dict[str, list[RuleResult]] = {}
        for item in items:
            item_id = str(item.get("id", "unknown"))
            results[item_id] = self.validate(item)
        return results
