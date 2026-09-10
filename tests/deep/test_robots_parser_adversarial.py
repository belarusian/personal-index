"""Adversarial deep tests for personal_index.robots_parser.

Cycle 191 (VALIDATOR). This module is the DEAD duplicate of
personal_index.crawler.robots (see docs/content-robots.md, "contract hole 1"
- it is never imported by product code). Its pattern-matching semantics
(wildcard substring match, $-anchor checked before wildcard) are DOCUMENTED
design differences from the live crawler module, so they are pinned here as
armor (expected behavior), not filed as defects.

These tests attack the public API (parse_robots_txt, is_allowed,
RobotsPolicy.can_fetch, _path_matches) with guard inputs (None-adjacent /
empty / whitespace / unicode / malformed / out-of-range), boundary lengths,
error/rollback contracts, defensive loads, ordering/stability, idempotence,
and property checks. No CLI entry point exists for this module (standalone),
so the "end-to-end" path is the full parse -> can_fetch -> is_allowed chain.
"""

from __future__ import annotations

import pytest

from personal_index.robots_parser import (
    RobotsPolicy,
    RobotsRule,
    is_allowed,
    parse_robots_txt,
)

BASE = "https://example.com"


def _policy(text: str, base: str = BASE) -> RobotsPolicy:
    return parse_robots_txt(text, base)


# ---------------------------------------------------------------------------
# parse_robots_txt guard inputs (defensive loads)
# ---------------------------------------------------------------------------
class TestParseGuardInputs:
    def test_empty_text(self):
        p = _policy("")
        assert p.domain == "example.com"
        assert p.rules == []
        assert p.crawl_delay == 0.0
        assert p.sitemap_urls == []

    def test_whitespace_only_text(self):
        p = _policy("   \n\t\n  \n")
        assert p.rules == []
        assert p.crawl_delay == 0.0
        assert p.sitemap_urls == []

    def test_unicode_text_no_crash(self):
        p = _policy("User-agent: *\nDisallow: /café/\n")
        assert len(p.rules) == 1
        assert p.rules[0].pattern == "/café/"

    def test_unicode_user_agent(self):
        p = _policy("User-agent: бот\nDisallow: /x\n")
        assert p.rules[0].user_agent == "бот"

    def test_line_without_colon_ignored(self):
        p = _policy("garbageline\nUser-agent: *\nDisallow: /x\n")
        assert len(p.rules) == 1
        assert p.rules[0].pattern == "/x"

    def test_empty_base_url(self):
        p = _policy("User-agent: *\nDisallow: /x\n", base="")
        assert p.domain == ""
        assert len(p.rules) == 1

    def test_base_url_without_netloc(self):
        p = _policy("User-agent: *\nDisallow: /x\n", base="not-a-url")
        assert p.domain == ""
        assert len(p.rules) == 1

    def test_base_url_with_port(self):
        p = _policy("User-agent: *\nDisallow: /x\n", base="https://e.com:8080")
        assert p.domain == "e.com:8080"

    def test_crlf_line_endings(self):
        p = _policy("User-agent: *\r\nDisallow: /x\r\n")
        assert len(p.rules) == 1
        assert p.rules[0].pattern == "/x"

    def test_comment_lines_ignored(self):
        p = _policy("# comment\n  # indented comment\nUser-agent: *\nDisallow: /x\n")
        assert len(p.rules) == 1

    def test_directive_before_user_agent_ignored(self):
        # disallow with no current agent must not create a rule
        p = _policy("Disallow: /x\nUser-agent: *\nDisallow: /y\n")
        assert [r.pattern for r in p.rules] == ["/y"]


# ---------------------------------------------------------------------------
# crawl-delay contract (ValueError suppressed, not raised)
# ---------------------------------------------------------------------------
class TestCrawlDelay:
    def test_non_numeric_suppressed(self):
        p = _policy("User-agent: *\nCrawl-delay: abc\n")
        assert p.crawl_delay == 0.0

    def test_negative_accepted_as_float(self):
        # documented: "the last Crawl-delay: value that parsed as a float"
        p = _policy("User-agent: *\nCrawl-delay: -5\n")
        assert p.crawl_delay == -5.0

    def test_last_wins(self):
        p = _policy("User-agent: *\nCrawl-delay: 1\nCrawl-delay: 2.5\n")
        assert p.crawl_delay == 2.5

    def test_empty_value_suppressed(self):
        p = _policy("User-agent: *\nCrawl-delay:\n")
        assert p.crawl_delay == 0.0

    def test_scientific_notation(self):
        p = _policy("User-agent: *\nCrawl-delay: 1e1\n")
        assert p.crawl_delay == 10.0


