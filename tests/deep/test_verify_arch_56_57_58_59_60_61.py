"""VALIDATOR cycle 213 — VERIFY ARCH-56/57/58/59/60/61.

One adversarial input per contract, on top of the existing pinning tests in
tests/test_*.py. Each test attacks a documented bound/guard the contract
implies and confirms the implemented option holds.

- ARCH-56 link-analyzer: get_aggregate_stats unions the FULL per-page
  all_external_domains set (not the top-20-truncated domain_distribution),
  so a page with >20 distinct external domains is not silently undercounted.
- ARCH-57 keyword-extractor: extract_top_n's n is authoritative (passes
  limit=n to extract), so n > max_keywords returns n items, not max_keywords.
- ARCH-58 pagination: Paginator.__init__ clamps per_page, so total_pages
  never raises ZeroDivisionError on per_page=0/negative.
- ARCH-59 throttle: rate_per_second returns 0.0 for window_seconds <= 0
  (finite fallback), so wait_if_needed never raises on a zero-window rule.
- ARCH-60 text-utils: read_time_minutes returns 0 for wpm <= 0 (no
  ZeroDivisionError, no bogus 1); wpm > 0 -> ceil(count/wpm).
- ARCH-61 url-utils: get_tld returns "" for dotless hosts (no TLD), the
  last dot-label for single-label TLDs, and the second-level label for
  two-label TLDs (documented limitation).
"""

from __future__ import annotations


import pytest

from personal_index.keyword_extractor import KeywordExtractor
from personal_index.link_analyzer import LinkAnalyzer
from personal_index.pagination import Paginator
from personal_index.text_utils import read_time_minutes
from personal_index.throttle import ThrottleManager, ThrottleRule
from personal_index.url_utils import get_tld


# ---------------------------------------------------------------------------
# ARCH-56: link_analyzer.get_aggregate_stats — full-set union, not top-20
# ---------------------------------------------------------------------------

class TestArch56AggregateUniqueExternalDomains:
    """ARCH-56: unique_external_domains is the TRUE cross-page distinct count."""

    def test_aggregate_unique_domains_exceeds_top20_cap(self):
        """One page has 25 distinct external domains, another has 3 (2 overlap).
        True union = 26. The old top-20-truncated union would give 21."""
        analyzer = LinkAnalyzer(base_domain="")
        # Page 1: 25 distinct external domains
        page1_links = [{"url": f"https://d{i}.com/page", "text": f"link{i}"} for i in range(25)]
        # Page 2: 3 domains, 2 overlap with page 1 (d0.com, d1.com), 1 new (e.com)
        page2_links = [
            {"url": "https://d0.com/x", "text": "a"},
            {"url": "https://d1.com/y", "text": "b"},
            {"url": "https://e.com/z", "text": "c"},
        ]
        results = analyzer.analyze_batch([
            {"url": "https://page1.com", "links": page1_links},
            {"url": "https://page2.com", "links": page2_links},
        ])
        stats = analyzer.get_aggregate_stats(results)
        # True union: 25 + 1 new = 26
        assert stats["unique_external_domains"] == 26
        assert stats["pages_analyzed"] == 2

    def test_aggregate_empty_results(self):
        """get_aggregate_stats([]) returns 0 unique domains, 0 pages, no raise."""
        analyzer = LinkAnalyzer()
        stats = analyzer.get_aggregate_stats([])
        assert stats["unique_external_domains"] == 0
        assert stats["pages_analyzed"] == 0

    def test_aggregate_all_internal_links(self):
        """A page with only internal links contributes no external domains."""
        analyzer = LinkAnalyzer(base_domain="example.com")
        links = [
            {"url": "https://example.com/a", "text": "a"},
            {"url": "https://example.com/b", "text": "b"},
        ]
        results = analyzer.analyze_batch([{"url": "https://example.com", "links": links}])
        stats = analyzer.get_aggregate_stats(results)
        assert stats["unique_external_domains"] == 0
        # all_external_domains should be empty set
        assert results[0].all_external_domains == set()


