"""Adversarial deep tests for personal_index.content_validation.ContentValidator.

Cycle 217 - VALIDATOR VERIFY of ARCH-51.

ARCH-51 (docs/content-validation.md, "Contract Holes"): `_is_valid_url` was a
naive scheme-prefix check that accepted any string beginning with `http://`
or `https://` regardless of whether a host is present. The fix (PR #1318,
commit 7c9bf86) requires a non-empty host: `urlparse(url).netloc.strip()` must
be truthy.

This file pins the corrected contract:
  - valid http/https URLs WITH a host pass;
  - no-host cases `http://`, `https://`, `http:// ` (trailing space) are
    REJECTED (the exact cases named in the ticket);
  - adversarial no-host / whitespace-netloc / query-only inputs the contract
    implies are also rejected.

The public entry points are `validate` (list) and `validate_single` (dict);
`_is_valid_url` is pinned directly as the private helper the contract names.
"""

from __future__ import annotations

import pytest

from click.testing import CliRunner

from personal_index.cli import main as cli_main
from personal_index.content_validation import ContentValidator, ValidationResult


@pytest.fixture
def validator() -> ContentValidator:
    return ContentValidator()


# --- _is_valid_url: the private helper the contract names ------------------


def test_valid_http_with_host_passes(validator: ContentValidator) -> None:
    assert validator._is_valid_url("http://example.com") is True


def test_valid_https_with_host_and_path_passes(validator: ContentValidator) -> None:
    assert validator._is_valid_url("https://example.com/path?q=1") is True


def test_http_no_host_rejected(validator: ContentValidator) -> None:
    # Exact ticket case: scheme prefix, empty netloc.
    assert validator._is_valid_url("http://") is False


def test_https_no_host_rejected(validator: ContentValidator) -> None:
    # Exact ticket case: scheme prefix, empty netloc.
    assert validator._is_valid_url("https://") is False


def test_http_trailing_space_no_host_rejected(validator: ContentValidator) -> None:
    # Exact ticket case: netloc is a single space -> strip() -> empty.
    assert validator._is_valid_url("http:// ") is False


# --- adversarial no-host / whitespace-netloc inputs the contract implies ---


def test_http_multiple_spaces_no_host_rejected(validator: ContentValidator) -> None:
    # netloc is all whitespace -> strip() -> empty -> rejected.
    assert validator._is_valid_url("http://   ") is False


def test_https_query_only_no_host_rejected(validator: ContentValidator) -> None:
    # `https://?x=1` has an empty netloc (the `?` starts the query).
    assert validator._is_valid_url("https://?x=1") is False


def test_http_fragment_only_no_host_rejected(validator: ContentValidator) -> None:
    # `http://#frag` has an empty netloc (the `#` starts the fragment).
    assert validator._is_valid_url("http://#frag") is False


def test_http_path_only_no_host_rejected(validator: ContentValidator) -> None:
    # `http:///path` -> netloc empty, path `/path`.
    assert validator._is_valid_url("http:///path") is False


def test_empty_string_rejected(validator: ContentValidator) -> None:
    assert validator._is_valid_url("") is False


def test_non_http_scheme_rejected(validator: ContentValidator) -> None:
    # ftp:// has a host but a disallowed scheme -> still rejected.
    assert validator._is_valid_url("ftp://example.com") is False


def test_non_string_input_rejected(validator: ContentValidator) -> None:
    # Contract: `(url: str) -> bool`; a non-str must not crash and must be False.
    assert validator._is_valid_url(None) is False  # type: ignore[arg-type]


# --- public entry points: validate / validate_single -----------------------


def test_validate_single_no_host_url_invalid(validator: ContentValidator) -> None:
    result = validator.validate_single({"id": "1", "url": "http://"})
    assert result.is_valid is False
    assert result.items_invalid == 1
    assert result.items_valid == 0
    assert any("Invalid URL" in e.message for e in result.errors)


def test_validate_single_trailing_space_no_host_invalid(validator: ContentValidator) -> None:
    result = validator.validate_single({"id": "1", "url": "http:// "})
    assert result.is_valid is False
    assert any("Invalid URL" in e.message for e in result.errors)


