"""Adversarial deep tests for personal_index.validator (URLValidator +
ContentValidator).

Cycle 146 - VALIDATOR probe.

Targets (never-probed subsystem in tests/deep/; the existing
test_content_validator_adversarial.py covers the *different* module
personal_index.content_validator package, not this file):
  - URLValidator.validate: "valid iff no errors were added" property,
    empty/whitespace/None guards, scheme case-insensitivity, blocked
    domain (exact + subdomain), blocked path prefix, fragment -> warning
    only (stays valid), out-of-range max_url_length.
  - URLValidator.validate_batch: idempotence, empty list, per-item results.
  - ContentValidator.validate: empty/None -> error, warnings never flip
    valid, mostly-whitespace -> error, link-ratio warning, unicode,
    out-of-range limits, "valid iff no errors" property.
  - End-to-end CLI run (installed entry point).
"""

from __future__ import annotations

import pytest

from personal_index.validator import (
    ContentValidator,
    URLValidator,
    ValidationResult,
)


# --- URLValidator.validate: guard inputs -----------------------------------

def test_none_url_is_invalid():
    v = URLValidator()
    r = v.validate(None)  # type: ignore[arg-type]
    assert r.valid is False
    assert r.errors


def test_empty_url_is_invalid():
    v = URLValidator()
    r = v.validate("")
    assert r.valid is False
    assert "URL is empty" in r.errors


def test_whitespace_url_is_invalid():
    v = URLValidator()
    r = v.validate("   \t\n  ")
    assert r.valid is False
    assert "URL is empty" in r.errors


def test_whitespace_is_stripped_before_checks():
    v = URLValidator()
    r = v.validate("  https://example.com/page  ")
    assert r.valid is True


# --- URLValidator.validate: scheme -----------------------------------------

def test_scheme_case_insensitive():
    v = URLValidator()
    assert v.validate("HTTP://example.com/").valid is True
    assert v.validate("HtTpS://example.com/").valid is True


def test_missing_scheme_invalid():
    v = URLValidator()
    r = v.validate("example.com/page")
    assert r.valid is False
    assert any("scheme" in e.lower() for e in r.errors)


def test_disallowed_scheme_invalid():
    v = URLValidator()
    r = v.validate("javascript:alert(1)")
    assert r.valid is False
    assert any("not allowed" in e for e in r.errors)


def test_custom_allowed_schemes():
    v = URLValidator(allowed_schemes={"ftp"})
    assert v.validate("ftp://example.com/x").valid is True
    assert v.validate("http://example.com/x").valid is False


# --- URLValidator.validate: domain -----------------------------------------

def test_missing_domain_invalid():
    v = URLValidator()
    r = v.validate("http://")
    assert r.valid is False
    assert any("domain" in e.lower() for e in r.errors)


def test_blocked_domain_exact():
    v = URLValidator(blocked_domains={"evil.com"})
    assert v.validate("http://evil.com/").valid is False


def test_blocked_domain_subdomain():
    v = URLValidator(blocked_domains={"evil.com"})
    assert v.validate("http://sub.evil.com/").valid is False
    assert v.validate("http://a.b.evil.com/").valid is False


def test_blocked_domain_case_insensitive():
    v = URLValidator(blocked_domains={"evil.com"})
    assert v.validate("http://EVIL.COM/").valid is False


def test_blocked_domain_suffix_not_blocked():
    v = URLValidator(blocked_domains={"evil.com"})
    # "not-evil.com" must NOT be treated as a subdomain of evil.com
    assert v.validate("http://not-evil.com/").valid is True


def test_domain_too_long_invalid():
    v = URLValidator()
    host = "a" * 254 + ".com"
    r = v.validate(f"http://{host}/")
    assert r.valid is False
    assert any("too long" in e for e in r.errors)


# --- URLValidator.validate: path + fragment --------------------------------

def test_blocked_path_prefix():
    v = URLValidator(blocked_paths=["/admin"])
    assert v.validate("http://example.com/admin").valid is False
    assert v.validate("http://example.com/admin/users").valid is False
    # non-prefix path is fine
    assert v.validate("http://example.com/management").valid is True


def test_fragment_is_warning_only_stays_valid():
    v = URLValidator()
    r = v.validate("http://example.com/page#section")
    assert r.valid is True
    assert r.errors == []
    assert any("fragment" in w.lower() for w in r.warnings)


# --- URLValidator.validate: length / out-of-range --------------------------

def test_max_length_boundary():
    v = URLValidator(max_url_length=10)
    # exactly 10 chars -> ok
    assert v.validate("http://a.b").valid is True
    # 11 chars -> error
    r = v.validate("http://a.bc")
    assert r.valid is False
    assert any("exceeds max length" in e for e in r.errors)


def test_zero_max_length_rejects_any_nonempty():
    v = URLValidator(max_url_length=0)
    assert v.validate("http://a.b").valid is False