# ---------------------------------------------------------------------------
# ARCH-57: keyword_extractor.extract_top_n — n is authoritative
# ---------------------------------------------------------------------------

class TestArch57ExtractTopNAuthoritative:
    """ARCH-57: extract_top_n(text, n) returns min(n, available) keywords."""

    def test_extract_top_n_respects_n_over_max_keywords(self):
        """n=50 > max_keywords=20: returns all 40 keywords, not 20."""
        extractor = KeywordExtractor(max_keywords=20)
        # 40 distinct keywords, each >= 3 chars, not stopwords
        text = " ".join(f"kw{i:03d}" for i in range(40))
        result = extractor.extract_top_n(text, n=50)
        assert len(result) == 40  # all 40, not capped at 20

    def test_extract_top_n_small_n(self):
        """n=5: returns exactly 5 keywords."""
        extractor = KeywordExtractor(max_keywords=20)
        text = " ".join(f"kw{i:03d}" for i in range(40))
        result = extractor.extract_top_n(text, n=5)
        assert len(result) == 5

    def test_extract_still_capped_by_max_keywords(self):
        """extract(text) without limit still caps at max_keywords=20."""
        extractor = KeywordExtractor(max_keywords=20)
        text = " ".join(f"kw{i:03d}" for i in range(40))
        result = extractor.extract(text)
        assert len(result) == 20

    def test_extract_top_n_zero_negative_guard(self):
        """n=0 and n=-3 return [] without raising."""
        extractor = KeywordExtractor(max_keywords=20)
        text = " ".join(f"kw{i:03d}" for i in range(10))
        assert extractor.extract_top_n(text, n=0) == []
        assert extractor.extract_top_n(text, n=-3) == []

    def test_extract_top_n_empty_text(self):
        """extract_top_n('', n=10) returns [] (empty text guard)."""
        extractor = KeywordExtractor(max_keywords=20)
        assert extractor.extract_top_n("", n=10) == []


# ---------------------------------------------------------------------------
# ARCH-58: pagination.Paginator — per_page clamped in __init__
# ---------------------------------------------------------------------------

class TestArch58PaginatorPerPageClamped:
    """ARCH-58: total_pages never raises on per_page=0/negative."""

    def test_total_pages_zero_per_page_no_raise(self):
        """Paginator([1,2,3], per_page=0).total_pages == 3 (clamped to 1)."""
        p = Paginator([1, 2, 3], per_page=0)
        assert p.total_pages == 3

    def test_total_pages_zero_per_page_empty(self):
        """Paginator([], per_page=0).total_pages == 1 (empty guard)."""
        p = Paginator([], per_page=0)
        assert p.total_pages == 1

    def test_total_pages_negative_per_page(self):
        """Paginator([1,2,3], per_page=-5).total_pages == 3 (clamped to 1)."""
        p = Paginator([1, 2, 3], per_page=-5)
        assert p.total_pages == 3

    def test_total_pages_matches_iterate_pages_zero_per_page(self):
        """For per_page=0, total_pages == len(iterate_pages())."""
        items = list(range(7))
        p = Paginator(items, per_page=0)
        assert p.total_pages == len(p.iterate_pages())
        assert p.total_pages == 7

    def test_get_page_zero_per_page_clamps(self):
        """get_page(1) with per_page=0 returns per_page=1, items=[1]."""
        p = Paginator([1, 2, 3], per_page=0)
        result = p.get_page(1)
        assert result.per_page == 1
        assert result.items == [1]

    def test_total_pages_normal_unchanged(self):
        """Normal path: Paginator([1,2,3,4,5], per_page=2).total_pages == 3."""
        p = Paginator([1, 2, 3, 4, 5], per_page=2)
        assert p.total_pages == 3


# ---------------------------------------------------------------------------
# ARCH-59: throttle.ThrottleRule.rate_per_second — finite fallback
# ---------------------------------------------------------------------------