def test_validate_single_valid_url_passes(validator: ContentValidator) -> None:
    result = validator.validate_single({"id": "1", "url": "https://example.com/a"})
    assert result.is_valid is True
    assert result.items_valid == 1
    assert result.items_invalid == 0
    assert result.errors == []


def test_validate_batch_mixed(validator: ContentValidator) -> None:
    items = [
        {"id": "1", "url": "https://good.example.com"},
        {"id": "2", "url": "http://"},
        {"id": "3", "url": "https://?x=1"},
    ]
    result = validator.validate(items)
    assert result.is_valid is False
    assert result.items_valid == 1
    assert result.items_invalid == 2
    # Both no-host items produce an Invalid URL error.
    url_errors = [e for e in result.errors if "Invalid URL" in e.message]
    assert len(url_errors) == 2


def test_validate_empty_list_is_valid(validator: ContentValidator) -> None:
    result = validator.validate([])
    assert result.is_valid is True
    assert result.items_valid == 0
    assert result.items_invalid == 0


# ============================================================================
# Cycle 365 - VALIDATOR PROBE: additional adversarial edge cases
#
# The 17 pins above only exercise URL validation (ARCH-51). This section
# attacks the rest of the public API the module documents but the prior
# probe never touched: ValidationResult (add_error/add_warning/to_dict),
# _check_required_fields, _validate_title (warning boundary), _validate_score
# (None / non-numeric / out-of-range), _validate_dates, _is_valid_date, and
# the max_url_length boundary. All pins are regression armor (must PASS).
# ============================================================================



class TestValidationResult:
    """ValidationResult dataclass: add_error/add_warning/to_dict contract."""

    def test_to_dict_has_exactly_six_keys(self) -> None:
        r = ValidationResult()
        assert sorted(r.to_dict().keys()) == [
            "error_count",
            "errors",
            "is_valid",
            "items_invalid",
            "items_valid",
            "warning_count",
        ]

    def test_add_error_flips_is_valid_and_defaults_severity(self) -> None:
        r = ValidationResult()
        r.add_error("item[0].url", "Invalid URL: http://", value="http://")
        assert r.is_valid is False
        assert len(r.errors) == 1
        assert r.errors[0].severity == "error"
        assert r.errors[0].value == "http://"

    def test_add_warning_keeps_is_valid_true(self) -> None:
        r = ValidationResult()
        r.add_warning("item[0].title", "Title exceeds recommended length")
        assert r.is_valid is True
        assert len(r.warnings) == 1
        assert r.warnings[0].severity == "warning"

    def test_to_dict_projects_errors_drops_severity_and_value(self) -> None:
        r = ValidationResult()
        r.add_error("item[0].url", "Invalid URL: http://", value="http://")
        d = r.to_dict()
        assert d["error_count"] == 1
        assert d["warning_count"] == 0
        # errors projected to {field, message} only - severity/value dropped.
        assert d["errors"] == [{"field": "item[0].url", "message": "Invalid URL: http://"}]
        # warnings list is NOT in the output (only its count).
        assert "warnings" not in d

    def test_to_dict_counts_derive_from_lists(self) -> None:
        r = ValidationResult()
        r.add_error("a", "m1")
        r.add_error("b", "m2")
        r.add_warning("c", "w1")
        d = r.to_dict()
        assert d["error_count"] == 2
        assert d["warning_count"] == 1
        assert d["is_valid"] is False


class TestRequiredFields:
    """_check_required_fields: default + custom required-field sets."""

    def test_empty_dict_missing_default_required_fields(self, validator: ContentValidator) -> None:
        r = validator.validate_single({})
        assert r.is_valid is False
        fields = {e.field for e in r.errors}
        # default required_fields = ["id", "url"] -> both flagged.
        assert "item[0].id" in fields
        assert "item[0].url" in fields

    def test_default_required_fields_are_id_and_url(self, validator: ContentValidator) -> None:
        assert validator.required_fields == ["id", "url"]

    def test_custom_required_fields_respected(self) -> None:
        v = ContentValidator(required_fields=["id", "url", "title"])
        r = v.validate_single({"id": "1", "url": "https://x.example.com"})
        assert r.is_valid is False
        assert any("title" in e.field for e in r.errors)
        # With the title present it passes.
        r2 = v.validate_single({"id": "1", "url": "https://x.example.com", "title": "t"})
        assert r2.is_valid is True

    def test_none_required_fields_falls_back_to_default(self) -> None:
        v = ContentValidator(required_fields=None)
        assert v.required_fields == ["id", "url"]


