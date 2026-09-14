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

from personal_index.content_validation import ContentValidator


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