class TestArch59ThrottleRatePerSecondGuard:
    """ARCH-59: rate_per_second returns 0.0 for window_seconds <= 0."""

    def test_rate_per_second_zero_window_no_raise(self):
        """ThrottleRule(max_requests=10, window_seconds=0).rate_per_second == 0.0."""
        rule = ThrottleRule(max_requests=10, window_seconds=0)
        assert rule.rate_per_second == 0.0

    def test_rate_per_second_negative_window_no_raise(self):
        """ThrottleRule(max_requests=10, window_seconds=-5).rate_per_second == 0.0."""
        rule = ThrottleRule(max_requests=10, window_seconds=-5)
        assert rule.rate_per_second == 0.0

    def test_rate_per_second_normal_unchanged(self):
        """Normal path: ThrottleRule(max_requests=10, window_seconds=60) == 10/60."""
        rule = ThrottleRule(max_requests=10, window_seconds=60)
        assert rule.rate_per_second == pytest.approx(10 / 60)

    def test_wait_if_needed_two_calls_zero_window_no_raise(self):
        """Two consecutive wait_if_needed calls on one domain with a
        zero-window rule do not raise (2nd call falls through to min_delay)."""
        rule = ThrottleRule(max_requests=10, window_seconds=0, min_delay=0.01)
        mgr = ThrottleManager(default_rule=rule)
        # First call: last_request is None, should_throttle is False -> 0.0
        w1 = mgr.wait_if_needed("https://example.com/a")
        assert w1 == 0.0
        # Second call: last_request is set, rate_per_second=0.0 -> min_delay
        # should_throttle: 1 request < max_requests=10 -> False
        # No raise, returns a finite value
        w2 = mgr.wait_if_needed("https://example.com/b")
        assert w2 >= 0.0  # finite, no exception


# ---------------------------------------------------------------------------
# ARCH-60: text_utils.read_time_minutes — wpm guard
# ---------------------------------------------------------------------------

class TestArch60ReadTimeMinutesWpmGuard:
    """ARCH-60: wpm <= 0 -> 0; wpm > 0 -> ceil(count/wpm)."""

    def test_zero_wpm_returns_zero(self):
        """read_time_minutes(text, wpm=0) == 0 (no ZeroDivisionError)."""
        assert read_time_minutes("word " * 300, wpm=0) == 0

    def test_negative_wpm_returns_zero(self):
        """read_time_minutes(text, wpm=-5) == 0 (no bogus 1)."""
        assert read_time_minutes("word " * 300, wpm=-5) == 0

    def test_positive_wpm_ceil(self):
        """read_time_minutes('word '*300, wpm=200) == ceil(300/200) == 2."""
        assert read_time_minutes("word " * 300, wpm=200) == 2

    def test_empty_text_returns_zero(self):
        """read_time_minutes('', wpm=200) == 0 (ceil(0/200) == 0)."""
        assert read_time_minutes("", wpm=200) == 0

    def test_single_word_returns_one(self):
        """read_time_minutes('hello', wpm=200) == ceil(1/200) == 1."""
        assert read_time_minutes("hello", wpm=200) == 1


# ---------------------------------------------------------------------------
# ARCH-61: url_utils.get_tld — dotless host returns ""
# ---------------------------------------------------------------------------

class TestArch61GetTldDotlessHost:
    """ARCH-61: dotless hosts return "" (no TLD); single-label TLDs work."""

    def test_single_label_regression(self):
        """get_tld('https://example.com') == 'com' (single-label still works)."""
        assert get_tld("https://example.com") == "com"

    def test_two_label_returns_last_label(self):
        """get_tld('https://www.example.co.uk/x') == 'uk' (documented limitation)."""
        assert get_tld("https://www.example.co.uk/x") == "uk"

    def test_dotless_host_returns_empty(self):
        """get_tld('https://intranet') == '' (dotless host has no TLD)."""
        assert get_tld("https://intranet") == ""

    def test_dotless_host_with_port_returns_empty(self):
        """get_tld('https://localhost:8080/x') == '' (dotless host with port)."""
        assert get_tld("https://localhost:8080/x") == ""

    def test_empty_and_no_netloc(self):
        """get_tld('') == '' and get_tld('not-a-url') == '' (no netloc)."""
        assert get_tld("") == ""
        assert get_tld("not-a-url") == ""
