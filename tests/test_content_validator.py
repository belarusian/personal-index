"""Tests for content validator module."""

import pytest

from personal_index.content_validator.quality import QualityChecker, QualityScore
from personal_index.content_validator.rules import (
    RuleResult,
    ValidationRule,
    has_required_fields,
    has_min_length,
    has_valid_url,
    has_valid_score,
)
from personal_index.content_validator.schema import (
    ContentSchema,
    SchemaValidator,
)


class TestValidationRule:
    def test_rule_pass(self) -> None:
        rule = ValidationRule(
            name="test",
            check=lambda item: True,
        )
        result = rule.validate({})
        assert result.passed is True

    def test_rule_fail(self) -> None:
        rule = ValidationRule(
            name="test",
            check=lambda item: False,
            message="Failed",
        )
        result = rule.validate({})
        assert result.passed is False
        assert result.message == "Failed"

    def test_has_required_fields(self) -> None:
        check = has_required_fields(["id", "title"])
        assert check({"id": "1", "title": "T"}) is True
        assert check({"id": "1"}) is False

    def test_has_min_length(self) -> None:
        check = has_min_length("title", 3)
        assert check({"title": "Hello"}) is True
        assert check({"title": "Hi"}) is False
        assert check({}) is False

    def test_has_valid_url(self) -> None:
        check = has_valid_url("url")
        assert check({"url": "https://example.com"}) is True
        assert check({"url": "ftp://example.com"}) is False
        assert check({}) is False

    def test_has_valid_score(self) -> None:
        check = has_valid_score()
        assert check({"score": 0.5}) is True
        assert check({"score": 1.5}) is False
        assert check({}) is True  # no score is ok


class TestSchemaValidator:
    def test_valid_item(self) -> None:
        validator = SchemaValidator()
        assert validator.is_valid({"id": "1", "title": "Test"}) is True

    def test_invalid_item(self) -> None:
        validator = SchemaValidator()
        assert validator.is_valid({"id": "1"}) is False

    def test_custom_schema(self) -> None:
        schema = ContentSchema(
            name="article",
            required_fields=["id", "title", "content"],
        )
        validator = SchemaValidator(schema=schema)
        assert validator.is_valid({"id": "1", "title": "T", "content": "C"}) is True
        assert validator.is_valid({"id": "1"}) is False

    def test_field_types(self) -> None:
        schema = ContentSchema(
            field_types={"score": float, "title": str},
        )
        validator = SchemaValidator(schema=schema)
        results = validator.validate({"id": "1", "title": "T", "score": "bad"})
        failed = [r for r in results if not r.passed]
        assert any("score" in r.rule_name for r in failed)

    def test_batch_validate(self) -> None:
        validator = SchemaValidator()
        items = [
            {"id": "1", "title": "A"},
            {"id": "2"},
        ]
        results = validator.validate_batch(items)
        assert "1" in results
        assert "2" in results


class TestQualityChecker:
    def test_perfect_quality(self) -> None:
        checker = QualityChecker()
        item = {
            "id": "1", "title": "Great Article",
            "content": "This is a long and detailed article content.",
            "tags": ["python"], "author": "Alice",
            "summary": "Summary here", "score": 0.9,
        }
        score = checker.check(item)
        assert score.overall == 1.0
        assert score.issues == []

    def test_poor_quality(self) -> None:
        checker = QualityChecker()
        item = {}
        score = checker.check(item)
        assert score.overall == 0.0
        assert len(score.issues) > 0

    def test_filter_by_quality(self) -> None:
        checker = QualityChecker()
        items = [
            {"id": "1", "title": "Good", "content": "Long content here"},
            {"id": "2"},
        ]
        filtered = checker.filter_by_quality(items, min_score=0.5)
        assert len(filtered) == 1
        assert filtered[0]["id"] == "1"

    def test_batch_check(self) -> None:
        checker = QualityChecker()
        items = [{"id": "1", "title": "A", "content": "B"}]
        results = checker.check_batch(items)
        assert len(results) == 1
        assert isinstance(results[0][1], QualityScore)
