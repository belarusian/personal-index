"""Adversarial deep tests for personal_index.url_utils.

Contract source: personal_index/url_utils.py docstrings for the pure URL
helpers. These tests pin the documented behavior against adversarial inputs:
empty / whitespace / unicode / duplicate / out-of-range values, IPv6 literals,
default-port stripping, query-param sorting, fragment handling, the documented
"parse failure returns the ORIGINAL url (not None)" claim, idempotence
(normalize is a fixed point), and one end-to-end CLI run (init + search on an
empty index).

Functions armored:
  is_valid_url, normalize_url, extract_domain, get_path, get_query_string,
  get_fragment, extract_subdomain, get_tld, get_url_depth, is_same_domain,
  is_internal_link, urls_are_equivalent, remove_query_params,
  strip_tracking_params, url_to_path, join_urls.
"""

from __future__ import annotations

import pytest

from personal_index.url_utils import (
    extract_domain,
    extract_subdomain,
    get_fragment,
    get_path,
    get_query_string,
    get_tld,
    get_url_depth,
    is_canonical,
    is_internal_link,
    is_same_domain,
    is_valid_url,
    join_urls,
    normalize_url,
    remove_query_params,
    strip_tracking_params,
    url_to_path,
    urls_are_equivalent,
)


# --- is_valid_url -----------------------------------------------------------

def test_is_valid_url_good():
    assert is_valid_url("https://a.com/p") is True
    assert is_valid_url("http://a.com") is True


def test_is_valid_url_rejects_non_http():
    # contract: "has an http/https scheme"
    assert is_valid_url("ftp://a.com/x") is False
    assert is_valid_url("javascript:alert(1)") is False
    assert is_valid_url("mailto:x@y.com") is False
    assert is_valid_url("data:text/plain,hi") is False


def test_is_valid_url_rejects_empty_and_no_netloc():
    assert is_valid_url("") is False
    assert is_valid_url("   ") is False
    # scheme present but no netloc -> invalid
    assert is_valid_url("http://") is False
    assert is_valid_url("https://") is False


def test_is_valid_url_rejects_schemeless():
    # no scheme at all -> not http/https
    assert is_valid_url("a.com/p") is False
    assert is_valid_url("www.a.com") is False


# --- normalize_url: None contract ------------------------------------------

def test_normalize_url_empty_is_none():
    assert normalize_url("") is None


def test_normalize_url_non_http_is_none():
    # contract: "None when scheme is not http/https (e.g. ftp://, javascript:)"
    assert normalize_url("ftp://a.com/x") is None
    assert normalize_url("javascript:alert(1)") is None
    assert normalize_url("mailto:x@y.com") is None


# --- normalize_url: transformations ----------------------------------------

def test_normalize_url_strips_default_port():
    # contract: strip :80 for http, :443 for https
    assert normalize_url("http://a.com:80/p") == "http://a.com/p"
    assert normalize_url("https://a.com:443/p") == "https://a.com/p"


def test_normalize_url_keeps_non_default_port():
    assert normalize_url("http://a.com:8080/p") == "http://a.com:8080/p"
    assert normalize_url("https://a.com:8443/p") == "https://a.com:8443/p"


def test_normalize_url_can_disable_default_port_strip():
    assert normalize_url("http://a.com:80/p", remove_default_port=False) == "http://a.com:80/p"


def test_normalize_url_lowercases_path():
    assert normalize_url("https://a.com/Path/To") == "https://a.com/path/to"


def test_normalize_url_can_disable_path_lowercase():
    assert normalize_url("https://a.com/Path/To", lowercase_path=False) == "https://a.com/Path/To"


def test_normalize_url_drops_fragment_by_default():
    assert normalize_url("https://a.com/p#frag") == "https://a.com/p"


def test_normalize_url_keeps_fragment_when_disabled():
    assert normalize_url("https://a.com/p#frag", remove_fragment=False) == "https://a.com/p#frag"


def test_normalize_url_sorts_query_params():
    # contract: "sort the query string alphabetically"
    assert normalize_url("https://a.com/p?b=2&a=1") == "https://a.com/p?a=1&b=2"


def test_normalize_url_can_disable_query_sort():
    assert normalize_url("https://a.com/p?b=2&a=1", sort_query_params=False) == "https://a.com/p?b=2&a=1"


def test_normalize_url_collapses_slashes():
    assert normalize_url("https://a.com/a//b///c") == "https://a.com/a/b/c"


def test_normalize_url_strips_trailing_slash():
    assert normalize_url("https://a.com/a/b/") == "https://a.com/a/b"


def test_normalize_url_resolves_relative_against_base():
    # contract: "When base_url is given and url has no scheme, url is first
    # resolved against base_url."
    assert normalize_url("/p", base_url="https://a.com/base/") == "https://a.com/p"
    assert normalize_url("rel", base_url="https://a.com/base/") == "https://a.com/base/rel"


