"""Adversarial deep tests for personal_index/validator.py.

Cycle 289 — first deep-probe of the never-probed module `validator`
(178 lines: `ValidationResult` dataclass with add_error/add_warning,
`URLValidator` with validate/validate_batch and length/scheme/domain/path/
fragment checks, `ContentValidator` with validate and length/word-count/link-
ratio/whitespace checks).

Covers the documented contracts:
  - URLValidator.validate: empty/whitespace -> "URL is empty"; length, scheme,
    domain, path, fragment checks; valid iff no errors added.
  - URLValidator.validate_batch: per-URL results.
  - ContentValidator.validate: empty -> "Content is empty"; soft warnings for
    short/long/few-words/too-many-links; error for mostly-whitespace.
  - ValidationResult.add_error flips valid False; add_warning does not.

Plus: None/empty/whitespace/unicode/oversized/boundary inputs, idempotence,
error paths, and an end-to-end programmatic run through the public API.

Two REAL contract violations surfaced and are pinned with xfail-strict
(documented, not hard-failed, so main stays green):
  - QA-50 (issue #1633): URLValidator.validate crashes (AttributeError) on
    non-string input (int/float/list) — the docstring/contract implies a
    robust validator but `url.strip()` is called on the raw value.
  - QA-51 (issue #1634): ContentValidator._is_mostly_whitespace only counts
    SPACE characters, so tab/newline-heavy content that is effectively
    whitespace is NOT flagged as an error.
"""

from __future__ import annotations

import pytest

from personal_index.validator import (
    ContentValidator,
    URLValidator,
    ValidationResult,
)


# ---------------------------------------------------------------------------
# ValidationResult dataclass


class TestValidationResult:
    def test_defaults_valid_no_errors_no_warnings(self):
        r = ValidationResult(valid=True)
        assert r.valid is True
        assert r.errors == []
        assert r.warnings == []

    def test_add_error_flips_valid_false_and_appends(self):
        r = ValidationResult(valid=True)
        r.add_error("boom")
        assert r.valid is False
        assert r.errors == ["boom"]

    def test_add_warning_does_not_change_valid(self):
        r = ValidationResult(valid=True)
        r.add_warning("soft")
        assert r.valid is True
        assert r.warnings == ["soft"]
        assert r.errors == []

    def test_add_error_idempotent_accumulates(self):
        r = ValidationResult(valid=True)
        r.add_error("a")
        r.add_error("b")
        assert r.valid is False
        assert r.errors == ["a", "b"]

    def test_independent_instances(self):
        a = ValidationResult(valid=True)
        b = ValidationResult(valid=True)
        a.add_error("x")
        assert b.valid is True
        assert b.errors == []


# ---------------------------------------------------------------------------
# URLValidator — happy path / documented contract


class TestURLValidatorHappy:
    def test_valid_http(self):
        r = URLValidator().validate("http://example.com/path")
        assert r.valid is True
        assert r.errors == []

    def test_valid_https(self):
        r = URLValidator().validate("https://example.com")
        assert r.valid is True

    def test_valid_ftp(self):
        r = URLValidator().validate("ftp://example.com/file")
        assert r.valid is True

    def test_valid_ftps(self):
        r = URLValidator().validate("ftps://example.com/file")
        assert r.valid is True

    def test_fragment_is_warning_not_error(self):
        r = URLValidator().validate("https://example.com/page#section")
        assert r.valid is True
        assert r.errors == []
        assert any("fragment" in w for w in r.warnings)

    def test_whitespace_stripped_before_validation(self):
        r = URLValidator().validate("  https://example.com  ")
        assert r.valid is True


class TestURLValidatorEmpty:
    def test_empty_string(self):
        r = URLValidator().validate("")
        assert r.valid is False
        assert r.errors == ["URL is empty"]

    def test_whitespace_only(self):
        r = URLValidator().validate("   \t  ")
        assert r.valid is False
        assert r.errors == ["URL is empty"]

    def test_none_is_empty(self):
        r = URLValidator().validate(None)
        assert r.valid is False
        assert r.errors == ["URL is empty"]


