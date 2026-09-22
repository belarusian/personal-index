"""Adversarial deep tests for personal_index.url_utils.get_tld - ARCH-61 armor.

The existing tests/deep/test_url_utils_adversarial.py (qa142, 2026-09-07)
predates the ARCH-61 behavioral change (2026-09-13, "get_tld returns '' for
dotless hosts + single-label-only docstring"). That change made get_tld return
"" for dotless hosts (localhost, intranet) instead of the whole host, and
reworded the docstring to state the single-label-only contract. The qa142 file
pins only the two-label case (a.b.co.uk -> 'uk') and the empty case; it does
NOT pin the dotless-host -> "" behavior, so a regression that resurrects the
pre-ARCH-61 "whole host as TLD" behavior would pass the qa142 suite.

This file pins the ARCH-61 contract against current main (re-derived by calling
get_tld directly and reading the real value):

  - dotless hosts (localhost, intranet, bare single-label) -> ""
  - two-label TLDs still return the second-level label (uk, au) - the
    documented single-label-only limitation is preserved, not "fixed"
  - empty / no-netloc / scheme-only -> ""
  - property: the result is always "" or a single dot-free label (never a
    multi-label string like 'co.uk')
  - stability: get_tld is not strictly idempotent (get_tld("com") -> ""), but a
    second application always yields "" (the first result is a bare label)

Contract source: personal_index/url_utils.py get_tld docstring (post-ARCH-61)
and tickets/ARCH-61.md.
"""

from __future__ import annotations

import pytest

from personal_index.url_utils import get_tld


# --- ARCH-61 behavioral: dotless hosts return "" (not the whole host) --------


def test_get_tld_dotless_localhost_returns_empty():
    # ARCH-61: a bare hostname has no TLD -> "" (pre-ARCH-61 returned 'localhost')
    assert get_tld("http://localhost:8080/x") == ""
    assert get_tld("http://localhost") == ""
    assert get_tld("https://localhost/p") == ""


def test_get_tld_dotless_intranet_returns_empty():
    # ARCH-61: dotless intranet host -> "" (pre-ARCH-61 returned 'intranet')
    assert get_tld("http://intranet/x") == ""
    assert get_tld("https://intranet") == ""


def test_get_tld_dotless_bare_single_label_returns_empty():
    # Any single-label host (no dot) has no TLD -> ""
    assert get_tld("http://host") == ""
    assert get_tld("http://myhost:9000/a/b") == ""


def test_get_tld_two_label_still_returns_second_level():
    # The single-label-only limitation is PRESERVED (not fixed): co.uk -> 'uk'
    assert get_tld("https://a.b.co.uk/p") == "uk"
    assert get_tld("https://example.com.au") == "au"
    assert get_tld("https://www.gov.uk/x") == "uk"


def test_get_tld_single_label_tld_returns_tld():
    # The correct case: single-label TLDs return the TLD
    assert get_tld("https://a.com/p") == "com"
    assert get_tld("https://a.org") == "org"
    assert get_tld("https://a.net/x") == "net"


def test_get_tld_deep_subdomain_returns_last_label():
    # Multi-level subdomain: still the last dot-label
    assert get_tld("https://a.b.c.d.com/p") == "com"


def test_get_tld_empty_and_no_netloc_return_empty():
    assert get_tld("") == ""
    assert get_tld("not a url") == ""
    assert get_tld("https://") == ""


def test_get_tld_trailing_dot_host_returns_empty():
    # 'a.com.' -> extract_domain lowercases/strips; trailing-dot host has no
    # resolvable TLD on current main -> "" (re-derived against actual result)
    assert get_tld("https://a.com./p") == ""


def test_get_tld_ipv6_literal_returns_empty():
    # IPv6 literal host has no dot-label TLD -> "" (re-derived against actual)
    assert get_tld("http://[::1]:8080/p") == ""


# --- property: result is always "" or a single dot-free label ----------------


@pytest.mark.parametrize(
    "url",
    [
        "https://a.com",
        "https://a.b.co.uk",
        "http://localhost:8080/x",
        "http://intranet",
        "not a url",
        "",
        "https://a.com./p",
        "https://[::1]:8080/p",
        "https://a..com/p",
        "https://a.b.c.d.com/p",
        "http://127.0.0.1:8080/p",
        "https://sub.domain.example.org/deep/path",
    ],
)
def test_get_tld_result_is_empty_or_single_label(url):
    # Property: the result never contains a dot (never a multi-label string
    # like 'co.uk' or a whole host like 'localhost')
    result = get_tld(url)
    assert isinstance(result, str)
    assert "." not in result, f"get_tld({url!r}) returned multi-label {result!r}"


# --- stability: a second application always yields "" -----------------------


@pytest.mark.parametrize(
    "url",
    [
        "https://a.com",
        "https://a.b.co.uk",
        "http://localhost:8080/x",
        "http://intranet",
        "https://a.b.c.d.com/p",
        "",
    ],
)
def test_get_tld_second_application_is_empty(url):
    # get_tld is NOT strictly idempotent (get_tld("com") -> "" != "com"), but
    # the result of the first application is always a bare dot-free label (or
    # ""), so a SECOND application always yields "" - a stable fixed point.
    once = get_tld(url)
    twice = get_tld(once)
    assert twice == ""
    # And the first application is deterministic (same input -> same output).
    assert once == get_tld(url)
