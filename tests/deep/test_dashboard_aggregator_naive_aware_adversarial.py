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

from personal_index.dashboard.aggregator import DashboardAggregator
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

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-66: mixed naive+aware crawled_at -> max(dates) at "
            "aggregator.py:94 raises uncaught TypeError (naive-vs-aware "
            "datetime seam, _compute_pages_per_day). Flip to hard pass once "
            "the implementer's fix is confirmed ON main."
        ),
    )
    def test_mixed_naive_aware_raises_type_error(self):
        pages = [
            _page("http://a.com", "2024-01-01T00:00:00"),          # naive
            _page("http://b.com", "2024-01-02T00:00:00+00:00"),    # aware
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-66: reverse direction (aware first, naive second) still mixes "
            "tz-awareness and hits the same uncaught TypeError. Flip on fix "
            "ON main."
        ),
    )
    def test_mixed_aware_naive_raises_type_error(self):
        pages = [
            _page("http://a.com", "2024-01-02T00:00:00+00:00"),    # aware
            _page("http://b.com", "2024-01-01T00:00:00"),          # naive
        ]
        stats = _aggregate(pages)
        assert stats.pages_per_day >= 0.0

    @pytest.mark.xfail(
        strict=True,
        reason=(
            "QA-66: three pages, two naive + one aware, still mixes "
            "tz-awareness and hits the uncaught TypeError. Flip on fix ON main."
        ),
    )
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


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