def test_normalize_url_ignores_base_for_absolute():
    # an absolute url is not re-resolved against base
    assert normalize_url("https://b.com/p", base_url="https://a.com/base/") == "https://b.com/p"


def test_normalize_url_lowercases_netloc():
    assert normalize_url("https://A.COM/p") == "https://a.com/p"


# --- normalize_url: parse-failure returns ORIGINAL (not None) ---------------

def test_normalize_url_parse_failure_returns_original():
    # contract: "On a parse failure (ValueError/AttributeError) the ORIGINAL
    # url is returned unchanged — not None."
    # A malformed percent-escape triggers a ValueError inside urlparse.
    bad = "http://a.com/%zz"
    assert normalize_url(bad) == bad


def test_normalize_url_parse_failure_not_none():
    bad = "http://a.com/%zz"
    assert normalize_url(bad) is not None


# --- normalize_url: idempotence (fixed point) -------------------------------

@pytest.mark.parametrize(
    "url",
    [
        "https://a.com/P?b=2&a=1#f",
        "http://a.com:80/x",
        "https://a.com/a/b/",
        "https://a.com/Ünïcödé/Path",
        "https://a.com:8080/p?z=1&a=2",
    ],
)
def test_normalize_url_is_idempotent(url):
    once = normalize_url(url)
    assert once is not None
    assert normalize_url(once) == once


def test_normalize_url_none_is_stable():
    # None normalizes to None (empty) and stays None
    assert normalize_url("") is None
    assert normalize_url(None) is None


# --- normalize_url: unicode -------------------------------------------------

def test_normalize_url_unicode_path_lowercased():
    assert normalize_url("https://a.com/Ünïcödé/Path") == "https://a.com/ünïcödé/path"


def test_normalize_url_unicode_netloc_lowercased():
    assert normalize_url("https://Ünïcödé.com/p") == "https://ünïcödé.com/p"


# --- extract_domain ---------------------------------------------------------

def test_extract_domain_strips_port():
    assert extract_domain("https://a.com:8080/p") == "a.com"


def test_extract_domain_ipv6_with_port():
    # contract: bracketed IPv6 literal keeps the literal, drops trailing :port
    assert extract_domain("https://[::1]:8080/p") == "[::1]"


def test_extract_domain_ipv6_without_port():
    # contract: no port -> literal preserved intact (not split on last colon)
    assert extract_domain("https://[::1]/p") == "[::1]"


def test_extract_domain_ipv6_full_literal():
    assert extract_domain("https://[2001:db8::1]:8080/p") == "[2001:db8::1]"


def test_extract_domain_empty_and_no_netloc():
    assert extract_domain("") is None
    assert extract_domain("http://") is None


def test_extract_domain_lowercases():
    assert extract_domain("https://A.COM/p") == "a.com"


def test_extract_domain_unicode():
    assert extract_domain("https://Ünïcödé.com/p") == "ünïcödé.com"


def test_extract_domain_get_domain_alias():
    from personal_index.url_utils import get_domain
    assert get_domain("https://a.com:8080/p") == extract_domain("https://a.com:8080/p")


# --- get_path / get_query_string / get_fragment -----------------------------

def test_get_path_defaults_to_slash():
    assert get_path("") == "/"
    assert get_path("https://a.com") == "/"


def test_get_path_returns_path():
    assert get_path("https://a.com/a/b") == "/a/b"


def test_get_query_string_empty():
    assert get_query_string("https://a.com/p") == ""


def test_get_query_string_returns_query():
    assert get_query_string("https://a.com/p?a=1&b=2") == "a=1&b=2"


def test_get_fragment_empty():
    assert get_fragment("https://a.com/p") == ""


def test_get_fragment_returns_fragment():
    assert get_fragment("https://a.com/p#frag") == "frag"


# --- extract_subdomain / get_tld --------------------------------------------

def test_extract_subdomain_multi_level():
    assert extract_subdomain("https://a.b.c.com/p") == "a.b"


def test_extract_subdomain_none():
    # two-level domain has no subdomain
    assert extract_subdomain("https://a.com/p") == ""
    assert extract_subdomain("") == ""


def test_get_tld_returns_last_label():
    assert get_tld("https://a.b.co.uk/p") == "uk"
    assert get_tld("https://a.com/p") == "com"
    assert get_tld("") == ""


# --- get_url_depth ----------------------------------------------------------

def test_get_url_depth_empty_and_root():
    assert get_url_depth("") == 0
    assert get_url_depth("https://a.com/") == 0
    assert get_url_depth("https://a.com") == 0


def test_get_url_depth_counts_segments():
    assert get_url_depth("https://a.com/a") == 1
    assert get_url_depth("https://a.com/a/b/c") == 3


# --- is_same_domain / is_internal_link --------------------------------------

def test_is_same_domain_true_and_false():
    assert is_same_domain("https://a.com/x", "https://a.com/y") is True
    assert is_same_domain("https://a.com", "https://b.com") is False