class TestURLValidatorScheme:
    def test_missing_scheme(self):
        r = URLValidator().validate("example.com/path")
        assert r.valid is False
        assert any("scheme" in e for e in r.errors)

    def test_disallowed_scheme(self):
        r = URLValidator().validate("javascript:alert(1)")
        assert r.valid is False
        assert any("not allowed" in e for e in r.errors)

    def test_scheme_case_insensitive(self):
        r = URLValidator().validate("HTTPS://example.com")
        assert r.valid is True

    def test_custom_allowed_schemes(self):
        v = URLValidator(allowed_schemes={"file"})
        assert v.validate("file://localhost/etc/hosts").valid is True
        assert v.validate("http://example.com").valid is False


class TestURLValidatorDomain:
    def test_missing_domain(self):
        r = URLValidator().validate("http://")
        assert r.valid is False
        assert any("domain" in e for e in r.errors)

    def test_domain_too_long(self):
        long_domain = "a" * 254
        r = URLValidator().validate(f"http://{long_domain}/")
        assert r.valid is False
        assert any("too long" in e for e in r.errors)

    def test_domain_at_max_length_ok(self):
        domain = "a" * 253
        r = URLValidator().validate(f"http://{domain}/")
        assert r.valid is True

    def test_blocked_domain_exact(self):
        v = URLValidator(blocked_domains={"bad.com"})
        assert v.validate("http://bad.com/").valid is False

    def test_blocked_domain_subdomain(self):
        v = URLValidator(blocked_domains={"bad.com"})
        assert v.validate("http://sub.bad.com/").valid is False

    def test_blocked_domain_case_insensitive(self):
        v = URLValidator(blocked_domains={"bad.com"})
        assert v.validate("http://BAD.COM/").valid is False

    def test_blocked_domain_trailing_dot(self):
        v = URLValidator(blocked_domains={"bad.com"})
        assert v.validate("http://bad.com./").valid is False

    def test_unblocked_similar_domain(self):
        v = URLValidator(blocked_domains={"bad.com"})
        assert v.validate("http://notbad.com/").valid is True


class TestURLValidatorPath:
    def test_blocked_path(self):
        v = URLValidator(blocked_paths=["/admin"])
        assert v.validate("http://example.com/admin").valid is False

    def test_blocked_path_case_insensitive(self):
        v = URLValidator(blocked_paths=["/admin"])
        assert v.validate("http://example.com/ADMIN").valid is False

    def test_unblocked_path(self):
        v = URLValidator(blocked_paths=["/admin"])
        assert v.validate("http://example.com/public").valid is True


class TestURLValidatorLength:
    def test_url_at_max_length_ok(self):
        v = URLValidator(max_url_length=20)
        url = "http://a" + "b" * 8 + ".com"  # exactly 20 chars
        assert len(url) == 20
        assert v.validate(url).valid is True

    def test_url_over_max_length(self):
        v = URLValidator(max_url_length=20)
        url = "http://a" + "b" * 9 + ".com"  # 21 chars
        r = v.validate(url)
        assert r.valid is False
        assert any("exceeds max length" in e for e in r.errors)


class TestURLValidatorBatch:
    def test_batch_mixed(self):
        v = URLValidator()
        results = v.validate_batch(["https://ok.com", "", "bad"])
        assert len(results) == 3
        assert results[0][1].valid is True
        assert results[1][1].valid is False
        assert results[2][1].valid is False

    def test_batch_empty(self):
        assert URLValidator().validate_batch([]) == []


# ---------------------------------------------------------------------------
# URLValidator — REAL DEFECT: non-string input crashes (QA-50)


class TestURLValidatorNonString:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-50: URLValidator.validate crashes (AttributeError) on "
        "non-string input; contract implies robust validation",
    )
    def test_int_input_does_not_crash(self):
        URLValidator().validate(123)

    @pytest.mark.xfail(
        strict=True,
        reason="QA-50: URLValidator.validate crashes (AttributeError) on "
        "non-string input",
    )
    def test_float_input_does_not_crash(self):
        URLValidator().validate(3.14)

    @pytest.mark.xfail(
        strict=True,
        reason="QA-50: URLValidator.validate crashes (AttributeError) on "
        "non-string input",
    )
    def test_list_input_does_not_crash(self):
        URLValidator().validate(["a"])