# ---------------------------------------------------------------------------
# sitemap contract
# ---------------------------------------------------------------------------
class TestSitemap:
    def test_multiple_sitemaps_in_order(self):
        p = _policy("Sitemap: https://e.com/s1\nSitemap: https://e.com/s2\n")
        assert p.sitemap_urls == ["https://e.com/s1", "https://e.com/s2"]

    def test_sitemap_empty_value_ignored(self):
        p = _policy("Sitemap:\n")
        assert p.sitemap_urls == []

    def test_sitemap_without_agent(self):
        p = _policy("Sitemap: https://e.com/s\n")
        assert p.sitemap_urls == ["https://e.com/s"]


# ---------------------------------------------------------------------------
# disallow/allow value handling
# ---------------------------------------------------------------------------
class TestRuleValues:
    def test_disallow_empty_value_no_rule(self):
        p = _policy("User-agent: *\nDisallow:\n")
        assert p.rules == []

    def test_allow_empty_value_no_rule(self):
        p = _policy("User-agent: *\nAllow:\n")
        assert p.rules == []

    def test_duplicate_user_agent_keeps_both(self):
        p = _policy("User-agent: bot\nDisallow: /a\nUser-agent: bot\nDisallow: /b\n")
        assert [r.pattern for r in p.rules] == ["/a", "/b"]
        assert all(r.user_agent == "bot" for r in p.rules)

    def test_rules_preserve_file_order(self):
        p = _policy(
            "User-agent: a\nDisallow: /1\n"
            "User-agent: b\nDisallow: /2\n"
            "User-agent: a\nDisallow: /3\n"
        )
        assert [(r.user_agent, r.pattern) for r in p.rules] == [
            ("a", "/1"),
            ("b", "/2"),
            ("a", "/3"),
        ]


# ---------------------------------------------------------------------------
# can_fetch: path normalization
# ---------------------------------------------------------------------------
class TestPathNormalization:
    def test_empty_path_becomes_root(self):
        p = _policy("User-agent: *\nDisallow: /\n")
        assert p.can_fetch("https://example.com") is False

    def test_query_ignored(self):
        p = _policy("User-agent: *\nDisallow: /secret\n")
        assert p.can_fetch("https://example.com/secret?x=1") is False

    def test_fragment_ignored(self):
        p = _policy("User-agent: *\nDisallow: /secret\n")
        assert p.can_fetch("https://example.com/secret#frag") is False

    def test_query_and_fragment_ignored(self):
        p = _policy("User-agent: *\nDisallow: /secret\n")
        assert p.can_fetch("https://example.com/secret?x=1#frag") is False


# ---------------------------------------------------------------------------
# can_fetch: prefix matching (no slash-boundary)
# ---------------------------------------------------------------------------
class TestPrefixMatching:
    def test_prefix_exact(self):
        p = _policy("User-agent: *\nDisallow: /a\n")
        assert p.can_fetch("https://example.com/a") is False

    def test_prefix_subpath(self):
        p = _policy("User-agent: *\nDisallow: /a\n")
        assert p.can_fetch("https://example.com/a/b") is False

    def test_prefix_no_slash_boundary(self):
        # /a does NOT match /ab (prefix match, not word boundary)
        p = _policy("User-agent: *\nDisallow: /a\n")
        assert p.can_fetch("https://example.com/ab") is True

    def test_trailing_slash_pattern(self):
        # can_fetch rstrips the pattern, so /a/ becomes /a and matches both
        # /a (exact) and /a/b (prefix)
        p = _policy("User-agent: *\nDisallow: /a/\n")
        assert p.can_fetch("https://example.com/a/b") is False
        assert p.can_fetch("https://example.com/a") is False


# ---------------------------------------------------------------------------
# can_fetch: wildcard semantics (documented design of the dead module)
# ---------------------------------------------------------------------------
class TestWildcardSemantics:
    def test_prefix_wildcard(self):
        p = _policy("User-agent: *\nDisallow: /tmp*\n")
        assert p.can_fetch("https://example.com/tmp/file") is False
        assert p.can_fetch("https://example.com/page") is True

    def test_suffix_wildcard_matches_substring(self):
        # documented: *.pdf matches /x.pdf AND /x.pdfy (substring, no end anchor)
        p = _policy("User-agent: *\nDisallow: *.pdf\n")
        assert p.can_fetch("https://example.com/x.pdf") is False
        assert p.can_fetch("https://example.com/x.pdfy") is False

    def test_bare_star_disallow_matches_all(self):
        p = _policy("User-agent: *\nDisallow: *\n")
        assert p.can_fetch("https://example.com/anything") is False
        assert p.can_fetch("https://example.com/") is False

    def test_dollar_anchor_wildcard_ignored(self):
        # documented: $ branch checked before wildcard, so /*.pdf$ is an
        # exact match on "/*.pdf" (wildcard ignored)
        p = _policy("User-agent: *\nDisallow: /*.pdf$\n")
        assert p.can_fetch("https://example.com/x.pdf") is True
        assert p.can_fetch("https://example.com/x.pdfy") is True


