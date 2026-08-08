"""Tests for URL normalization module."""

import pytest
from personal_index.url_normalizer import (
    normalize_url,
    is_canonical,
    get_domain,
    get_path,
    get_query_string,
    get_fragment,
    urls_are_equivalent,
    strip_tracking_params,
    resolve_relative_url,
)


class TestNormalizeURL:
    def test_lowercase_scheme_and_host(self):
        result = normalize_url("HTTP://EXAMPLE.COM/Path")
        assert result == "http://example.com/path"

    def test_remove_default_http_port(self):
        result = normalize_url("http://example.com:80/path")
        assert result == "http://example.com/path"

    def test_remove_default_https_port(self):
        result = normalize_url("https://example.com:443/path")
        assert result == "https://example.com/path"

    def test_keep_non_default_port(self):
        result = normalize_url("http://example.com:8080/path")
        assert result == "http://example.com:8080/path"

    def test_remove_trailing_slash(self):
        result = normalize_url("http://example.com/path/")
        assert result == "http://example.com/path"

    def test_keep_root_slash(self):
        result = normalize_url("http://example.com/")
        assert result == "http://example.com"

    def test_collapse_multiple_slashes(self):
        result = normalize_url("http://example.com/path//to///page")
        assert result == "http://example.com/path/to/page"

    def test_sort_query_params(self):
        result = normalize_url("http://example.com?b=2&a=1")
        assert result == "http://example.com?a=1&b=2"

    def test_remove_fragment(self):
        result = normalize_url("http://example.com/page#section")
        assert result == "http://example.com/page"

    def test_keep_fragment_when_requested(self):
        result = normalize_url("http://example.com/page#section", remove_fragment=False)
        assert result == "http://example.com/page#section"

    def test_complex_url(self):
        url = "HTTP://Example.COM:80/Path/To/Page/?b=2&a=1#frag"
        result = normalize_url(url)
        assert result == "http://example.com/path/to/page?a=1&b=2"


class TestIsCanonical:
    def test_canonical_url(self):
        assert is_canonical("http://example.com/path") is True

    def test_non_canonical_url(self):
        assert is_canonical("HTTP://EXAMPLE.COM/PATH") is False


class TestGetDomain:
    def test_extract_domain(self):
        assert get_domain("https://example.com/path") == "example.com"

    def test_domain_with_port(self):
        assert get_domain("http://example.com:8080/path") == "example.com:8080"


class TestGetPath:
    def test_extract_path(self):
        assert get_path("http://example.com/path/to/page") == "/path/to/page"

    def test_root_path(self):
        assert get_path("http://example.com") == "/"


class TestGetQueryString:
    def test_extract_query(self):
        assert get_query_string("http://example.com?foo=bar") == "foo=bar"

    def test_no_query(self):
        assert get_query_string("http://example.com/path") == ""


class TestGetFragment:
    def test_extract_fragment(self):
        assert get_fragment("http://example.com/page#section") == "section"

    def test_no_fragment(self):
        assert get_fragment("http://example.com/page") == ""


class TestUrlsAreEquivalent:
    def test_equivalent_urls(self):
        assert urls_are_equivalent("HTTP://A.COM/path", "http://a.com/PATH") is True

    def test_different_urls(self):
        assert urls_are_equivalent("http://a.com/path", "http://b.com/path") is False

    def test_port_difference(self):
        assert urls_are_equivalent("http://a.com:80/path", "http://a.com/path") is True


class TestStripTrackingParams:
    def test_remove_utm_params(self):
        result = strip_tracking_params("http://example.com?utm_source=google&foo=bar")
        assert "utm_source" not in result
        assert "foo=bar" in result

    def test_remove_fbclid(self):
        result = strip_tracking_params("http://example.com?fbclid=abc123&ref=home")
        assert "fbclid" not in result
        assert "ref=home" in result

    def test_no_tracking_params(self):
        result = strip_tracking_params("http://example.com?foo=bar")
        assert "foo=bar" in result


class TestResolveRelativeURL:
    def test_absolute_url(self):
        result = resolve_relative_url("http://example.com", "http://other.com/page")
        assert result == "http://other.com/page"

    def test_root_relative(self):
        result = resolve_relative_url("http://example.com/base", "/page")
        assert result == "http://example.com/page"

    def test_relative_path(self):
        result = resolve_relative_url("http://example.com/base/", "page")
        assert result == "http://example.com/base/page"

    def test_relative_path_no_trailing_slash(self):
        result = resolve_relative_url("http://example.com/dir/page", "other")
        assert result == "http://example.com/dir/other"