# ---------------------------------------------------------------------------
# ContentValidator — happy path / documented contract


class TestContentValidatorHappy:
    def test_valid_content(self):
        content = "This is a perfectly fine piece of content with enough words."
        r = ContentValidator().validate(content)
        assert r.valid is True
        assert r.errors == []

    def test_empty_content(self):
        r = ContentValidator().validate("")
        assert r.valid is False
        assert r.errors == ["Content is empty"]

    def test_none_content(self):
        r = ContentValidator().validate(None)
        assert r.valid is False
        assert r.errors == ["Content is empty"]


class TestContentValidatorWarnings:
    def test_too_short_warning(self):
        r = ContentValidator().validate("short")
        assert r.valid is True
        assert any("too short" in w for w in r.warnings)

    def test_too_few_words_warning(self):
        r = ContentValidator().validate("one two three four five six seven eight nine")
        assert r.valid is True
        assert any("few words" in w for w in r.warnings)

    def test_too_many_links_warning(self):
        content = " ".join(["http://x"] * 10)
        r = ContentValidator().validate(content)
        assert r.valid is True
        assert any("too many links" in w for w in r.warnings)

    def test_custom_min_length(self):
        v = ContentValidator(min_length=1000)
        r = v.validate("short")
        assert any("too short" in w for w in r.warnings)


class TestContentValidatorWhitespace:
    def test_mostly_whitespace_space(self):
        r = ContentValidator().validate("a" + " " * 200)
        assert r.valid is False
        assert any("mostly whitespace" in e for e in r.errors)

    def test_all_whitespace(self):
        r = ContentValidator().validate("   \n\t  ")
        assert r.valid is False
        assert any("mostly whitespace" in e for e in r.errors)


# ---------------------------------------------------------------------------
# ContentValidator — REAL DEFECT: tab/newline whitespace not flagged (QA-51)


class TestContentValidatorTabWhitespace:
    @pytest.mark.xfail(
        strict=True,
        reason="QA-51: ContentValidator._is_mostly_whitespace only counts "
        "spaces, so tab-heavy content that is effectively whitespace is not "
        "flagged as an error",
    )
    def test_tab_heavy_content_flagged(self):
        r = ContentValidator().validate("a" + "\t" * 200)
        assert r.valid is False
        assert any("mostly whitespace" in e for e in r.errors)

    @pytest.mark.xfail(
        strict=True,
        reason="QA-51: ContentValidator._is_mostly_whitespace only counts "
        "spaces, so newline-heavy content that is effectively whitespace is "
        "not flagged as an error",
    )
    def test_newline_heavy_content_flagged(self):
        r = ContentValidator().validate("a" + "\n" * 200)
        assert r.valid is False
        assert any("mostly whitespace" in e for e in r.errors)


# ---------------------------------------------------------------------------
# End-to-end programmatic run through the public API


class TestEndToEnd:
    def test_full_url_pipeline(self):
        v = URLValidator(
            allowed_schemes={"http", "https"},
            blocked_domains={"internal.corp"},
            blocked_paths=["/private"],
            max_url_length=2048,
        )
        urls = [
            "https://public.example.com/article",
            "http://internal.corp/secret",
            "https://public.example.com/private",
            "",
            "ftp://example.com/file",
        ]
        results = v.validate_batch(urls)
        assert results[0][1].valid is True
        assert results[1][1].valid is False
        assert results[2][1].valid is False
        assert results[3][1].valid is False
        assert results[4][1].valid is False

    def test_full_content_pipeline(self):
        c = ContentValidator(min_length=50, min_words=10)
        good = "This is a well-formed paragraph with plenty of words to pass."
        bad = "x"
        assert c.validate(good).valid is True
        assert c.validate(bad).valid is True  # short -> warning, not error
        assert c.validate("").valid is False
