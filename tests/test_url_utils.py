"""Tests for personal_index.url_utils."""

import pytest
from personal_index.url_utils import (
    normalize_url,
    is_valid_url,
    extract_domain,
    is_same_domain,
    is_internal_link,
    sanitize_url,
    url_to_path,
    generate_seed_urls,
)


class TestNormalizeUrl:
    def test_remove_fragment(self):
        assert normalize_url("https://example.com/page#section") == "https://example.com/page"

    def test_lowercase_scheme_and_netloc(self):
        assert normalize_url("HTTPS://EXAMPLE.COM/Page") == "https://example.com/Page"

    def test_remove_trailing_slash(self):
        assert normalize_url("https://example.com/page/") == "https://example.com/page"

    def test_preserve_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com/"

    def test_no_change_needed(self):
        url = "https://example.com/page"
        assert normalize_url(url) == url

    def test_normalize_with_query(self):
        url = "https://example.com/page?b=2&a=1#frag"
        result = normalize_url(url)
        assert "#frag" not in result
        assert "https://example.com/page?b=2&a=1" == result


class TestIsValidUrl:
    def test_valid_http_url(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https_url(self):
        assert is_valid_url("https://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_ftp(self):
        assert is_valid_url("ftp://example.com") is False

    def test_invalid_empty(self):
        assert is_valid_url("") is False

    def test_invalid_malformed(self):
        assert is_valid_url("not a url") is False

    def test_valid_with_port(self):
        assert is_valid_url("https://example.com:8080/path") is True


class TestExtractDomain:
    def test_basic_domain(self):
        assert extract_domain("https://example.com/path") == "example.com"

    def test_domain_with_port(self):
        assert extract_domain("https://example.com:8080/path") == "example.com:8080"

    def test_domain_lowercase(self):
        assert extract_domain("https://EXAMPLE.COM/path") == "example.com"

    def test_domain_with_subdomain(self):
        assert extract_domain("https://sub.example.com/path") == "sub.example.com"


class TestIsSameDomain:
    def test_same_domain(self):
        assert is_same_domain("https://example.com/a", "https://example.com/b") is True

    def test_different_domain(self):
        assert is_same_domain("https://example.com", "https://other.com") is False

    def test_case_insensitive(self):
        assert is_same_domain("https://Example.com", "https://example.com") is True

    def test_different_subdomains(self):
        assert is_same_domain("https://a.example.com", "https://b.example.com") is False


class TestIsInternalLink:
    def test_internal_link(self):
        assert is_internal_link("https://example.com/page", "https://example.com") is True

    def test_external_link(self):
        assert is_internal_link("https://other.com/page", "https://example.com") is False


class TestSanitizeUrl:
    def test_remove_fragment(self):
        assert sanitize_url("https://example.com/page#section") == "https://example.com/page"

    def test_remove_null_bytes(self):
        assert sanitize_url("https://example.com/page%00evil") == "https://example.com/pageevil"

    def test_normalize_whitespace(self):
        assert sanitize_url("  https://example.com/page  ") == "https://example.com/page"

    def test_clean_url(self):
        url = "https://example.com/page"
        assert sanitize_url(url) == url


class TestUrlToPath:
    def test_basic_path(self):
        path = url_to_path("https://example.com/page")
        assert "example.com" in path
        assert "page" in path

    def test_path_with_special_chars(self):
        path = url_to_path("https://example.com/page?query=1")
        assert "?" not in path
        assert "=" not in path

    def test_empty_path(self):
        path = url_to_path("https://example.com")
        assert "index" in path


class TestGenerateSeedUrls:
    def test_generate_google_url(self):
        urls = generate_seed_urls(["python", "tutorial"], "google")
        assert len(urls) == 1
        assert "google.com" in urls[0]
        assert "python" in urls[0]
        assert "tutorial" in urls[0]

    def test_generate_duckduckgo_url(self):
        urls = generate_seed_urls(["python"], "duckduckgo")
        assert "duckduckgo.com" in urls[0]

    def test_generate_bing_url(self):
        urls = generate_seed_urls(["python"], "bing")
        assert "bing.com" in urls[0]

    def test_default_engine(self):
        urls = generate_seed_urls(["python"])
        assert "google.com" in urls[0]