class TestTitleBoundary:
    """_validate_title: a length breach is a WARNING, never invalid."""

    def test_title_at_max_length_no_warning(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "title": "a" * 500})
        assert r.is_valid is True
        assert len(r.warnings) == 0

    def test_title_over_max_length_warning_not_invalid(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "title": "a" * 501})
        # A title-length breach is a warning; the item stays valid.
        assert r.is_valid is True
        assert len(r.warnings) == 1
        assert "title" in r.warnings[0].field

    def test_empty_title_no_warning(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "title": ""})
        assert r.is_valid is True
        assert len(r.warnings) == 0


class TestScoreValidation:
    """_validate_score: None skipped, non-numeric error, out-of-range warning."""

    def test_score_none_is_skipped_and_valid(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "score": None})
        assert r.is_valid is True
        assert len(r.errors) == 0
        assert len(r.warnings) == 0

    def test_score_non_numeric_is_error(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "score": "abc"})
        assert r.is_valid is False
        assert any("Score must be a number" in e.message for e in r.errors)

    def test_score_out_of_range_is_warning_not_invalid(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "score": 5.0})
        # Out-of-range score is a warning; the item stays valid.
        assert r.is_valid is True
        assert len(r.warnings) == 1
        assert "score" in r.warnings[0].field

    def test_score_boundaries_zero_and_one_are_valid(self, validator: ContentValidator) -> None:
        for s in (0.0, 1.0):
            r = validator.validate_single({"id": "1", "url": "https://x.example.com", "score": s})
            assert r.is_valid is True
            assert len(r.warnings) == 0


class TestDateValidation:
    """_validate_dates / _is_valid_date: ISO strings, datetime, and rejects."""

    def test_invalid_date_string_is_error(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "published_at": "not-a-date"})
        assert r.is_valid is False
        assert any("Invalid date format" in e.message for e in r.errors)

    def test_valid_iso_date_string_is_valid(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "published_at": "2024-01-01"})
        assert r.is_valid is True

    def test_empty_date_string_is_skipped(self, validator: ContentValidator) -> None:
        r = validator.validate_single({"id": "1", "url": "https://x.example.com", "published_at": ""})
        assert r.is_valid is True

    def test_is_valid_date_rejects_int(self, validator: ContentValidator) -> None:
        assert validator._is_valid_date(12345) is False

    def test_is_valid_date_rejects_empty_string(self, validator: ContentValidator) -> None:
        assert validator._is_valid_date("") is False


class TestUrlLengthBoundary:
    """_validate_url: max_url_length boundary (default 2048)."""

    def test_url_at_max_length_is_valid(self, validator: ContentValidator) -> None:
        url = "http://" + "a" * 2041  # len == 2048
        assert len(url) == 2048
        r = validator.validate_single({"id": "1", "url": url})
        assert r.is_valid is True

    def test_url_over_max_length_is_error(self, validator: ContentValidator) -> None:
        url = "http://" + "a" * 2042  # len == 2049
        assert len(url) == 2049
        r = validator.validate_single({"id": "1", "url": url})
        assert r.is_valid is False
        assert any("exceeds max length" in e.message for e in r.errors)


class TestCliEndToEnd:
    """End-to-end CLI smoke: the installed CLI entry point runs and exits 0."""

    def test_cli_main_help_exits_zero(self) -> None:
        runner = CliRunner()
        res = runner.invoke(cli_main, ["--help"])
        assert res.exit_code == 0
        # The group advertises its subcommands.
        assert "Usage" in res.output
