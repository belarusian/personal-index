"""Tests for personal_index.url_utils (all pure functions)."""

from __future__ import annotations

from personal_index.url_utils import (
    extract_domain,
    extract_subdomain,
    get_domain,
    get_fragment,
    get_path,
    get_query_string,
    get_tld,
    get_url_depth,
    is_canonical,
    is_excluded_url,
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

# ── is_valid_url ───────────────────────────────────────────────────

class TestIsValidUrl:
    """Tests for is_valid_url."""

    def test_valid_http(self) -> None:
        assert is_valid_url("http://example.com") is True

    def test_valid_https(self) -> None:
        assert is_valid_url("https://example.com/path") is True

    def test_valid_with_port(self) -> None:
        assert is_valid_url("https://example.com:8080/path") is True

    def test_invalid_ftp_scheme(self) -> None:
        assert is_valid_url("ftp://example.com") is False

    def test_invalid_no_scheme(self) -> None:
        assert is_valid_url("example.com") is False

    def test_invalid_empty_string(self) -> None:
        assert is_valid_url("") is False

    def test_invalid_malformed(self) -> None:
        assert is_valid_url("not a url at all") is False

    def test_invalid_javascript_scheme(self) -> None:
        assert is_valid_url("javascript:alert(1)") is False


# ── normalize_url ──────────────────────────────────────────────────

class TestNormalizeUrl:
    """Tests for normalize_url."""

    def test_fragment_removal(self) -> None:
        result = normalize_url("https://example.com/page#section")
        assert result is not None
        assert "#section" not in result

    def test_lowercase_path(self) -> None:
        result = normalize_url("https://example.com/Path/To/Page")
        assert result == "https://example.com/path/to/page"

    def test_default_port_removal_http(self) -> None:
        result = normalize_url("http://example.com:80/path")
        assert result is not None
        assert ":80" not in result

    def test_default_port_removal_https(self) -> None:
        result = normalize_url("https://example.com:443/path")
        assert result is not None
        assert ":443" not in result

    def test_non_default_port_kept(self) -> None:
        result = normalize_url("https://example.com:8080/path")
        assert result is not None
        assert ":8080" in result

    def test_query_param_sorting(self) -> None:
        result = normalize_url("https://example.com?b=2&a=1")
        assert result == "https://example.com?a=1&b=2"

    def test_relative_url_resolution(self) -> None:
        result = normalize_url("page.html", base_url="https://example.com/dir/")
        assert result == "https://example.com/dir/page.html"

    def test_trailing_slash_removal(self) -> None:
        result = normalize_url("https://example.com/path/")
        assert result == "https://example.com/path"

    def test_root_slash_preserved(self) -> None:
        result = normalize_url("https://example.com/")
        assert result == "https://example.com/"

    def test_lowercase_scheme_and_host(self) -> None:
        result = normalize_url("HTTP://EXAMPLE.COM/Path")
        assert result == "http://example.com/path"

    def test_collapse_multiple_slashes(self) -> None:
        result = normalize_url("http://example.com/path//to///page")
        assert result == "http://example.com/path/to/page"

    def test_keep_fragment_when_requested(self) -> None:
        result = normalize_url(
            "http://example.com/page#section", remove_fragment=False
        )
        assert result is not None
        assert "#section" in result

    def test_empty_url_returns_none(self) -> None:
        assert normalize_url("") is None

    def test_invalid_scheme_returns_none(self) -> None:
        assert normalize_url("ftp://example.com") is None

    def test_complex_url(self) -> None:
        url = "HTTP://Example.COM:80/Path/To/Page/?b=2&a=1#frag"
        result = normalize_url(url)
        assert result == "http://example.com/path/to/page?a=1&b=2"


# ── is_canonical ───────────────────────────────────────────────────

class TestIsCanonical:
    """Tests for is_canonical."""

    def test_canonical_url(self) -> None:
        assert is_canonical("http://example.com/path") is True

    def test_non_canonical_uppercase(self) -> None:
        assert is_canonical("HTTP://EXAMPLE.COM/PATH") is False

    def test_non_canonical_with_fragment(self) -> None:
        assert is_canonical("http://example.com/path#section") is False


# ── extract_domain / get_domain ────────────────────────────────────

class TestExtractDomain:
    """Tests for extract_domain and get_domain alias."""

    def test_simple_domain(self) -> None:
        assert extract_domain("https://example.com/path") == "example.com"

    def test_subdomain(self) -> None:
        assert extract_domain("https://sub.example.com") == "sub.example.com"

    def test_empty_url(self) -> None:
        assert extract_domain("") is None

    def test_domain_with_port_stripped(self) -> None:
        assert extract_domain("http://example.com:8080/path") == "example.com"

    # TICKET-316: bracketed IPv6 literals contain internal colons; the port
    # strip must not chop the last colon off the literal when no port is set.
    def test_ipv6_literal_without_port(self) -> None:
        assert extract_domain("http://[::1]/path") == "[::1]"

    def test_ipv6_full_literal_without_port(self) -> None:
        assert extract_domain("http://[2001:db8::1]/") == "[2001:db8::1]"

    def test_ipv6_literal_with_port(self) -> None:
        assert extract_domain("http://[::1]:8080/path") == "[::1]"

    def test_ipv6_full_literal_with_port(self) -> None:
        assert extract_domain("http://[2001:db8::ff00:42:8329]:80/") == (
            "[2001:db8::ff00:42:8329]"
        )

    def test_ipv6_literal_is_case_normalized(self) -> None:
        assert extract_domain("http://[2001:DB8::1]/") == "[2001:db8::1]"

    def test_get_domain_alias(self) -> None:
        assert get_domain("https://example.com/path") == "example.com"


# ── get_path ───────────────────────────────────────────────────────

class TestGetPath:
    """Tests for get_path."""

    def test_extract_path(self) -> None:
        assert get_path("http://example.com/path/to/page") == "/path/to/page"

    def test_root_path(self) -> None:
        assert get_path("http://example.com") == "/"


# ── get_query_string ───────────────────────────────────────────────

class TestGetQueryString:
    """Tests for get_query_string."""

    def test_extract_query(self) -> None:
        assert get_query_string("http://example.com?foo=bar") == "foo=bar"

    def test_no_query(self) -> None:
        assert get_query_string("http://example.com/path") == ""


# ── get_fragment ───────────────────────────────────────────────────

class TestGetFragment:
    """Tests for get_fragment."""

    def test_extract_fragment(self) -> None:
        assert get_fragment("http://example.com/page#section") == "section"

    def test_no_fragment(self) -> None:
        assert get_fragment("http://example.com/page") == ""


# ── extract_subdomain ──────────────────────────────────────────────

class TestExtractSubdomain:
    """Tests for extract_subdomain."""

    def test_with_subdomain(self) -> None:
        assert extract_subdomain("https://blog.example.com") == "blog"

    def test_without_subdomain(self) -> None:
        assert extract_subdomain("https://example.com") == ""

    def test_nested_subdomain(self) -> None:
        assert extract_subdomain("https://dev.blog.example.com") == "dev.blog"

    def test_empty_url(self) -> None:
        assert extract_subdomain("") == ""


# ── get_tld ────────────────────────────────────────────────────────

class TestGetTld:
    """Tests for get_tld."""

    def test_com(self) -> None:
        assert get_tld("https://example.com") == "com"

    def test_org(self) -> None:
        assert get_tld("https://example.org") == "org"

    def test_empty(self) -> None:
        assert get_tld("") == ""


# ── get_url_depth ──────────────────────────────────────────────────

class TestGetUrlDepth:
    """Tests for get_url_depth."""

    def test_root_depth(self) -> None:
        assert get_url_depth("https://example.com/") == 0

    def test_one_level(self) -> None:
        assert get_url_depth("https://example.com/page") == 1

    def test_multiple_levels(self) -> None:
        assert get_url_depth("https://example.com/a/b/c") == 3


# ── is_same_domain ─────────────────────────────────────────────────

class TestIsSameDomain:
    """Tests for is_same_domain."""

    def test_same_domain(self) -> None:
        assert is_same_domain(
            "https://example.com/a", "https://example.com/b"
        ) is True

    def test_different_domain(self) -> None:
        assert is_same_domain(
            "https://example.com", "https://other.com"
        ) is False

    def test_subdomain_different(self) -> None:
        assert is_same_domain(
            "https://sub.example.com", "https://example.com"
        ) is False


# ── is_internal_link ───────────────────────────────────────────────

class TestIsInternalLink:
    """Tests for is_internal_link."""

    def test_internal(self) -> None:
        assert is_internal_link(
            "https://example.com/page", "https://example.com"
        ) is True

    def test_external(self) -> None:
        assert is_internal_link(
            "https://other.com/page", "https://example.com"
        ) is False


# ── urls_are_equivalent ────────────────────────────────────────────

class TestUrlsAreEquivalent:
    """Tests for urls_are_equivalent."""

    def test_equivalent_urls(self) -> None:
        assert urls_are_equivalent(
            "HTTP://A.COM/path", "http://a.com/PATH"
        ) is True

    def test_different_urls(self) -> None:
        assert urls_are_equivalent(
            "http://a.com/path", "http://b.com/path"
        ) is False

    def test_port_difference_normalized(self) -> None:
        assert urls_are_equivalent(
            "http://a.com:80/path", "http://a.com/path"
        ) is True

    def test_distinct_non_http_urls_not_equivalent(self) -> None:
        # TICKET-314: two distinct non-http/https URLs both normalize to None
        # and must NOT be reported as equivalent.
        assert urls_are_equivalent(
            "mailto:a@x.com", "mailto:b@y.com"
        ) is False
        assert urls_are_equivalent(
            "ftp://a.com/f", "ftp://b.com/g"
        ) is False

    def test_empty_urls_not_equivalent(self) -> None:
        # TICKET-314: empty input normalizes to None -> never equivalent.
        assert urls_are_equivalent("", "") is False


# ── remove_query_params ────────────────────────────────────────────

class TestRemoveQueryParams:
    """Tests for remove_query_params."""

    def test_remove_single_param(self) -> None:
        result = remove_query_params(
            "https://example.com?foo=1&bar=2", params=["foo"]
        )
        assert "foo" not in result
        assert "bar=2" in result

    def test_remove_no_params(self) -> None:
        result = remove_query_params("https://example.com?foo=1")
        assert "foo=1" in result

    def test_remove_all_params(self) -> None:
        result = remove_query_params(
            "https://example.com?foo=1&bar=2", params=["foo", "bar"]
        )
        assert "foo" not in result
        assert "bar" not in result

    def test_remove_does_not_drop_sibling_prefix_param(self) -> None:
        # Removing "foo" must not drop the sibling "foobar" param.
        result = remove_query_params(
            "https://example.com?foo=1&foobar=2", params=["foo"]
        )
        assert "foo=1" not in result
        assert "foobar=2" in result

    def test_remove_does_not_match_key_inside_value(self) -> None:
        # A value that merely contains the key must not be removed.
        result = remove_query_params(
            "https://example.com?msg=foo=1&bar=2", params=["foo"]
        )
        assert "msg=foo=1" in result
        assert "bar=2" in result


# ── strip_tracking_params ──────────────────────────────────────────

class TestStripTrackingParams:
    """Tests for strip_tracking_params."""

    def test_remove_utm_source(self) -> None:
        result = strip_tracking_params(
            "http://example.com?utm_source=google&foo=bar"
        )
        assert "utm_source" not in result
        assert "foo=bar" in result

    def test_remove_fbclid(self) -> None:
        result = strip_tracking_params(
            "http://example.com?fbclid=abc123&ref=home"
        )
        assert "fbclid" not in result
        assert "ref=home" in result

    def test_no_tracking_params(self) -> None:
        result = strip_tracking_params("http://example.com?foo=bar")
        assert "foo=bar" in result

    def test_remove_all_utm_params(self) -> None:
        result = strip_tracking_params(
            "http://example.com?utm_source=a&utm_medium=b&utm_campaign=c"
        )
        assert "utm_source" not in result
        assert "utm_medium" not in result
        assert "utm_campaign" not in result


# ── url_to_path ────────────────────────────────────────────────────

class TestUrlToPath:
    """Tests for url_to_path."""

    def test_simple_path(self) -> None:
        path = url_to_path("https://example.com/page")
        assert "example.com" in path
        assert "page" in path

    def test_special_chars_replaced(self) -> None:
        path = url_to_path("https://example.com/path/to/page")
        assert "/" not in path

    def test_empty_url(self) -> None:
        assert url_to_path("") == ""

    def test_root_url(self) -> None:
        path = url_to_path("https://example.com/")
        assert "index" in path


# ── join_urls ──────────────────────────────────────────────────────

class TestJoinUrls:
    """Tests for join_urls."""

    def test_relative_path(self) -> None:
        result = join_urls("https://example.com/base/", "page")
        assert result == "https://example.com/base/page"

    def test_absolute_path_replaces(self) -> None:
        result = join_urls("https://example.com/base", "/other")
        assert result == "https://example.com/other"

    def test_full_url_returned_as_is(self) -> None:
        result = join_urls("https://example.com", "https://other.com/page")
        assert result == "https://other.com/page"

    def test_base_without_trailing_slash(self) -> None:
        result = join_urls("https://example.com/dir", "page")
        assert result == "https://example.com/dir/page"


# ── resolve_relative_url ───────────────────────────────────────────

class TestResolveRelativeUrl:
    """Tests for resolve_relative_url."""

    def test_absolute_url(self) -> None:
        result = resolve_relative_url(
            "http://example.com", "http://other.com/page"
        )
        assert result == "http://other.com/page"

    def test_root_relative(self) -> None:
        result = resolve_relative_url("http://example.com/base", "/page")
        assert result == "http://example.com/page"

    def test_relative_path_with_trailing_slash(self) -> None:
        result = resolve_relative_url("http://example.com/base/", "page")
        assert result == "http://example.com/base/page"

    def test_relative_path_no_trailing_slash(self) -> None:
        result = resolve_relative_url(
            "http://example.com/dir/page", "other"
        )
        assert result == "http://example.com/dir/other"

    def test_javascript_scheme_rejected(self) -> None:
        result = resolve_relative_url(
            "http://example.com", "javascript:alert(1)"
        )
        assert result is None

    def test_root_relative_with_query(self) -> None:
        result = resolve_relative_url("http://example.com/base", "/page?x=1")
        assert result == "http://example.com/page?x=1"

    def test_relative_with_query(self) -> None:
        result = resolve_relative_url("http://example.com/base/", "page?x=1")
        assert result == "http://example.com/base/page?x=1"

    def test_fragment_only_keeps_base_page(self) -> None:
        # A fragment-only reference points at the base page itself; the
        # page path must not be dropped to the parent directory.
        result = resolve_relative_url(
            "http://example.com/dir/page", "#section"
        )
        assert result == "http://example.com/dir/page#section"

    def test_query_only_keeps_base_page(self) -> None:
        # A query-only reference likewise points at the base page itself.
        result = resolve_relative_url(
            "http://example.com/dir/page", "?x=1"
        )
        assert result == "http://example.com/dir/page?x=1"


# ── is_robotstxt ───────────────────────────────────────────────────

class TestIsRobotstxt:
    """Tests for is_robotstxt."""

    def test_is_robots(self) -> None:
        assert is_robotstxt("https://example.com/robots.txt") is True

    def test_not_robots(self) -> None:
        assert is_robotstxt("https://example.com/page") is False


# ── is_sitemap ─────────────────────────────────────────────────────

class TestIsSitemap:
    """Tests for is_sitemap."""

    def test_is_sitemap(self) -> None:
        assert is_sitemap("https://example.com/sitemap.xml") is True

    def test_not_sitemap(self) -> None:
        assert is_sitemap("https://example.com/page") is False

    def test_sitemap_variants(self) -> None:
        assert is_sitemap("https://example.com/sitemap_index.xml") is True
        assert is_sitemap("https://example.com/sitemap-news.xml") is True

    def test_substring_overmatch_not_sitemap(self) -> None:
        # Pages that merely contain the word "sitemap" in a longer name are
        # not sitemaps (the old bare-substring check misclassified these).
        assert is_sitemap("https://example.com/about-sitemap") is False
        assert is_sitemap("https://example.com/sitemap-backup") is False
        assert is_sitemap("https://example.com/mysitemap-page") is False
        assert is_sitemap("https://example.com/sitemap") is False


# ── is_excluded_url ────────────────────────────────────────────────

class TestIsExcludedUrl:
    """Tests for is_excluded_url."""

    def test_excluded_image(self) -> None:
        assert is_excluded_url("https://example.com/photo.jpg") is True

    def test_excluded_css(self) -> None:
        assert is_excluded_url("https://example.com/style.css") is True

    def test_excluded_pdf(self) -> None:
        assert is_excluded_url("https://example.com/doc.pdf") is True

    def test_not_excluded_html(self) -> None:
        assert is_excluded_url("https://example.com/page.html") is False

    def test_empty_url_excluded(self) -> None:
        assert is_excluded_url("") is True

    def test_excluded_javascript_scheme(self) -> None:
        assert is_excluded_url("javascript:alert(1)") is True


# ── normalize_url contract (TICKET-500) ───────────────────────────

class TestNormalizeUrlContract:
    """Pinning tests for the exact normalize_url contract (TICKET-500)."""

    def test_exception_fallback_returns_original_not_none(self) -> None:
        # A URL that raises during parsing is returned UNCHANGED, not None.
        bad = "http://[invalid"
        result = normalize_url(bad)
        assert result is bad

    def test_empty_url_returns_none(self) -> None:
        assert normalize_url("") is None

    def test_non_http_scheme_returns_none(self) -> None:
        assert normalize_url("ftp://example.com/file") is None

    def test_javascript_scheme_returns_none(self) -> None:
        assert normalize_url("javascript:alert(1)") is None

    def test_base_url_resolves_schemeless_url(self) -> None:
        result = normalize_url("/relative/path", base_url="http://example.com/base/")
        assert result == "http://example.com/relative/path"

    def test_sort_query_params_opt_out(self) -> None:
        result = normalize_url(
            "http://example.com/path?b=2&a=1", sort_query_params=False
        )
        assert result == "http://example.com/path?b=2&a=1"

    def test_lowercase_path_opt_out(self) -> None:
        result = normalize_url("http://example.com/Path", lowercase_path=False)
        assert result == "http://example.com/Path"

    def test_remove_default_port_opt_out(self) -> None:
        result = normalize_url(
            "http://example.com:80/path", remove_default_port=False
        )
        assert result == "http://example.com:80/path"

    def test_remove_fragment_opt_out(self) -> None:
        result = normalize_url(
            "http://example.com/path#section", remove_fragment=False
        )
        assert result == "http://example.com/path#section"
