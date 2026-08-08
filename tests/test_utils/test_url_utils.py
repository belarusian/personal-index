"""Tests for URL utility functions."""

import pytest

from personal_index.utils.url_utils import (
    is_valid_url,
    normalize_url,
    resolve_relative_url,
    extract_domain,
    is_excluded_url,
    get_url_depth,
    is_same_domain,
)


class TestIsValidUrl:
    def test_valid_http(self):
        assert is_valid_url("http://example.com")

    def test_valid_https(self):
        assert is_valid_url("https://example.com/path")

    def test_invalid_no_scheme(self):
        assert not is_valid_url("example.com")

    def test_invalid_no_netloc(self):
        assert not is_valid_url("http://")

    def test_invalid_scheme(self):
        assert not is_valid_url("ftp://example.com")

    def test_empty_string(self):
        assert not is_valid_url("")


class TestNormalizeUrl:
    def test_removes_fragment(self):
        result = normalize_url("https://example.com/page#section")
        assert "#section" not in result

    def test_removes_trailing_slash(self):
        result = normalize_url("https://example.com/path/")
        assert result == "https://example.com/path"

    def test_lowercases_domain(self):
        result = normalize_url("https://Example.COM/path")
        assert "example.com" in result

    def test_preserves_query(self):
        result = normalize_url("https://example.com/path?q=1")
        assert "q=1" in result

    def test_root_path(self):
        result = normalize_url("https://example.com/")
        assert result == "https://example.com/"


class TestResolveRelativeUrl:
    def test_absolute_url(self):
        result = resolve_relative_url("https://example.com", "/page")
        assert result == "https://example.com/page"

    def test_relative_path(self):
        result = resolve_relative_url("https://example.com/dir/", "page.html")
        assert result == "https://example.com/dir/page.html"

    def test_parent_directory(self):
        result = resolve_relative_url("https://example.com/dir/page", "../other")
        assert result == "https://example.com/other"

    def test_invalid_url(self):
        result = resolve_relative_url("https://example.com", "javascript:void(0)")
        assert result is None

    def test_external_url(self):
        result = resolve_relative_url("https://example.com", "https://other.com/page")
        assert result == "https://other.com/page"


class TestExtractDomain:
    def test_http(self):
        assert extract_domain("http://example.com/path") == "example.com"

    def test_https(self):
        assert extract_domain("https://example.com") == "example.com"

    def test_with_port(self):
        assert extract_domain("https://example.com:8080") == "example.com:8080"

    def test_subdomain(self):
        assert extract_domain("https://blog.example.com") == "blog.example.com"

    def test_invalid(self):
        assert extract_domain("not-a-url") is None


class TestIsExcludedUrl:
    def test_css_excluded(self):
        assert is_excluded_url("https://example.com/style.css")

    def test_js_excluded(self):
        assert is_excluded_url("https://example.com/app.js")

    def test_image_excluded(self):
        assert is_excluded_url("https://example.com/photo.png")

    def test_pdf_excluded(self):
        assert is_excluded_url("https://example.com/doc.pdf")

    def test_html_not_excluded(self):
        assert not is_excluded_url("https://example.com/page.html")

    def test_javascript_scheme(self):
        assert is_excluded_url("javascript:void(0)")

    def test_mailto_scheme(self):
        assert is_excluded_url("mailto:test@example.com")

    def test_data_scheme(self):
        assert is_excluded_url("data:text/html,<h1>test</h1>")

    def test_normal_page(self):
        assert not is_excluded_url("https://example.com/blog/post")


class TestGetUrlDepth:
    def test_root(self):
        assert get_url_depth("https://example.com") == 0

    def test_one_level(self):
        assert get_url_depth("https://example.com/page") == 1

    def test_multiple_levels(self):
        assert get_url_depth("https://example.com/a/b/c") == 3

    def test_trailing_slash(self):
        assert get_url_depth("https://example.com/page/") == 1


class TestIsSameDomain:
    def test_same_domain(self):
        assert is_same_domain("https://example.com/a", "https://example.com/b")

    def test_different_domain(self):
        assert not is_same_domain("https://example.com", "https://other.com")

    def test_subdomain_different(self):
        assert not is_same_domain("https://blog.example.com", "https://example.com")

    def test_case_insensitive(self):
        assert is_same_domain("https://Example.com", "https://example.com")