# ---------------------------------------------------------------------------
# can_fetch: $ anchor (exact match)
# ---------------------------------------------------------------------------
class TestDollarAnchor:
    def test_exact_match(self):
        p = _policy("User-agent: *\nDisallow: /search$\n")
        assert p.can_fetch("https://example.com/search") is False

    def test_subpath_not_matched(self):
        p = _policy("User-agent: *\nDisallow: /search$\n")
        assert p.can_fetch("https://example.com/search/page") is True

    def test_bare_dollar_pattern(self):
        # pattern "$" -> strip -> "" -> exact match on "" (never "/")
        p = _policy("User-agent: *\nDisallow: $\n")
        assert p.can_fetch("https://example.com/") is True


# ---------------------------------------------------------------------------
# can_fetch: user-agent selection (specific preferred over wildcard)
# ---------------------------------------------------------------------------
class TestUserAgentSelection:
    def test_default_user_agent_is_personal_index(self):
        p = _policy("User-agent: personal-index\nDisallow: /x\n")
        assert p.can_fetch("https://example.com/x") is False

    def test_case_insensitive_user_agent(self):
        p = _policy("User-agent: PERSONAL-INDEX\nDisallow: /x\n")
        assert p.can_fetch("https://example.com/x") is False

    def test_specific_preferred_over_wildcard(self):
        # documented difference from live crawler: specific wins over wildcard
        p = _policy(
            "User-agent: *\nDisallow: /x\n"
            "User-agent: personal-index\nAllow: /x\n"
        )
        assert p.can_fetch("https://example.com/x") is True

    def test_wildcard_applies_when_no_specific(self):
        p = _policy("User-agent: *\nDisallow: /x\n")
        assert p.can_fetch("https://example.com/x") is False

    def test_unrelated_agent_falls_back_to_wildcard(self):
        p = _policy("User-agent: other\nDisallow: /x\nUser-agent: *\nDisallow: /y\n")
        # personal-index has no specific rule -> wildcard /y applies
        assert p.can_fetch("https://example.com/y") is False
        assert p.can_fetch("https://example.com/x") is True

    def test_no_applicable_rules_default_allow(self):
        p = _policy("User-agent: other\nDisallow: /x\n")
        assert p.can_fetch("https://example.com/x") is True


# ---------------------------------------------------------------------------
# can_fetch: longest-pattern-wins
# ---------------------------------------------------------------------------
class TestLongestPatternWins:
    def test_longer_allow_wins(self):
        p = _policy("User-agent: *\nDisallow: /a\nAllow: /a/b\n")
        assert p.can_fetch("https://example.com/a/b") is True

    def test_longer_disallow_wins(self):
        p = _policy("User-agent: *\nAllow: /a\nDisallow: /a/b\n")
        assert p.can_fetch("https://example.com/a/b") is False

    def test_no_match_default_allow(self):
        p = _policy("User-agent: *\nDisallow: /a\n")
        assert p.can_fetch("https://example.com/b") is True


# ---------------------------------------------------------------------------
# is_allowed wrapper
# ---------------------------------------------------------------------------
class TestIsAllowedWrapper:
    def test_allowed(self):
        p = _policy("User-agent: *\nDisallow: /x\n")
        assert is_allowed("https://example.com/y", p) is True

    def test_disallowed(self):
        p = _policy("User-agent: *\nDisallow: /x\n")
        assert is_allowed("https://example.com/x", p) is False

    def test_custom_user_agent(self):
        p = _policy("User-agent: bot\nDisallow: /x\n")
        assert is_allowed("https://example.com/x", p, user_agent="bot") is False
        assert is_allowed("https://example.com/x", p, user_agent="other") is True


# ---------------------------------------------------------------------------
# idempotence / property checks
# ---------------------------------------------------------------------------
class TestIdempotenceAndProperties:
    def test_parse_is_idempotent(self):
        text = "User-agent: *\nDisallow: /x\nCrawl-delay: 2\nSitemap: https://e.com/s\n"
        assert _policy(text) == _policy(text)

    def test_can_fetch_is_pure(self):
        p = _policy("User-agent: *\nDisallow: /x\n")
        assert p.can_fetch("https://example.com/x") == p.can_fetch("https://example.com/x")

    def test_empty_policy_allows_everything(self):
        p = RobotsPolicy(domain="example.com")
        for url in ("https://example.com/", "https://example.com/a", "https://example.com/a/b"):
            assert p.can_fetch(url) is True

    def test_property_disallow_root_blocks_all(self):
        p = _policy("User-agent: *\nDisallow: /\n")
        for url in ("https://example.com/", "https://example.com/a", "https://example.com/a/b"):
            assert p.can_fetch(url) is False

    def test_rule_dataclass_fields(self):
        r = RobotsRule(user_agent="*", allowed=False, pattern="/x")
        assert (r.user_agent, r.allowed, r.pattern) == ("*", False, "/x")


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
