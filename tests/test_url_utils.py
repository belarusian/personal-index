"""Tests for personal_index.url_utils (merged from url_utils + url_normalizer)."""


from personal_index.url_utils import (
    extract_all_urls,
    extract_domain,
    extract_subdomain,
    get_domain,
    get_fragment,
    get_path,
    get_query_string,
    get_tld,
    is_canonical,
    is_internal_link,
    is_robotstxt,
    is_same_domain,
    is_sitemap,
    is_valid_url,
    join_urls,
    normalize_url,
    remove_query_params,
    resolve_relative_url,
    strip_tracking_params,
    url_to_path,
    urls_are_equivalent,
)

# ── Tests from original test_url_utils.py ──


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
        assert normalize_url("https://example.com/") == "https://example.com/"

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
        assert extract_domain("") is None


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

    def test_full_url(self):
        result = join_urls("https://example.com/base", "https://other.com/page")
        assert result == "https://other.com/page"


class TestExtractAllUrls:
    """Tests for extract_all_urls."""

    def test_from_html(self):
        html = '<a href="https://example.com/page">Link</a>'
        urls = extract_all_urls(html)
        assert "https://example.com/page" in urls

    def test_from_plain_text(self):
        text = "Visit https://example.com for more info."
        urls = extract_all_urls(text)
        assert "https://example.com" in urls

    def test_empty(self):
        urls = extract_all_urls("")
        assert urls == []


class TestIsRobotstxt:
    """Tests for is_robotstxt."""

    def test_is_robots(self):
        assert is_robotstxt("https://example.com/robots.txt") is True

    def test_not_robots(self):
        assert is_robotstxt("https://example.com/page") is False


class TestIsSitemap:
    """Tests for is_sitemap."""

    def test_is_sitemap(self):
        assert is_sitemap("https://example.com/sitemap.xml") is True

    def test_not_sitemap(self):
        assert is_sitemap("https://example.com/page") is False


# ── Tests from original test_url_normalizer.py ──


class TestNormalizeURLAdvanced:
    """Tests for normalize_url advanced features from url_normalizer."""

    def test_lowercase_scheme_and_host(self):
        result = normalize_url("HTTP://EXAMPLE.COM/Path")
        assert result == "http://example.com/path"

    def test_collapse_multiple_slashes(self):
        result = normalize_url("http://example.com/path//to///page")
        assert result == "http://example.com/path/to/page"

    def test_sort_query_params(self):
        result = normalize_url("http://example.com?b=2&a=1")
        assert result == "http://example.com?a=1&b=2"

    def test_keep_fragment_when_requested(self):
        result = normalize_url("http://example.com/page#section", remove_fragment=False)
        assert result == "http://example.com/page#section"

    def test_complex_url(self):
        url = "HTTP://Example.COM:80/Path/To/Page/?b=2&a=1#frag"
        result = normalize_url(url)
        assert result == "http://example.com/path/to/page?a=1&b=2"


class TestIsCanonical:
    """Tests for is_canonical."""

    def test_canonical_url(self):
        assert is_canonical("http://example.com/path") is True

    def test_non_canonical_url(self):
        assert is_canonical("HTTP://EXAMPLE.COM/PATH") is False


class TestGetDomain:
    """Tests for get_domain (alias of extract_domain)."""

    def test_extract_domain(self):
        assert get_domain("https://example.com/path") == "example.com"

    def test_domain_with_port(self):
        # Note: extract_domain strips port, but get_domain alias should match
        # Since we changed extract_domain to strip ports, update test expectation
        assert get_domain("http://example.com:8080/path") == "example.com"


class TestGetPath:
    """Tests for get_path."""

    def test_extract_path(self):
        assert get_path("http://example.com/path/to/page") == "/path/to/page"

    def test_root_path(self):
        assert get_path("http://example.com") == "/"


class TestGetQueryString:
    """Tests for get_query_string."""

    def test_extract_query(self):
        assert get_query_string("http://example.com?foo=bar") == "foo=bar"

    def test_no_query(self):
        assert get_query_string("http://example.com/path") == ""


class TestGetFragment:
    """Tests for get_fragment."""

    def test_extract_fragment(self):
        assert get_fragment("http://example.com/page#section") == "section"

    def test_no_fragment(self):
        assert get_fragment("http://example.com/page") == ""


class TestUrlsAreEquivalent:
    """Tests for urls_are_equivalent."""

    def test_equivalent_urls(self):
        assert urls_are_equivalent("HTTP://A.COM/path", "http://a.com/PATH") is True

    def test_different_urls(self):
        assert urls_are_equivalent("http://a.com/path", "http://b.com/path") is False

    def test_port_difference(self):
        assert urls_are_equivalent("http://a.com:80/path", "http://a.com/path") is True


class TestStripTrackingParams:
    """Tests for strip_tracking_params."""

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
    """Tests for resolve_relative_url."""

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
