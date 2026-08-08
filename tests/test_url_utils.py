"""Tests for URL utilities."""

import pytest
from personal_index.url_utils import (
    is_valid_url,
    normalize_url,
    extract_links,
    get_domain,
    url_matches_pattern,
    is_same_domain,
    get_url_depth,
    filter_urls,
)


class TestIsValidUrl:
    def test_valid_http(self):
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self):
        assert is_valid_url("https://example.com/path") is True

    def test_invalid_no_scheme(self):
        assert is_valid_url("example.com") is False

    def test_invalid_no_netloc(self):
        assert is_valid_url("http://") is False

    def test_invalid_file_scheme(self):
        assert is_valid_url("file:///etc/passwd") is False

    def test_empty_string(self):
        assert is_valid_url("") is False


class TestNormalizeUrl:
    def test_remove_fragment(self):
        assert normalize_url("http://example.com/page#section") == "http://example.com/page"

    def test_remove_trailing_slash(self):
        assert normalize_url("http://example.com/path/") == "http://example.com/path"

    def test_lowercase_scheme_and_host(self):
        assert normalize_url("HTTP://EXAMPLE.COM/Path") == "http://example.com/Path"

    def test_remove_default_port_http(self):
        assert normalize_url("http://example.com:80/path") == "http://example.com/path"

    def test_remove_default_port_https(self):
        assert normalize_url("https://example.com:443/path") == "https://example.com/path"

    def test_preserve_non_default_port(self):
        result = normalize_url("http://example.com:8080/path")
        assert ":8080" in result


class TestExtractLinks:
    def test_extract_simple_links(self):
        html = '<a href="http://example.com/page1">Link 1</a><a href="http://example.com/page2">Link 2</a>'
        links = extract_links(html, "http://example.com/")
        assert "http://example.com/page1" in links
        assert "http://example.com/page2" in links

    def test_relative_links(self):
        html = '<a href="/page1">Link</a><a href="page2">Link</a>'
        links = extract_links(html, "http://example.com/")
        assert "http://example.com/page1" in links
        assert "http://example.com/page2" in links

    def test_skip_javascript_links(self):
        html = '<a href="javascript:void(0)">Skip</a><a href="http://example.com/valid">Valid</a>'
        links = extract_links(html, "http://example.com/")
        assert len(links) == 1
        assert "http://example.com/valid" in links

    def test_skip_mailto_links(self):
        html = '<a href="mailto:test@example.com">Email</a>'
        links = extract_links(html, "http://example.com/")
        assert len(links) == 0

    def test_deduplicate_links(self):
        html = '<a href="http://example.com/page">A</a><a href="http://example.com/page">B</a>'
        links = extract_links(html, "http://example.com/")
        assert len(links) == 1


class TestGetDomain:
    def test_simple_domain(self):
        assert get_domain("http://example.com/path") == "example.com"

    def test_https_domain(self):
        assert get_domain("https://www.example.com") == "www.example.com"

    def test_domain_with_port(self):
        assert get_domain("http://example.com:8080") == "example.com:8080"


class TestUrlMatchesPattern:
    def test_exact_match(self):
        assert url_matches_pattern("http://example.com/page", "http://example.com/page") is True

    def test_wildcard_match(self):
        assert url_matches_pattern("http://example.com/page1", "http://example.com/*") is True

    def test_no_match(self):
        assert url_matches_pattern("http://other.com/page", "http://example.com/*") is False

    def test_single_char_wildcard(self):
        assert url_matches_pattern("http://example.com/page", "http://example.com/pa?e") is True


class TestIsSameDomain:
    def test_same_domain(self):
        assert is_same_domain("http://example.com/a", "http://example.com/b") is True

    def test_different_domain(self):
        assert is_same_domain("http://example.com/a", "http://other.com/b") is False

    def test_case_insensitive(self):
        assert is_same_domain("http://Example.com/a", "http://example.com/b") is True


class TestGetUrlDepth:
    def test_same_page(self):
        assert get_url_depth("http://example.com/", "http://example.com/") == 0

    def test_deeper_page(self):
        assert get_url_depth("http://example.com/a/b/c", "http://example.com/") == 3

    def test_different_domain(self):
        assert get_url_depth("http://other.com/a", "http://example.com/") == -1


class TestFilterUrls:
    def test_no_filter(self):
        urls = ["http://example.com/a", "http://example.com/b"]
        assert filter_urls(urls) == urls

    def test_blocked_domains(self):
        urls = ["http://example.com/a", "http://blocked.com/b"]
        result = filter_urls(urls, blocked_domains={"blocked.com"})
        assert len(result) == 1
        assert "http://example.com/a" in result

    def test_url_patterns(self):
        urls = ["http://example.com/blog/post1", "http://example.com/shop/item1"]
        result = filter_urls(urls, url_patterns=["http://example.com/blog/*"])
        assert len(result) == 1
        assert "http://example.com/blog/post1" in result
