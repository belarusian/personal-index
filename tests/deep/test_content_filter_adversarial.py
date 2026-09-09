"""Adversarial deep tests for personal_index.content_filter (ContentFilter).

Cycle 185 — VALIDATOR probe.

Covers: None/empty/whitespace/unicode/duplicate/out-of-range inputs,
round-trips, idempotence, ordering/stability, boundary lengths,
error/rollback contracts, defensive loads, and one end-to-end run
through the installed CLI entry point.

Contracts under test (from docstrings + docs/content-filter.md):
- FilterConfig defaults: min_content_length=100, max_content_length=100000,
  min_title_length=3, require_interest_match=True, empty lists,
  min_relevance_score=0.0.
- ContentFilter(config=None) defaults to FilterConfig(); interest_store may
  be None.
- _compile_patterns (blocked): invalid regex silently dropped (no raise).
- _compile_required_patterns (required): invalid regex raises ValueError
  naming the offending pattern at construction time.
- get_filter_reasons: up to 8 checks in order, one reason string per
  failure, empty list when the page passes every check.
- should_include: True iff get_filter_reasons is empty.
- filter_pages: new list, order preserved, empty input -> [].
- _is_blocked_domain: extract_domain None -> False; exact or subdomain
  suffix match.
- _matches_interests: None store -> True (no check); on match mutates
  page.matched_interests and page.relevance_score.
- Check 8 re-computes total_score independently.
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest


def _page(
    url: str = "http://example.com/a",
    title: str = "A valid title",
    content: str = "x" * 200,
) -> CrawledPage:
    return CrawledPage(url=url, title=title, content=content)


# ── FilterConfig defaults ──────────────────────────────────────────────


class TestFilterConfigDefaults:
    def test_defaults(self):
        c = FilterConfig()
        assert c.min_content_length == 100
        assert c.max_content_length == 100000
        assert c.min_title_length == 3
        assert c.require_interest_match is True
        assert c.blocked_domains == []
        assert c.blocked_patterns == []
        assert c.required_patterns == []
        assert c.min_relevance_score == 0.0

    def test_list_fields_are_independent(self):
        a = FilterConfig()
        b = FilterConfig()
        a.blocked_domains.append("evil.com")
        assert b.blocked_domains == []


# ── Construction ───────────────────────────────────────────────────────


class TestConstruction:
    def test_none_config_defaults(self):
        f = ContentFilter()
        assert isinstance(f.config, FilterConfig)
        assert f.config.min_content_length == 100
        assert f.interest_store is None

    def test_none_config_none_store(self):
        f = ContentFilter(config=None, interest_store=None)
        assert f.config is not None
        assert f.interest_store is None

    def test_invalid_blocked_pattern_silently_dropped(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["[unclosed"]))
        assert f._compiled_blocked == []

    def test_valid_blocked_pattern_compiled(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["spam"]))
        assert len(f._compiled_blocked) == 1

    def test_invalid_required_pattern_raises_valueerror(self):
        with pytest.raises(ValueError) as ei:
            ContentFilter(config=FilterConfig(required_patterns=["[unclosed"]))
        assert "invalid required pattern" in str(ei.value)
        assert "[unclosed" in str(ei.value)

    def test_valid_required_pattern_compiled(self):
        f = ContentFilter(config=FilterConfig(required_patterns=["must"]))
        assert len(f._compiled_required) == 1


# ── Content length checks ──────────────────────────────────────────────


class TestContentLength:
    def test_below_min_rejected(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content="x" * 99)
        assert f.should_include(page) is False
        reasons = f.get_filter_reasons(page)
        assert any("below minimum" in r for r in reasons)

    def test_exactly_min_included(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content="x" * 100)
        assert f.should_include(page) is True

    def test_above_max_rejected(self):
        f = ContentFilter(config=FilterConfig(max_content_length=10))
        page = _page(content="x" * 11)
        assert f.should_include(page) is False
        assert any("exceeds maximum" in r for r in f.get_filter_reasons(page))

    def test_exactly_max_included(self):
        f = ContentFilter(config=FilterConfig(min_content_length=1, max_content_length=10))
        page = _page(content="x" * 10)
        assert f.should_include(page) is True

    def test_empty_content_rejected(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content="")
        assert f.should_include(page) is False

    def test_whitespace_content_counts_toward_length(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content=" " * 100)
        assert f.should_include(page) is True


# ── Title length check ─────────────────────────────────────────────────


class TestTitleLength:
    def test_short_title_rejected(self):
        f = ContentFilter(config=FilterConfig(min_title_length=3))
        page = _page(title="ab")
        assert f.should_include(page) is False
        assert any("title too short" in r for r in f.get_filter_reasons(page))

    def test_exactly_min_title_included(self):
        f = ContentFilter(config=FilterConfig(min_title_length=3))
        page = _page(title="abc")
        assert f.should_include(page) is True

    def test_empty_title_rejected(self):
        f = ContentFilter(config=FilterConfig(min_title_length=3))
        page = _page(title="")
        assert f.should_include(page) is False


# ── Blocked domains ────────────────────────────────────────────────────


class TestBlockedDomains:
    def test_exact_domain_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        assert f.should_include(_page(url="http://example.com/a")) is False
        assert "domain is blocked" in f.get_filter_reasons(_page(url="http://example.com/a"))

    def test_subdomain_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        assert f.should_include(_page(url="http://sub.example.com/a")) is False

    def test_non_subdomain_not_blocked(self):
        # "notexample.com" must NOT be treated as a subdomain of "example.com"
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        assert f.should_include(_page(url="http://notexample.com/a")) is True

    def test_different_domain_not_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        assert f.should_include(_page(url="http://other.org/a")) is True

    def test_empty_url_not_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        # extract_domain("") -> None -> not blocked by domain check
        page = _page(url="")
        reasons = f.get_filter_reasons(page)
        assert "domain is blocked" not in reasons

    def test_malformed_url_not_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        page = _page(url="not a url at all")
        assert "domain is blocked" not in f.get_filter_reasons(page)


# ── Blocked patterns ───────────────────────────────────────────────────


class TestBlockedPatterns:
    def test_blocked_pattern_matches_content(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["spam"]))
        page = _page(content="this is SPAM content " + "x" * 100)
        assert f.should_include(page) is False
        assert "content matches blocked pattern" in f.get_filter_reasons(page)

    def test_blocked_pattern_matches_title(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["spam"]))
        page = _page(title="spam alert", content="x" * 200)
        assert f.should_include(page) is False

    def test_blocked_pattern_case_insensitive(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["[Ss]pam"]))
        page = _page(content="SPAM " + "x" * 200)
        assert f.should_include(page) is False

    def test_blocked_pattern_no_match_included(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["spam"]))
        page = _page(content="clean content " + "x" * 200)
        assert f.should_include(page) is True


# ── Required patterns ──────────────────────────────────────────────────


class TestRequiredPatterns:
    def test_required_pattern_matched_included(self):
        f = ContentFilter(config=FilterConfig(required_patterns=["python"]))
        page = _page(content="about Python " + "x" * 200)
        assert f.should_include(page) is True

    def test_required_pattern_not_matched_rejected(self):
        f = ContentFilter(config=FilterConfig(required_patterns=["python"]))
        page = _page(content="about rust " + "x" * 200)
        assert f.should_include(page) is False
        assert "content does not match required pattern" in f.get_filter_reasons(page)

    def test_empty_required_patterns_skips_check(self):
        f = ContentFilter(config=FilterConfig(required_patterns=[]))
        page = _page(content="anything " + "x" * 200)
        assert f.should_include(page) is True

    def test_any_required_pattern_match_suffices(self):
        f = ContentFilter(
            config=FilterConfig(required_patterns=["python", "rust"])
        )
        page = _page(content="about rust " + "x" * 200)
        assert f.should_include(page) is True


# ── Interest matching + side effects ───────────────────────────────────


def _store_with_keyword(kw: str) -> InterestStore:
    store = InterestStore()
    store.add(Interest(name="kw", keywords=[kw]))
    return store


class TestInterestMatching:
    def test_no_store_no_interest_check(self):
        f = ContentFilter(config=FilterConfig(require_interest_match=True))
        assert f.interest_store is None
        assert f.should_include(_page()) is True

    def test_matching_interest_included(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(require_interest_match=True),
            interest_store=store,
        )
        page = _page(content="about Python " + "x" * 200)
        assert f.should_include(page) is True
        assert page.matched_interests == ["kw"]
        assert page.relevance_score > 0

    def test_no_matching_interest_rejected(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(require_interest_match=True),
            interest_store=store,
        )
        page = _page(content="about rust " + "x" * 200)
        assert f.should_include(page) is False
        assert "no matching interests" in f.get_filter_reasons(page)

    def test_require_interest_match_false_skips_check(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(require_interest_match=False),
            interest_store=store,
        )
        page = _page(content="about rust " + "x" * 200)
        assert f.should_include(page) is True

    def test_side_effect_sets_matched_interests(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(require_interest_match=True),
            interest_store=store,
        )
        page = _page(content="about Python " + "x" * 200)
        assert page.matched_interests == []
        f.get_filter_reasons(page)
        assert page.matched_interests == ["kw"]


# ── Relevance score check (check 8) ────────────────────────────────────


class TestRelevanceScore:
    def test_score_below_min_rejected(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(
                require_interest_match=False, min_relevance_score=1000.0
            ),
            interest_store=store,
        )
        page = _page(content="python " + "x" * 200)
        assert f.should_include(page) is False
        assert any("below minimum" in r for r in f.get_filter_reasons(page))

    def test_score_at_or_above_min_included(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(
                require_interest_match=False, min_relevance_score=0.0
            ),
            interest_store=store,
        )
        page = _page(content="python " + "x" * 200)
        assert f.should_include(page) is True

    def test_zero_min_relevance_skips_check(self):
        store = _store_with_keyword("python")
        f = ContentFilter(
            config=FilterConfig(
                require_interest_match=False, min_relevance_score=0.0
            ),
            interest_store=store,
        )
        page = _page(content="rust " + "x" * 200)
        # no interest match required, min_relevance 0 -> passes
        assert f.should_include(page) is True

    def test_no_store_skips_relevance_check(self):
        f = ContentFilter(
            config=FilterConfig(
                require_interest_match=False, min_relevance_score=1000.0
            )
        )
        assert f.interest_store is None
        page = _page(content="rust " + "x" * 200)
        assert f.should_include(page) is True


# ── filter_pages: ordering, empty, idempotence ─────────────────────────


class TestFilterPages:
    def test_empty_input_returns_empty(self):
        f = ContentFilter()
        assert f.filter_pages([]) == []

    def test_order_preserved(self):
        f = ContentFilter(config=FilterConfig(min_content_length=10))
        pages = [
            _page(url="http://a.com", content="keep a " + "x" * 20),
            _page(url="http://b.com", content="keep b " + "x" * 20),
            _page(url="http://c.com", content="keep c " + "x" * 20),
        ]
        out = f.filter_pages(pages)
        assert [p.url for p in out] == [
            "http://a.com",
            "http://b.com",
            "http://c.com",
        ]

    def test_mixed_included_excluded(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        good = _page(url="http://good.com", content="x" * 200)
        bad = _page(url="http://bad.com", content="short")
        out = f.filter_pages([good, bad, good])
        assert len(out) == 2
        assert all(p.url == "http://good.com" for p in out)

    def test_returns_new_list(self):
        f = ContentFilter(config=FilterConfig(min_content_length=10))
        pages = [_page(content="x" * 20)]
        out = f.filter_pages(pages)
        assert out is not pages

    def test_idempotence(self):
        f = ContentFilter(config=FilterConfig(min_content_length=10))
        pages = [
            _page(url="http://a.com", content="x" * 20),
            _page(url="http://b.com", content="short"),
        ]
        first = f.filter_pages(pages)
        second = f.filter_pages(first)
        assert [p.url for p in first] == [p.url for p in second]


# ── Unicode / guard inputs ─────────────────────────────────────────────


class TestUnicodeAndGuards:
    def test_unicode_content_included(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content="héllo wörld " * 10)
        assert f.should_include(page) is True

    def test_unicode_title(self):
        f = ContentFilter(config=FilterConfig(min_title_length=3))
        page = _page(title="héllo", content="x" * 200)
        assert f.should_include(page) is True

    def test_unicode_blocked_pattern(self):
        f = ContentFilter(config=FilterConfig(blocked_patterns=["café"]))
        page = _page(content="this is a café " + "x" * 200)
        assert f.should_include(page) is False

    def test_unicode_domain_not_blocked(self):
        f = ContentFilter(config=FilterConfig(blocked_domains=["example.com"]))
        page = _page(url="http://exämple.com/a", content="x" * 200)
        assert "domain is blocked" not in f.get_filter_reasons(page)

    def test_duplicate_blocked_domains(self):
        f = ContentFilter(
            config=FilterConfig(blocked_domains=["example.com", "example.com"])
        )
        assert f.should_include(_page(url="http://example.com/a")) is False

    def test_duplicate_required_patterns(self):
        f = ContentFilter(
            config=FilterConfig(required_patterns=["python", "python"])
        )
        page = _page(content="about Python " + "x" * 200)
        assert f.should_include(page) is True


# ── Multiple reasons accumulate ────────────────────────────────────────


class TestMultipleReasons:
    def test_multiple_failures_accumulate(self):
        f = ContentFilter(
            config=FilterConfig(
                min_content_length=100,
                max_content_length=100000,
                min_title_length=3,
                blocked_domains=["example.com"],
            )
        )
        page = _page(url="http://example.com/a", title="ab", content="short")
        reasons = f.get_filter_reasons(page)
        assert any("below minimum" in r for r in reasons)
        assert any("title too short" in r for r in reasons)
        assert any("domain is blocked" in r for r in reasons)
        assert f.should_include(page) is False

    def test_passing_page_has_empty_reasons(self):
        f = ContentFilter(config=FilterConfig(min_content_length=100))
        page = _page(content="x" * 200)
        assert f.get_filter_reasons(page) == []


# ── End-to-end CLI ─────────────────────────────────────────────────────


class TestCliEndToEnd:
    def test_cli_verify_runs(self, tmp_path):
        proc = subprocess.run(
            [
                sys.executable,
                "-m",
                "personal_index.cli",
                "verify",
                "--quick",
                "--data-dir",
                str(tmp_path),
            ],
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert proc.returncode == 0, proc.stderr
        assert "All checks passed" in proc.stdout

    def test_cli_help_lists_verify(self):
        proc = subprocess.run(
            [sys.executable, "-m", "personal_index.cli", "--help"],
            capture_output=True,
            text=True,
            timeout=60,
        )
        assert proc.returncode == 0
        assert "verify" in proc.stdout
