"""Tests for personal_index.url_utils."""

import pytest

from personal_index.url_utils import (
    extract_all_urls,
    extract_domain,
    extract_subdomain,
    get_tld,
    is_internal_link,
    is_robotstxt,
    is_same_domain,
    is_sitemap,
    is_valid_url,
    join_urls,
    normalize_url,
    remove_query_params,
    url_to_path,
)


class TestIsValidUrl:
    """Tests for is_valid_url."""

    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self):
        assert is_valid_url("https://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_ftp(self):
        assert is_valid_url("ftp://example.com") is False

    def test_invalid_empty(self):
        assert is_valid_url("") is False

    def test_invalid_malformed(self):
        assert is_valid_url("not a url at all") is False


class TestNormalizeUrl:
    """Tests for normalize_url."""

    def test_lowercase_scheme(self):
        assert normalize_url("HTTPS://Example.com") == "https://example.com"

    def test_remove_fragment(self):
        assert normalize_url("https://example.com#section") == "https://example.com"

    def test_remove_trailing_slash(self):
        assert normalize_url("https://example.com/path/") == "https://example.com/path"

    def test_keep_root_slash(self):
        assert normalize_url("https://example.com/") == "https://example.com"

    def test_remove_default_http_port(self):
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_remove_default_https_port(self):
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_keep_non_default_port(self):
        assert normalize_url("https://example.com:8080/path") == "https://example.com:8080/path"


class TestExtractDomain:
    """Tests for extract_domain."""

    def test_simple_domain(self):
        assert extract_domain("https://example.com/path") == "example.com"

    def test_subdomain(self):
        assert extract_domain("https://sub.example.com") == "sub.example.com"

    def test_empty_url(self):
        assert extract_domain("") == ""


class TestIsSameDomain:
    """Tests for is_same_domain."""

    def test_same_domain(self):
        assert is_same_domain("https://example.com/a", "https://example.com/b") is True

    def test_different_domain(self):
        assert is_same_domain("https://example.com", "https://other.com") is False

    def test_subdomain_different(self):
        assert is_same_domain("https://sub.example.com", "https://example.com") is False


class TestExtractSubdomain:
    """Tests for extract_subdomain."""

    def test_with_subdomain(self):
        assert extract_subdomain("https://blog.example.com") == "blog"

    def test_without_subdomain(self):
        assert extract_subdomain("https://example.com") == ""

    def test_nested_subdomain(self):
        assert extract_subdomain("https://dev.blog.example.com") == "dev.blog"


class TestGetTld:
    """Tests for get_tld."""

    def test_com(self):
        assert get_tld("https://example.com") == "com"

    def test_org(self):
        assert get_tld("https://example.org") == "org"

    def test_empty(self):
        assert get_tld("") == ""


class TestIsInternalLink:
    """Tests for is_internal_link."""

    def test_internal(self):
        assert is_internal_link("https://example.com/page", "https://example.com") is True

    def test_external(self):
        assert is_internal_link("https://other.com/page", "https://example.com") is False


class TestRemoveQueryParams:
    """Tests for remove_query_params."""

    def test_remove_single_param(self):
        result = remove_query_params(
            "https://example.com?foo=1&bar=2",
            params=["foo"],
        )
        assert "foo" not in result
        assert "bar=2" in result

    def test_remove_no_params(self):
        result = remove_query_params("https://example.com?foo=1")
        assert "foo=1" in result

    def test_remove_all_params(self):
        result = remove_query_params(
            "https://example.com?foo=1&bar=2",
            params=["foo", "bar"],
        )
        assert "foo" not in result
        assert "bar" not in result


class TestUrlToPath:
    """Tests for url_to_path."""

    def test_simple_path(self):
        path = url_to_path("https://example.com/page")
        assert "example.com" in path
        assert "page" in path

    def test_special_chars(self):
        path = url_to_path("https://example.com/path/to/page")
        assert "/" not in path  # Should be replaced with _


class TestJoinUrls:
    """Tests for join_urls."""

    def test_relative_path(self):
        result = join_urls("https://example.com/base", "page")
        assert result == "https://example.com/base/page"

    def test_absolute_path(self):
        result = join_urls("https://example.com/base", "/other")
        assert result == "https://example.com/other"

    def test_external_url(self):
        result = join_urls("https://example.com", "https://other.com/page")
        assert result == "https://other.com/page"


class TestExtractAllUrls:
    """Tests for extract_all_urls."""

    def test_extract_single_url(self):
        text = "Visit https://example.com for more"
        urls = extract_all_urls(text)
        assert "https://example.com" in urls

    def test_extract_multiple_urls(self):
        text = "See https://a.com and https://b.com"
        urls = extract_all_urls(text)
        assert len(urls) == 2

    def test_no_urls(self):
        urls = extract_all_urls("No URLs here")
        assert urls == []


class TestIsRobotstxt:
    """Tests for is_robotstxt."""

    def test_is_robots(self):
        assert is_robotstxt("https://example.com/robots.txt") is True

    def test_not_robots(self):
        assert is_robotstxt("https://example.com/page") is False


class TestIsSitemap:
    """Tests for is_sitemap."""

    def test_is_sitemap_xml(self):
        assert is_sitemap("https://example.com/sitemap.xml") is True

    def test_is_sitemap_path(self):
        assert is_sitemap("https://example.com/sitemap/index.xml") is True

    def test_not_sitemap(self):
        assert is_sitemap("https://example.com/page") is False