# --- URLValidator.validate: "valid iff no errors" property -----------------

@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://example.com/a?b=1",
        "ftp://example.com/x",
        "http://example.com/#frag",
        "example.com",
        "javascript:alert(1)",
        "",
        "   ",
        "http://",
        "http://" + "a" * 300 + ".com/",
    ],
)
def test_valid_iff_no_errors_property(url):
    v = URLValidator(blocked_domains={"evil.com"}, blocked_paths=["/admin"])
    r = v.validate(url)
    assert r.valid == (len(r.errors) == 0)


# --- URLValidator.validate_batch -------------------------------------------

def test_validate_batch_empty():
    v = URLValidator()
    assert v.validate_batch([]) == []


def test_validate_batch_idempotent():
    v = URLValidator()
    urls = ["http://example.com", "bad", "https://x.com/#f"]
    first = v.validate_batch(urls)
    second = v.validate_batch(urls)
    assert [u for u, _ in first] == [u for u, _ in second]
    assert [r.valid for _, r in first] == [r.valid for _, r in second]


def test_validate_batch_preserves_order_and_results():
    v = URLValidator()
    out = v.validate_batch(["http://ok.com", "nope"])
    assert out[0][0] == "http://ok.com" and out[0][1].valid is True
    assert out[1][0] == "nope" and out[1][1].valid is False


# --- ContentValidator.validate: guards -------------------------------------

def test_content_none_invalid():
    cv = ContentValidator()
    r = cv.validate(None)  # type: ignore[arg-type]
    assert r.valid is False
    assert "Content is empty" in r.errors


def test_content_empty_invalid():
    cv = ContentValidator()
    r = cv.validate("")
    assert r.valid is False
    assert "Content is empty" in r.errors


def test_content_mostly_whitespace_invalid():
    cv = ContentValidator()
    r = cv.validate("   " * 100)
    assert r.valid is False
    assert any("whitespace" in e for e in r.errors)


def test_content_whitespace_only_short_invalid():
    cv = ContentValidator()
    r = cv.validate("   ")
    assert r.valid is False
    assert any("whitespace" in e for e in r.errors)


# --- ContentValidator.validate: warnings never flip valid ------------------

def test_short_content_warning_stays_valid():
    cv = ContentValidator(min_length=50, min_words=10)
    # 60 chars, 12 words, no links -> only "too short" is avoided; valid
    text = " ".join(["word"] * 12)  # 59 chars, 12 words
    r = cv.validate(text)
    assert r.valid is True
    assert r.errors == []


def test_warnings_do_not_change_valid():
    cv = ContentValidator(min_length=1000, min_words=100)
    text = "hello world " * 20  # 240 chars, 40 words
    r = cv.validate(text)
    # below min_length and min_words -> warnings, but no errors
    assert r.valid is True
    assert r.errors == []
    assert r.warnings


def test_too_many_links_warning_stays_valid():
    cv = ContentValidator(min_length=10, min_words=1)
    # 2 links, 2 words -> ratio 1.0 > 0.5 -> warning, still valid
    text = "http://a.com http://b.com"
    r = cv.validate(text)
    assert r.valid is True
    assert any("links" in w for w in r.warnings)


# --- ContentValidator.validate: unicode + out-of-range ---------------------

def test_content_unicode_length():
    cv = ContentValidator(min_length=5, min_words=1)
    r = cv.validate("héllo wörld ünïcode")
    assert r.valid is True


def test_content_zero_min_length():
    cv = ContentValidator(min_length=0, min_words=0)
    r = cv.validate("x")
    assert r.valid is True


def test_content_negative_limits_do_not_crash():
    cv = ContentValidator(min_length=-5, max_length=-1, min_words=-1)
    r = cv.validate("some content here")
    assert isinstance(r, ValidationResult)


# --- ContentValidator.validate: "valid iff no errors" property -------------

@pytest.mark.parametrize(
    "content",
    [
        "",
        "   ",
        "   " * 100,
        "a" * 60,
        " ".join(["word"] * 12),
        "http://a.com http://b.com",
        "héllo wörld ünïcode",
    ],
)
def test_content_valid_iff_no_errors_property(content):
    cv = ContentValidator(min_length=50, min_words=10)
    r = cv.validate(content)
    assert r.valid == (len(r.errors) == 0)


# --- ValidationResult: add_error / add_warning semantics -------------------

def test_add_error_flips_valid():
    r = ValidationResult(valid=True)
    r.add_error("boom")
    assert r.valid is False
    assert r.errors == ["boom"]


def test_add_warning_keeps_valid():
    r = ValidationResult(valid=True)
    r.add_warning("note")
    assert r.valid is True
    assert r.warnings == ["note"]
    assert r.errors == []


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_export(tmp_path):
    """End-to-end: init + export on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["export", "--format", "json", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "No indexed content to export." in r.output
