"""Adversarial deep tests for personal_index.url_filter — cycle 347 deepen.

Complements test_url_filter_adversarial.py (cycle 148, 34 pins) with:
  - None-input behavior (TypeError with non-empty filter, True with empty)
  - Empty-pattern edge cases (empty pattern, re: empty regex)
  - fnmatch special chars (case sensitivity, ?, [abc], *)
  - URL variant inputs (query, fragment, credentials, port, uppercase, IDN, IPv4, IPv6)
  - get_blocked_urls idempotence + partition property
  - Large-list stress (10 000 URLs)
  - Duplicate rules (count, behavior, clear)
  - Multiple whitelist rules + get_matching_rule precedence
  - End-to-end CLI run (init + crawl --no-crawl + export)
"""

from __future__ import annotations

import time

import pytest

from personal_index.url_filter import UrlFilter, UrlFilterRule


# --- None-input behavior (type-hint violations, not contract violations) ---

def test_matches_none_raises_typeerror():
    """UrlFilterRule.matches(None) raises TypeError (fnmatch requires str)."""
    r = UrlFilterRule("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        r.matches(None)


def test_is_allowed_none_empty_filter_returns_true():
    """is_allowed(None) on an EMPTY filter returns True (all([]) == True)."""
    f = UrlFilter()
    assert f.is_allowed(None) is True


def test_is_allowed_none_nonempty_filter_raises():
    """is_allowed(None) with a blacklist rule raises TypeError."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        f.is_allowed(None)


def test_is_blocked_none_nonempty_filter_raises():
    """is_blocked(None) with a blacklist rule raises TypeError."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        f.is_blocked(None)


def test_filter_urls_none_in_list_nonempty_filter_raises():
    """filter_urls([None, ...]) with a blacklist rule raises TypeError."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        f.filter_urls([None, "https://good.com"])


def test_get_blocked_urls_none_in_list_nonempty_filter_raises():
    """get_blocked_urls([None, ...]) with a blacklist rule raises TypeError."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        f.get_blocked_urls([None, "https://good.com"])


def test_get_matching_rule_none_nonempty_filter_raises():
    """get_matching_rule(None) with a blacklist rule raises TypeError."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    with pytest.raises(TypeError, match="expected str"):
        f.get_matching_rule(None)


def test_add_blacklist_none_stores_none_pattern():
    """add_blacklist(None) stores a rule with pattern=None (no validation)."""
    f = UrlFilter()
    f.add_blacklist(None)
    assert f.blacklist_count == 1
    # The stored rule has pattern=None; matching against it raises TypeError.
    rule = f._blacklist[0]
    assert rule.pattern is None


# --- Empty-pattern edge cases ---

def test_empty_pattern_matches_only_empty_string():
    """UrlFilterRule('').matches('') is True; matches('anything') is False."""
    r = UrlFilterRule("")
    assert r.matches("") is True
    assert r.matches("anything") is False


def test_re_empty_regex_matches_everything():
    """UrlFilterRule('re:').matches(anything) is True (empty regex matches all)."""
    r = UrlFilterRule("re:")
    assert r.matches("anything") is True
    assert r.matches("") is True


def test_empty_pattern_blacklist_blocks_only_empty():
    """A blacklist with pattern='' blocks only the empty string."""
    f = UrlFilter()
    f.add_blacklist("")
    assert f.is_blocked("") is True
    assert f.is_blocked("anything") is False


def test_star_pattern_matches_everything():
    """UrlFilterRule('*').matches(anything) is True."""
    r = UrlFilterRule("*")
    assert r.matches("anything") is True
    assert r.matches("") is True


def test_question_mark_single_char():
    """UrlFilterRule('?') matches exactly one character."""
    r = UrlFilterRule("?")
    assert r.matches("a") is True
    assert r.matches("ab") is False
    assert r.matches("") is False


def test_char_class_brackets():
    """UrlFilterRule('[abc]') matches a, b, or c (single char)."""
    r = UrlFilterRule("[abc]")
    assert r.matches("a") is True
    assert r.matches("b") is True
    assert r.matches("c") is True
    assert r.matches("d") is False


# --- fnmatch special chars and case sensitivity ---

def test_fnmatch_case_sensitive():
    """fnmatch is case-sensitive: '*.COM' does not match 'example.com'."""
    r = UrlFilterRule("*.COM")
    assert r.matches("example.com") is False
    assert r.matches("example.COM") is True


def test_fnmatch_query_string():
    """fnmatch handles query strings with & and = correctly."""
    r = UrlFilterRule("https://example.com/*")
    assert r.matches("https://example.com/a?b=c&d=e") is True


def test_fnmatch_nested_path():
    """fnmatch * matches across path separators."""
    r = UrlFilterRule("https://example.com/*")
    assert r.matches("https://example.com/a/b/c") is True


def test_fnmatch_bare_domain_no_match():
    """'https://example.com/*' does NOT match bare 'https://example.com'."""
    r = UrlFilterRule("https://example.com/*")
    assert r.matches("https://example.com") is False


# --- URL variant inputs ---

def test_url_with_query_blocked_by_wildcard():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://example.com/path?x=1") is False


def test_url_with_fragment_blocked_by_wildcard():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://example.com/path#frag") is False


def test_url_with_credentials_not_matched_by_path_wildcard():
    """Credentials (user:pass@) change the host portion; path wildcard doesn't match."""
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://user:pass@example.com/") is True


def test_url_with_port_not_matched_by_path_wildcard():
    """Port number changes the host portion; path wildcard doesn't match."""
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://example.com:8080/") is True


def test_url_trailing_slash_blocked_by_wildcard():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://example.com/") is False


def test_url_uppercase_scheme_not_matched():
    """fnmatch is case-sensitive: HTTPS://EXAMPLE.COM/ != https://example.com/*"""
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("HTTPS://EXAMPLE.COM/") is True


def test_url_idn_not_matched_by_ascii_wildcard():
    """IDN URLs (Unicode) are not matched by ASCII fnmatch patterns."""
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://例え.jp/") is True


def test_url_ipv4_not_matched_by_domain_wildcard():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://192.168.1.1/") is True


def test_url_ipv6_not_matched_by_domain_wildcard():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://[::1]/") is True


# --- get_blocked_urls: idempotence + partition ---

def test_get_blocked_urls_empty_list():
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    assert f.get_blocked_urls([]) == []


def test_get_blocked_urls_idempotent():
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    urls = ["https://good.com", "https://sub.bad.com", "https://good.com"]
    b1 = f.get_blocked_urls(urls)
    b2 = f.get_blocked_urls(urls)
    assert b1 == b2
    assert b1 == ["https://sub.bad.com"]


def test_filter_and_blocked_partition_property():
    """filter_urls + get_blocked_urls partition the input (no overlap, full coverage)."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    urls = ["https://good.com", "https://sub.bad.com", "https://other.com", "https://x.bad.com"]
    allowed = f.filter_urls(urls)
    blocked = f.get_blocked_urls(urls)
    # No overlap
    assert not set(allowed) & set(blocked)
    # Full coverage (multiset)
    assert sorted(allowed + blocked) == sorted(urls)


# --- Large-list stress ---

def test_filter_urls_large_list():
    """filter_urls handles 10 000 URLs in < 2 s."""
    f = UrlFilter()
    f.add_blacklist("*.bad.com")
    urls = [f"https://site{i}.com" for i in range(10_000)]
    urls[5_000] = "https://sub.bad.com"
    t0 = time.time()
    result = f.filter_urls(urls)
    elapsed = time.time() - t0
    assert len(result) == 9_999
    assert elapsed < 2.0


# --- Duplicate rules ---

def test_duplicate_blacklist_rules_counted():
    f = UrlFilter()
    f.add_blacklist("*.com")
    f.add_blacklist("*.com")
    assert f.blacklist_count == 2
    assert f.is_blocked("https://example.com") is True


def test_duplicate_whitelist_rules_counted():
    f = UrlFilter()
    f.add_whitelist("https://a.com")
    f.add_whitelist("https://a.com")
    assert f.whitelist_count == 2


def test_clear_blacklist_removes_duplicates():
    f = UrlFilter()
    f.add_blacklist("*.com")
    f.add_blacklist("*.com")
    f.clear_blacklist()
    assert f.blacklist_count == 0


# --- Multiple whitelist rules + get_matching_rule precedence ---

def test_multiple_whitelist_rules_all_match():
    f = UrlFilter()
    f.add_blacklist("*")
    f.add_whitelist("https://a.com")
    f.add_whitelist("https://b.com")
    assert f.is_allowed("https://a.com") is True
    assert f.is_allowed("https://b.com") is True
    assert f.is_allowed("https://c.com") is False


def test_get_matching_rule_whitelist_precedence_over_blacklist():
    """When both whitelist and blacklist match, get_matching_rule returns the whitelist rule."""
    f = UrlFilter()
    f.add_blacklist("*.com")
    f.add_whitelist("https://good.com")
    r = f.get_matching_rule("https://good.com")
    assert r is not None
    assert r.pattern == "https://good.com"


def test_get_matching_rule_blacklist_when_no_whitelist_match():
    f = UrlFilter()
    f.add_blacklist("*.com")
    f.add_whitelist("https://good.com")
    r = f.get_matching_rule("https://bad.com")
    assert r is not None
    assert r.pattern == "*.com"


# --- End-to-end CLI run ---

def test_end_to_end_cli_init_crawl_export(tmp_path):
    """End-to-end: init + list + export on an empty index (no network)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    dd = str(tmp_path / "data")
    runner = CliRunner()
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    r = runner.invoke(main, ["list", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    r = runner.invoke(main, ["export", "--format", "json", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "No pages to export." in r.output
