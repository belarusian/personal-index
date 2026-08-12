"""Tests for the content validation module."""

from datetime import datetime, timezone

from personal_index.content_validation import (
    ContentValidator,
    ValidationError,
    ValidationResult,
)


class TestValidationError:
    def test_create(self) -> None:
        error = ValidationError(
            field="url",
            message="Invalid URL",
            severity="error",
        )
        assert error.severity == "error"


class TestValidationResult:
    def test_create(self) -> None:
        result = ValidationResult()
        assert result.is_valid is True
        assert len(result.errors) == 0

    def test_add_error(self) -> None:
        result = ValidationResult()
        result.add_error("url", "Invalid URL")
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_add_warning(self) -> None:
        result = ValidationResult()
        result.add_warning("title", "Too long")
        assert result.is_valid is True
        assert len(result.warnings) == 1

    def test_to_dict(self) -> None:
        result = ValidationResult()
        result.add_error("url", "Invalid")
        d = result.to_dict()
        assert d["is_valid"] is False
        assert d["error_count"] == 1


class TestContentValidator:
    def setup_method(self) -> None:
        self.validator = ContentValidator()

    def test_valid_item(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.validator.validate([item])
        assert result.is_valid is True
        assert result.items_valid == 1

    def test_missing_required_field(self) -> None:
        item = {"id": "1"}  # Missing url
        result = self.validator.validate([item])
        assert result.is_valid is False
        assert len(result.errors) == 1

    def test_invalid_url(self) -> None:
        item = {"id": "1", "url": "not-a-url"}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_url_too_long(self) -> None:
        item = {"id": "1", "url": "https://" + "a" * 2049}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_title_too_long(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "title": "x" * 501,
        }
        result = self.validator.validate([item])
        assert result.is_valid is True  # Warning, not error
        assert len(result.warnings) == 1

    def test_invalid_score_type(self) -> None:
        item = {"id": "1", "url": "https://example.com", "score": "high"}
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_score_out_of_range(self) -> None:
        item = {"id": "1", "url": "https://example.com", "score": 1.5}
        result = self.validator.validate([item])
        assert result.is_valid is True  # Warning
        assert len(result.warnings) == 1

    def test_invalid_date(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": "not-a-date",
        }
        result = self.validator.validate([item])
        assert result.is_valid is False

    def test_valid_date_string(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": "2024-01-01T00:00:00",
        }
        result = self.validator.validate([item])
        assert result.is_valid is True

    def test_valid_date_object(self) -> None:
        item = {
            "id": "1",
            "url": "https://example.com",
            "published_at": datetime(2024, 1, 1, tzinfo=timezone.utc),
        }
        result = self.validator.validate([item])
        assert result.is_valid is True

    def test_custom_required_fields(self) -> None:
        validator = ContentValidator(
            required_fields=["id", "url", "title"],
        )
        item = {"id": "1", "url": "https://example.com"}
        result = validator.validate([item])
        assert result.is_valid is False

    def test_multiple_items(self) -> None:
        items = [
            {"id": "1", "url": "https://example.com"},
            {"id": "2"},  # Missing url
            {"id": "3", "url": "https://example.com"},
        ]
        result = self.validator.validate(items)
        assert result.items_valid == 2
        assert result.items_invalid == 1

    def test_validate_single(self) -> None:
        item = {"id": "1", "url": "https://example.com"}
        result = self.validator.validate_single(item)
        assert result.is_valid is True
