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


class TestContentValidatorDocstring:
    def test_docstring_does_not_promise_custom_rules(self) -> None:
        """Regression: class docstring must not over-promise capabilities.

        ContentValidator runs a fixed set of built-in checks (required
        fields, URL, title, score, dates) and exposes no custom-rule API
        (no add_rule/register/callback/predicate), so its docstring must
        not claim to support 'custom rules' (TICKET-330).
        """
        doc = (ContentValidator.__doc__ or "").lower()
        assert "custom rules" not in doc


class TestValidateDocstringDefaults:
    """TICKET-445: pin the corrected validate docstring against the returned
    ValidationResult object. The docstring now enumerates the per-item checks,
    the warning-vs-error distinction, the items_valid/items_invalid tally, and
    the returned fields. Witness both the normal case (all-valid item) and the
    guard path (a title-length breach is a WARNING that leaves the item valid,
    vs a required-field breach that marks it invalid)."""

    def test_validate_all_valid_pins_returned_fields(self) -> None:
        """A fully-valid item is tallied valid with no errors/warnings and the
        returned ValidationResult carries is_valid/items_valid/items_invalid."""
        validator = ContentValidator()
        result = validator.validate([{"id": "1", "url": "https://example.com"}])
        assert result.is_valid is True
        assert result.errors == []
        assert result.warnings == []
        assert result.items_valid == 1
        assert result.items_invalid == 0

    def test_validate_title_breach_is_warning_not_invalid(self) -> None:
        """Guard path: a title-length breach is a WARNING (does not mark the
        item invalid), while a missing required field is an ERROR (marks the
        item invalid) - one returned object pins both distinctions."""
        validator = ContentValidator()
        # title breach -> warning, item still valid
        warn_result = validator.validate(
            [{"id": "1", "url": "https://example.com", "title": "x" * 501}]
        )
        assert warn_result.is_valid is True
        assert warn_result.items_valid == 1
        assert warn_result.items_invalid == 0
        assert len(warn_result.warnings) == 1
        assert warn_result.errors == []
        # required-field breach -> error, item invalid
        err_result = validator.validate([{"id": "1"}])
        assert err_result.is_valid is False
        assert err_result.items_valid == 0
        assert err_result.items_invalid == 1
        assert len(err_result.errors) == 1
        assert err_result.warnings == []


class TestValidationResultToDictPinning:
    """Pin ValidationResult.to_dict keys, derived counts, and errors projection."""

    def test_to_dict_pins_keys_and_projection(self):
        from personal_index.content_validation import ValidationResult

        result = ValidationResult()
        result.add_error("item[0].url", "Invalid URL: bad", value="bad")
        result.add_warning("item[0].title", "Title too long")

        d = result.to_dict()

        # exactly 6 keys
        assert set(d.keys()) == {
            "is_valid", "error_count", "warning_count",
            "items_valid", "items_invalid", "errors",
        }
        # derived counts
        assert d["error_count"] == 1
        assert d["warning_count"] == 1
        # is_valid is False (add_error set it)
        assert d["is_valid"] is False
        # items tallies
        assert d["items_valid"] == 0
        assert d["items_invalid"] == 0
        # errors is a projected list of {field, message} — no severity/value
        assert d["errors"] == [
            {"field": "item[0].url", "message": "Invalid URL: bad"},
        ]
        assert "severity" not in d["errors"][0]
        assert "value" not in d["errors"][0]
        # warnings list is NOT in the output
        assert "warnings" not in d

    def test_to_dict_guard_path_empty_result(self):
        from personal_index.content_validation import ValidationResult

        result = ValidationResult()
        d = result.to_dict()

        assert d["is_valid"] is True
        assert d["error_count"] == 0
        assert d["warning_count"] == 0
        assert d["items_valid"] == 0
        assert d["items_invalid"] == 0
        assert d["errors"] == []
        assert "warnings" not in d
