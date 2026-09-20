"""Adversarial deep tests for personal_index.url_filter (UrlFilterRule / UrlFilter).

Cycle 148 - VALIDATOR probe.

Targets (never-probed subsystem in tests/deep/):
  - UrlFilterRule.matches: exact match, fnmatch wildcards, re: regex (SEARCH
    semantics, not match), invalid regex -> False, precedence order
    (exact before fnmatch before regex), empty/whitespace/unicode inputs.
  - UrlFilter.is_allowed / is_blocked: whitelist precedence over blacklist,
    empty filter allows everything, is_blocked == not is_allowed.
  - filter_urls / get_blocked_urls: partition property, order + duplicate
    preservation, empty list, idempotence.
  - get_matching_rule: whitelist-first, insertion order within each list,
    identity (not a copy), None when no match, pure accessor (no mutation).
  - blacklist_count / whitelist_count / clear / clear_blacklist / clear_whitelist.
  - one end-to-end CLI run (installed entry point).
"""

from __future__ import annotations


from personal_index.url_filter import UrlFilter, UrlFilterRule


# --- UrlFilterRule.matches: exact-contract pins ----------------------------

def test_matches_exact():
    r = UrlFilterRule("https://example.com/a")
    assert r.matches("https://example.com/a") is True
    assert r.matches("https://example.com/b") is False


def test_matches_fnmatch_wildcard():
    r = UrlFilterRule("*.com")
    assert r.matches("example.com") is True
    assert r.matches("example.org") is False


def test_matches_fnmatch_prefix_wildcard():
    r = UrlFilterRule("https://example.com/*")
    assert r.matches("https://example.com/anything") is True
    assert r.matches("https://other.com/anything") is False


def test_matches_regex_search_not_match():
    # re: uses re.search (substring), NOT re.match (anchored at start).
    r = UrlFilterRule("re:example")
    assert r.matches("https://example.com") is True  # substring, not at start
    assert r.matches("https://nope.com") is False


def test_matches_regex_anchored():
    r = UrlFilterRule("re:^https://example\\.com$")
    assert r.matches("https://example.com") is True
    assert r.matches("https://example.com/x") is False


def test_matches_invalid_regex_returns_false():
    # re.error must be swallowed -> False, not raised.
    r = UrlFilterRule("re:[unclosed")
    assert r.matches("https://example.com") is False


def test_matches_empty_regex_matches_everything():
    # re: with empty pattern -> re.search("", url) is always truthy.
    r = UrlFilterRule("re:")
    assert r.matches("https://example.com") is True
    assert r.matches("") is True


def test_matches_empty_string_input():
    r = UrlFilterRule("*.com")
    assert r.matches("") is False
    r2 = UrlFilterRule("")
    # exact match: pattern "" == url "" -> True
    assert r2.matches("") is True


def test_matches_whitespace_input():
    r = UrlFilterRule("  ")
    assert r.matches("  ") is True  # exact
    assert r.matches(" ") is False


def test_matches_unicode_input():
    r = UrlFilterRule("re:привет")
    assert r.matches("https://example.com/привет") is True
    assert r.matches("https://example.com/hello") is False


def test_matches_precedence_exact_before_fnmatch():
    # A pattern that is a literal exact string AND contains no wildcard:
    # exact match path returns True before fnmatch is consulted.
    r = UrlFilterRule("https://example.com")
    assert r.matches("https://example.com") is True


def test_matches_regex_pattern_not_matched_by_fnmatch_first():
    # "re:example" has no fnmatch wildcard, so fnmatch(url, "re:example") is
    # False for a normal url; the regex path then decides.
    r = UrlFilterRule("re:example")
    assert r.matches("https://example.com") is True
    # a url that literally equals the pattern string would hit exact/fnmatch
    assert r.matches("re:example") is True  # exact match on the raw string


# --- UrlFilter.is_allowed / is_blocked: whitelist precedence ---------------

def test_empty_filter_allows_everything():
    f = UrlFilter()
    assert f.is_allowed("https://example.com") is True
    assert f.is_blocked("https://example.com") is False


def test_blacklist_blocks():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    assert f.is_allowed("https://spam.com/x") is False
    assert f.is_blocked("https://spam.com/x") is True
    assert f.is_allowed("https://good.com") is True


def test_whitelist_takes_precedence_over_blacklist():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    f.add_whitelist("https://example.com/allowed")
    # whitelist exact match wins even though blacklist wildcard also matches
    assert f.is_allowed("https://example.com/allowed") is True
    assert f.is_blocked("https://example.com/allowed") is False
    # non-whitelisted example.com url is still blocked
    assert f.is_allowed("https://example.com/blocked") is False


def test_whitelist_wins_regardless_of_insertion_order():
    f = UrlFilter()
    f.add_whitelist("https://example.com/ok")
    f.add_blacklist("https://example.com/*")
    assert f.is_allowed("https://example.com/ok") is True


