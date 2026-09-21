"""Cycle 337 VALIDATOR probe: naive-vs-aware datetime seam in
personal_index.dashboard.aggregator.DashboardAggregator.

CLASS SWEEP LEAD (carry-over from QA-62/63/64/65): the naive-vs-aware
datetime seam is a MULTI-SITE class. A site is a ``datetime.fromisoformat``
result compared against an aware bound (or against another datetime of the
opposite tz-awareness) with an ``except`` that omits ``TypeError`` (or a bare
comparison with no ``except`` at all).

Already filed:
  * content_archive.archive_old            -> QA-62 (VERIFIED, fixed)
  * sitemap.get_recent_entries +
    progress.elapsed_seconds               -> QA-63 (OPEN)
  * auth/api_keys.validate_key             -> QA-64 (OPEN)
  * search_facets.faceted_search range     -> QA-65 (OPEN)

NEW site found this cycle (QA-66):
  * dashboard.aggregator.DashboardAggregator._compute_pages_per_day

``_compute_pages_per_day`` (aggregator.py:79) builds a ``dates`` list by
parsing each page's ``crawled_at`` (a string) with ``datetime.fromisoformat``
or keeping an existing ``datetime``. The per-item parse is wrapped in
``except (ValueError, TypeError)`` so a single bad item is skipped. BUT the
span computation at aggregator.py:94,

    span = (max(dates) - min(dates)).total_seconds()

lives OUTSIDE that try/except. When ``dates`` mixes a naive and an aware
datetime (both reachable: ``CrawledPage.from_dict`` parses a naive ISO string
to a naive datetime and an aware ISO string to an aware datetime), ``max()``
raises an uncaught ``TypeError: can't compare offset-naive and offset-aware
datetimes``. The public entry point is ``aggregate()`` ->
``_apply_page_stats`` -> ``_compute_pages_per_day``.

The reference fix (content_scoring._score_recency, content_scoring.py:267-268)
normalizes a naive datetime to UTC-aware via ``replace(tzinfo=timezone.utc)``
before comparing. The same normalization is missing here.

These xfail-strict pins DOCUMENT the defect (they fail on current main). They
must be flipped to hard passes ONLY once the implementer's fix is confirmed ON
main (see QA-66).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.dashboard.aggregator import AggregatedStats, DashboardAggregator
from personal_index.models import CrawledPage


def _page(url: str, crawled_at) -> CrawledPage:
    return CrawledPage.from_dict({"url": url, "crawled_at": crawled_at})


class _FakeIndex:
    """Minimal index_instance exposing get_all_pages()."""

    def __init__(self, pages):
        self._pages = pages

    def get_all_pages(self):
        return list(self._pages)


def _aggregate(pages):
    return DashboardAggregator().aggregate(
        index_instance=_FakeIndex(pages), force_refresh=True
    )


class TestNaiveAwarePagesPerDaySeam:
    """The seam: a mixed naive/aware crawled_at list reaches max() outside
    the per-item try/except and raises an uncaught TypeError."""

    def test_mixed_naive_aware_raises_type_error(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00"),          # naive
            _page("http://b.com", "2024-01-02T00:00:00+00:00"),    # aware
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    def test_mixed_aware_naive_raises_type_error(self):
        pages = [
            _page("http://a.com", "2024-01-02T00:00:00+00:00"),    # aware
            _page("http://b.com", "2024-01-01T00:00:00"),          # naive
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    def test_mixed_three_pages_raises_type_error(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00"),
            _page("http://b.com", "2024-01-02T00:00:00"),
            _page("http://c.com", "2024-01-03T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0


class TestBothSameAwarenessNoSeam:
    """Armor: when every crawled_at is the SAME tz-awareness (all aware or
    all naive) there is NO seam and pages_per_day is computed. These must
    stay green on current main."""

    def test_all_aware_computes_pages_per_day(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00+00:00"),
            _page("http://b.com", "2024-01-02T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        # 2 pages over a 1-day span -> 2.0 pages/day.
        assert stats.pages_per_day == pytest.approx(2.0)

    def test_all_naive_computes_pages_per_day(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00"),
            _page("http://b.com", "2024-01-02T00:00:00"),
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day == pytest.approx(2.0)

    def test_single_page_returns_zero(self):
        pages = [_page("http://a.com", "2024-01-01T00:00:00+00:00")]
        stats = _aggregate(pages)
        assert stats.pages_per_day == 0.0

    def test_empty_pages_returns_zero(self):
        stats = _aggregate([])
        assert stats.pages_per_day == 0.0


class TestPagesPerDayGuards:
    """Armor: guard inputs on the _compute_pages_per_day path that do NOT
    touch the naive-vs-aware seam.

    Note the contract: ``CrawledPage.from_dict`` normalizes a bad/None/empty
    ``crawled_at`` to ``datetime.now(timezone.utc)`` (an AWARE datetime), so
    such pages are NOT skipped by the per-item try/except - they contribute an
    aware "now" date. The per-item try/except only fires for a page whose
    ``crawled_at`` is a raw non-ISO string that bypassed ``from_dict`` (e.g. a
    directly-constructed ``CrawledPage``)."""

    def test_bad_crawled_at_normalized_to_now_aware(self):
        # from_dict turns "not-a-date" into now(utc) (aware) -> all three
        # dates are aware -> no seam, a finite pages_per_day is computed.
        pages = [
            _page("http://a.com", "not-a-date"),
            _page("http://b.com", "2024-01-01T00:00:00+00:00"),
            _page("http://c.com", "2024-01-02T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    def test_none_crawled_at_normalized_to_now_aware(self):
        # from_dict turns None into now(utc) (aware) -> all aware, no seam.
        pages = [
            _page("http://a.com", None),
            _page("http://b.com", "2024-01-01T00:00:00+00:00"),
            _page("http://c.com", "2024-01-02T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    def test_raw_string_crawled_at_skipped_by_item_guard(self):
        # A directly-constructed page with a raw non-ISO string crawled_at
        # bypasses from_dict's normalization; the per-item try/except skips it
        # (ValueError), so the two valid aware dates span 1 day. pages_per_day
        # divides len(pages)=3 by the 1-day span -> 3.0 (the skipped page still
        # counts in the numerator, only its date is dropped from the span).
        raw = CrawledPage(url="http://a.com", crawled_at="garbage")  # type: ignore[arg-type]
        pages = [
            raw,
            _page("http://b.com", "2024-01-01T00:00:00+00:00"),
            _page("http://c.com", "2024-01-02T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day == pytest.approx(3.0)


class TestCliEndToEnd:
    def test_init_then_stats_empty_index(self, tmp_path):
        # End-to-end: init a data dir, then run `stats` on the empty index ->
        # exit code 0 and the documented statistics header.
        env_dir = str(tmp_path / "dd")
        r1 = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r1.returncode == 0, r1.stderr
        r2 = subprocess.run(
            [sys.executable, "-m", "personal_index", "stats", "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r2.returncode == 0, r2.stderr
        assert "Personal Index Statistics" in r2.stdout


class TestRecentActivityNoSeam:
    """Cycle 343 RE-PROBE: _compute_recent_activity (aggregator.py:195) is the
    second fromisoformat site in the module. It only does ``dt.strftime`` string
    grouping (no datetime comparison/subtraction), so a mixed naive/aware
    crawled_at list must NOT raise - it groups by day-key. This is armor for the
    site the QA-66 fix did NOT touch (the fix only normalized _compute_pages_per_day)."""

    def test_mixed_naive_aware_groups_by_day(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00"),          # naive
            _page("http://b.com", "2024-01-02T00:00:00+00:00"),    # aware
            _page("http://c.com", "2024-01-01T05:00:00"),          # naive, same day as a
        ]
        stats = _aggregate(pages)
        # Grouped by day: 2024-01-01 -> 2, 2024-01-02 -> 1; sorted desc.
        got = [(p.timestamp, p.value) for p in stats.recent_activity]
        assert got == [("2024-01-02", 1), ("2024-01-01", 2)]

    def test_recent_activity_empty_pages(self):
        stats = _aggregate([])
        assert stats.recent_activity == []

    def test_recent_activity_bad_crawled_at_skipped(self):
        # from_dict normalizes "not-a-date" to now(utc) (aware) -> contributes a
        # day-key; the two explicit aware dates contribute their own day-keys.
        pages = [
            _page("http://a.com", "not-a-date"),
            _page("http://b.com", "2024-01-01T00:00:00+00:00"),
            _page("http://c.com", "2024-01-01T00:00:00+00:00"),
        ]
        stats = _aggregate(pages)
        # 2024-01-01 -> 2; the "now" page -> its own day-key (>= 1).
        by_day = {p.timestamp: p.value for p in stats.recent_activity}
        assert by_day.get("2024-01-01") == 2
        assert sum(by_day.values()) == 3

    def test_recent_activity_limit_caps_points(self):
        # 30 distinct days -> limit (default 24) caps the returned points.
        pages = [
            _page(f"http://d{i}.com", f"2024-01-{(i % 28) + 1:02d}T00:00:00+00:00")
            for i in range(30)
        ]
        stats = _aggregate(pages)
        assert len(stats.recent_activity) <= 24


class TestCacheIdempotence:
    """Cycle 343 RE-PROBE: aggregate() caches for _cache_ttl (30s). A second
    call within the TTL (force_refresh=False) returns the SAME cached object;
    clear_cache() forces a fresh aggregation."""

    def test_second_call_returns_cached_object(self):
        pages = [_page("http://a.com", "2024-01-01T00:00:00+00:00")]
        agg = DashboardAggregator()
        s1 = agg.aggregate(index_instance=_FakeIndex(pages), force_refresh=True)
        s2 = agg.aggregate(index_instance=_FakeIndex(pages), force_refresh=False)
        assert s2 is s1

    def test_clear_cache_forces_recompute(self):
        pages = [_page("http://a.com", "2024-01-01T00:00:00+00:00")]
        agg = DashboardAggregator()
        s1 = agg.aggregate(index_instance=_FakeIndex(pages), force_refresh=True)
        agg.clear_cache()
        s2 = agg.aggregate(index_instance=_FakeIndex(pages), force_refresh=False)
        assert s2 is not s1


class TestSuccessRateAndBreakdowns:
    """Cycle 343 RE-PROBE: _compute_success_rate, _compute_status_breakdown,
    _compute_content_types, _compute_top_domains, _compute_total_keywords,
    _compute_avg_relevance - guard inputs (empty, mixed codes, dedup, limit)."""

    def test_success_rate_mixed_codes(self):
        agg = DashboardAggregator()
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00+00:00"),
            CrawledPage.from_dict({"url": "http://b.com", "status_code": 404}),
            CrawledPage.from_dict({"url": "http://c.com", "status_code": 500}),
        ]
        assert agg._compute_success_rate(pages) == pytest.approx(100.0 / 3)

    def test_success_rate_empty_is_100(self):
        assert DashboardAggregator()._compute_success_rate([]) == 100.0

    def test_status_breakdown_categories(self):
        agg = DashboardAggregator()
        pages = [
            CrawledPage.from_dict({"url": "a", "status_code": 200}),
            CrawledPage.from_dict({"url": "b", "status_code": 404}),
            CrawledPage.from_dict({"url": "c", "status_code": 500}),
        ]
        assert agg._compute_status_breakdown(pages) == {"2xx": 1, "4xx": 1, "5xx": 1}

    def test_status_breakdown_zero_code_is_unknown(self):
        agg = DashboardAggregator()
        pages = [CrawledPage.from_dict({"url": "a", "status_code": 0})]
        assert agg._compute_status_breakdown(pages) == {"unknown": 1}

    def test_content_type_breakdown_defaults_unknown(self):
        # CrawledPage has no content_type field -> getattr default -> "unknown".
        agg = DashboardAggregator()
        pages = [_page("http://a.com", "2024-01-01T00:00:00+00:00")]
        assert agg._compute_content_types(pages) == {"unknown": 1}

    def test_top_domains_counts_and_limit(self):
        agg = DashboardAggregator()

        class _P:
            def __init__(self, d):
                self.domain = d

        pages = [_P("x.com"), _P("x.com"), _P("y.com")]
        top = agg._compute_top_domains(pages)
        assert top == [
            {"domain": "x.com", "count": 2, "percentage": 66.7},
            {"domain": "y.com", "count": 1, "percentage": 33.3},
        ]
        # limit caps the returned list.
        assert len(agg._compute_top_domains([_P("a"), _P("b"), _P("c"), _P("d")], limit=2)) == 2

    def test_top_domains_empty(self):
        assert DashboardAggregator()._compute_top_domains([]) == []

    def test_total_keywords_dedups_across_pages(self):
        agg = DashboardAggregator()

        class _K:
            def __init__(self, k):
                self.keywords = k

        assert agg._compute_total_keywords([_K(["a", "b"]), _K(["b", "c"])]) == 3

    def test_avg_relevance_empty_is_zero(self):
        assert DashboardAggregator()._compute_avg_relevance([]) == 0.0


class TestToDictRounding:
    """Cycle 343 RE-PROBE: AggregatedStats.to_dict rounds the three float
    fields (avg_relevance_score -> 2dp, pages_per_day -> 1dp,
    crawl_success_rate -> 1dp) and serializes recent_activity points."""

    def test_float_fields_rounded(self):
        s = AggregatedStats(
            total_pages=5,
            avg_relevance_score=1.234,
            pages_per_day=2.34,
            crawl_success_rate=99.94,
        )
        d = s.to_dict()
        assert d["avg_relevance_score"] == 1.23
        assert d["pages_per_day"] == 2.3
        assert d["crawl_success_rate"] == 99.9

    def test_recent_activity_serialized_to_dicts(self):
        from personal_index.dashboard.aggregator import TimeSeriesPoint

        s = AggregatedStats(recent_activity=[TimeSeriesPoint("2024-01-01", 2, "2024-01-01")])
        d = s.to_dict()
        assert d["recent_activity"] == [{"timestamp": "2024-01-01", "value": 2, "label": "2024-01-01"}]




if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
