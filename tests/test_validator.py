"""Tests for URL and content validation."""

import pytest
from personal_index.validator import URLValidator, ContentValidator, ValidationResult


class TestValidationResult:
    def test_default_valid(self):
        result = ValidationResult(valid=True)
        assert result.valid is True
        assert result.errors == []

    def test_add_error(self):
        result = ValidationResult(valid=True)
        result.add_error("bad")
        assert result.valid is False
        assert "bad" in result.errors

    def test_add_warning(self):
        result = ValidationResult(valid=True)
        result.add_warning("caution")
        assert result.valid is True
        assert "caution" in result.warnings


class TestURLValidator:
    def test_valid_url(self):
        v = URLValidator()
        result = v.validate("http://example.com/page")
        assert result.valid is True

    def test_https_url(self):
        v = URLValidator()
        result = v.validate("https://example.com/path?q=1")
        assert result.valid is True

    def test_empty_url(self):
        v = URLValidator()
        result = v.validate("")
        assert result.valid is False

    def test_missing_scheme(self):
        v = URLValidator()
        result = v.validate("example.com/page")
        assert result.valid is False

    def test_blocked_scheme(self):
        v = URLValidator()
        result = v.validate("javascript:alert(1)")
        assert result.valid is False

    def test_blocked_domain(self):
        v = URLValidator(blocked_domains={"bad.com"})
        result = v.validate("http://bad.com/page")
        assert result.valid is False

    def test_blocked_subdomain(self):
        v = URLValidator(blocked_domains={"bad.com"})
        result = v.validate("http://sub.bad.com/page")
        assert result.valid is False

    def test_blocked_path(self):
        v = URLValidator(blocked_paths=["/admin"])
        result = v.validate("http://example.com/admin/settings")
        assert result.valid is False

    def test_url_too_long(self):
        v = URLValidator(max_url_length=20)
        result = v.validate("http://example.com/" + "a" * 100)
        assert result.valid is False

    def test_fragment_warning(self):
        v = URLValidator()
        result = v.validate("http://example.com/page#section")
        assert result.valid is True
        assert len(result.warnings) > 0

    def test_validate_batch(self):
        v = URLValidator()
        results = v.validate_batch([
            "http://good.com",
            "bad-url",
            "https://also-good.com",
        ])
        assert len(results) == 3
        assert results[0][1].valid is True
        assert results[1][1].valid is False
        assert results[2][1].valid is True

    def test_missing_domain(self):
        v = URLValidator()
        result = v.validate("http:///path")
        assert result.valid is False


class TestContentValidator:
    def test_valid_content(self):
        v = ContentValidator()
        content = "This is a valid piece of content with enough words to pass validation."
        result = v.validate(content)
        assert result.valid is True

    def test_empty_content(self):
        v = ContentValidator()
        result = v.validate("")
        assert result.valid is False

    def test_short_content_warning(self):
        v = ContentValidator(min_length=100)
        result = v.validate("Short")
        assert result.valid is True
        assert len(result.warnings) > 0

    def test_few_words_warning(self):
        v = ContentValidator(min_words=20)
        result = v.validate("One two three four five")
        assert len(result.warnings) > 0

    def test_mostly_whitespace(self):
        v = ContentValidator()
        content = "a" + " " * 1000
        result = v.validate(content)
        assert result.valid is False

    def test_too_many_links(self):
        v = ContentValidator()
        content = "http://a.com http://b.com http://c.com http://d.com http://e.com"
        result = v.validate(content)
        assert len(result.warnings) > 0

    def test_very_long_content_warning(self):
        v = ContentValidator(max_length=100)
        content = "word " * 200
        result = v.validate(content)
        assert any("long" in w.lower() for w in result.warnings)


def test_validator_module_docstring_and_imports():
    """Verify module has proper docstring before imports (E402 fix)."""
    import personal_index.validator as mod
    assert mod.__doc__ == "URL and content validation utilities."
    # Verify the module imports correctly without E402 issues
    assert hasattr(mod, "URLValidator")
    assert hasattr(mod, "ContentValidator")