def test_is_internal_link_delegates():
    assert is_internal_link("https://a.com/x", "https://a.com/base") is True
    assert is_internal_link("https://b.com/x", "https://a.com/base") is False


# --- urls_are_equivalent ----------------------------------------------------

def test_urls_are_equivalent_true():
    assert urls_are_equivalent(
        "https://a.com/P?b=2&a=1#f", "https://a.com/p?a=1&b=2"
    ) is True


def test_urls_are_equivalent_false_distinct():
    assert urls_are_equivalent("https://a.com/p", "https://a.com/q") is False


def test_urls_are_equivalent_non_normalizable_never_equivalent():
    # contract: "A URL that cannot be normalized ... normalizes to None and is
    # never equivalent to anything, so two distinct non-normalizable URLs are
    # not reported as equivalent."
    assert urls_are_equivalent("ftp://a.com", "ftp://a.com") is False
    assert urls_are_equivalent("", "") is False
    assert urls_are_equivalent("ftp://a.com", "https://a.com") is False


# --- remove_query_params ----------------------------------------------------

def test_remove_query_params_specific():
    assert remove_query_params("https://a.com/p?a=1&b=2&c=3", ["b"]) == "https://a.com/p?a=1&c=3"


def test_remove_query_params_none_returns_unchanged():
    assert remove_query_params("https://a.com/p?a=1", None) == "https://a.com/p?a=1"
    assert remove_query_params("https://a.com/p?a=1", []) == "https://a.com/p?a=1"


def test_remove_query_params_removes_all_requested():
    assert remove_query_params("https://a.com/p?a=1&b=2", ["a", "b"]) == "https://a.com/p"


def test_remove_query_params_preserves_fragment():
    assert remove_query_params("https://a.com/p?a=1&b=2#f", ["a"]) == "https://a.com/p?b=2#f"


# --- strip_tracking_params --------------------------------------------------

def test_strip_tracking_params_removes_utm_and_friends():
    assert strip_tracking_params("https://a.com/p?utm_source=x&keep=1") == "https://a.com/p?keep=1"


def test_strip_tracking_params_removes_all_tracking():
    url = "https://a.com/p?utm_source=x&utm_medium=y&fbclid=z&gclid=w&keep=1"
    assert strip_tracking_params(url) == "https://a.com/p?keep=1"


def test_strip_tracking_params_no_tracking_unchanged():
    assert strip_tracking_params("https://a.com/p?keep=1") == "https://a.com/p?keep=1"


def test_strip_tracking_params_empty_query():
    assert strip_tracking_params("https://a.com/p") == "https://a.com/p"


# --- url_to_path ------------------------------------------------------------

def test_url_to_path_empty():
    assert url_to_path("") == ""


def test_url_to_path_root_uses_index():
    # contract: empty path -> "index"
    assert url_to_path("https://a.com/") == "a.com_index"
    assert url_to_path("https://a.com") == "a.com_index"


def test_url_to_path_sanitizes_special_chars():
    # contract: "filesystem-safe path" - non [a-zA-Z0-9_-] -> "_"
    assert url_to_path("https://a.com/a/b/c.html") == "a.com_a_b_c_html"


def test_url_to_path_sanitizes_query_and_fragment():
    # query/fragment are not part of the path
    assert url_to_path("https://a.com/p?q=1#f") == "a.com_p"


# --- join_urls --------------------------------------------------------------

def test_join_urls_full_url_returned_as_is():
    assert join_urls("https://a.com/x", "https://b.com/y") == "https://b.com/y"


def test_join_urls_absolute_path_replaces():
    # contract: "If relative starts with /, it replaces the path."
    assert join_urls("https://a.com/x", "/abs") == "https://a.com/abs"


def test_join_urls_relative_appended():
    # contract: "If base ends with a path (not /), relative paths are appended"
    assert join_urls("https://a.com/x", "rel") == "https://a.com/x/rel"


def test_join_urls_relative_with_slash_base():
    assert join_urls("https://a.com/x/", "rel") == "https://a.com/x/rel"


def test_join_urls_relative_root_path():
    assert join_urls("https://a.com/x", "/") == "https://a.com/"


# --- is_canonical -----------------------------------------------------------

def test_is_canonical_true_when_already_normalized():
    assert is_canonical("https://a.com/p") is True


def test_is_canonical_false_when_not_normalized():
    assert is_canonical("https://a.com/P") is False
    assert is_canonical("https://a.com/p?b=2&a=1") is False


# --- end-to-end CLI run -----------------------------------------------------

def test_end_to_end_cli_init_and_search_empty_index(tmp_path):
    """End-to-end: init + search on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner
    from personal_index.cli import main

    runner = CliRunner()
    dd = str(tmp_path / "data")
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "Initialized" in r.output

    r = runner.invoke(main, ["search", "python", "--data-dir", dd, "--format", "json"])
    assert r.exit_code == 0, r.output
    assert "No indexed content found" in r.output