def test_is_blocked_is_inverse_of_is_allowed():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    f.add_whitelist("https://spam.com/ok")
    for url in ["https://spam.com/x", "https://spam.com/ok", "https://good.com"]:
        assert f.is_blocked(url) is not f.is_allowed(url)


def test_multiple_blacklist_any_match_blocks():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_blacklist("https://b.com/*")
    assert f.is_allowed("https://a.com/x") is False
    assert f.is_allowed("https://b.com/x") is False
    assert f.is_allowed("https://c.com/x") is True


# --- filter_urls / get_blocked_urls: partition + order + idempotence -------

def test_filter_urls_empty_list():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    assert f.filter_urls([]) == []
    assert f.get_blocked_urls([]) == []


def test_filter_urls_preserves_order_and_duplicates():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    urls = [
        "https://good.com/1",
        "https://spam.com/1",
        "https://good.com/1",  # duplicate allowed
        "https://spam.com/2",
        "https://good.com/2",
    ]
    assert f.filter_urls(urls) == [
        "https://good.com/1",
        "https://good.com/1",
        "https://good.com/2",
    ]
    assert f.get_blocked_urls(urls) == [
        "https://spam.com/1",
        "https://spam.com/2",
    ]


def test_filter_and_blocked_partition_input():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    f.add_whitelist("https://spam.com/ok")
    urls = [
        "https://spam.com/ok",
        "https://spam.com/x",
        "https://good.com",
        "https://spam.com/y",
    ]
    allowed = f.filter_urls(urls)
    blocked = f.get_blocked_urls(urls)
    # every input url appears in exactly one of the two lists
    assert sorted(allowed + blocked) == sorted(urls)
    assert not set(allowed) & set(blocked)


def test_filter_urls_idempotent():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    urls = ["https://good.com", "https://spam.com", "https://good.com/x"]
    once = f.filter_urls(urls)
    twice = f.filter_urls(once)
    assert once == twice


# --- get_matching_rule: exact-contract pins --------------------------------

def test_get_matching_rule_none_when_empty():
    f = UrlFilter()
    assert f.get_matching_rule("https://example.com") is None


def test_get_matching_rule_none_when_no_match():
    f = UrlFilter()
    f.add_blacklist("https://spam.com/*")
    assert f.get_matching_rule("https://good.com") is None


def test_get_matching_rule_returns_whitelist_first():
    f = UrlFilter()
    f.add_blacklist("https://example.com/*")
    f.add_whitelist("https://example.com/*")
    rule = f.get_matching_rule("https://example.com/x")
    # whitelist scanned first -> the whitelist rule is returned
    assert rule is f._whitelist[0]
    assert rule is not f._blacklist[0]


def test_get_matching_rule_insertion_order_within_blacklist():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_blacklist("https://a.com/*")
    rule = f.get_matching_rule("https://a.com/x")
    assert rule is f._blacklist[0]  # first inserted, not second


def test_get_matching_rule_identity_not_copy():
    f = UrlFilter()
    f.add_blacklist("re:example")
    rule = f.get_matching_rule("https://example.com")
    assert rule is f._blacklist[0]
    assert isinstance(rule, UrlFilterRule)


def test_get_matching_rule_is_pure_accessor():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_whitelist("https://b.com/*")
    bl_before = list(f._blacklist)
    wl_before = list(f._whitelist)
    f.get_matching_rule("https://a.com/x")
    f.get_matching_rule("https://b.com/x")
    f.get_matching_rule("https://c.com/x")
    assert f._blacklist == bl_before
    assert f._whitelist == wl_before


# --- counts / clear --------------------------------------------------------

def test_counts_empty():
    f = UrlFilter()
    assert f.blacklist_count == 0
    assert f.whitelist_count == 0


def test_counts_after_add():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_blacklist("https://b.com/*")
    f.add_whitelist("*.c.com")
    assert f.blacklist_count == 2
    assert f.whitelist_count == 1


def test_clear_resets_both():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_whitelist("https://b.com/*")
    f.clear()
    assert f.blacklist_count == 0
    assert f.whitelist_count == 0
    assert f.is_allowed("https://a.com") is True


def test_clear_blacklist_only():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_whitelist("https://b.com/*")
    f.clear_blacklist()
    assert f.blacklist_count == 0
    assert f.whitelist_count == 1


def test_clear_whitelist_only():
    f = UrlFilter()
    f.add_blacklist("https://a.com/*")
    f.add_whitelist("https://b.com/*")
    f.clear_whitelist()
    assert f.blacklist_count == 1
    assert f.whitelist_count == 0


# --- end-to-end CLI ---------------------------------------------------------

def test_end_to_end_cli_init_and_export(tmp_path):
    """End-to-end: init + export on an empty index (exit 0, no crash)."""
    from click.testing import CliRunner

    from personal_index.cli import main

    dd = str(tmp_path / "data")
    runner = CliRunner()
    r = runner.invoke(main, ["init", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    r = runner.invoke(main, ["export", "--format", "json", "--data-dir", dd])
    assert r.exit_code == 0, r.output
    assert "No indexed content to export." in r.output
