"""Cycle 336 VALIDATOR probe: naive-vs-aware datetime seam in
personal_index.search_facets.faceted_search.FacetedSearch.

CLASS SWEEP LEAD (carry-over from QA-62/63/64): the naive-vs-aware datetime
seam is a MULTI-SITE class. A site is a ``datetime.fromisoformat`` result
compared against an aware bound (``datetime.now(timezone.utc)`` / an aware
ISO string) with an ``except`` that omits ``TypeError``.

Already filed:
  * content_archive.archive_old            -> QA-62 (VERIFIED, fixed)
  * sitemap.get_recent_entries +
    progress.elapsed_seconds               -> QA-63 (OPEN)
  * auth/api_keys.validate_key             -> QA-64 (OPEN)

NEW site found this cycle (QA-65):
  * search_facets.faceted_search.FacetedSearch._parse_date_value ->
    _matches_range_filter -> _check_{between,gte,lte,gt,lt}

``_parse_date_value`` (faceted_search.py:289) parses an ISO string with
``datetime.fromisoformat`` and returns the resulting datetime. The result is
then compared against the filter bound in ``_check_*`` (faceted_search.py:
239/247/255/263/271). When the DOCUMENT value is a naive ISO string and the
filter bound is an aware ISO string (or vice-versa), the comparison raises an
uncaught ``TypeError: can't compare offset-naive and offset-aware datetimes``.

The reference fix (content_scoring._score_recency, content_scoring.py:267-268)
normalizes a naive datetime to UTC-aware via ``replace(tzinfo=timezone.utc)``
before comparing. The same normalization is missing here.

These xfail-strict pins DOCUMENT the defect (they fail on current main). They
must be flipped to hard passes ONLY once the implementer's fix is confirmed ON
main (see QA-65).
"""

from __future__ import annotations

import subprocess
import sys

import pytest

from personal_index.search_facets.faceted_search import FacetedSearch

NAIVE_DOC = "2024-06-01T00:00:00"          # naive (no tz)
AWARE_DOC = "2024-06-01T00:00:00+00:00"    # aware UTC
AWARE_BOUND = "2024-03-01T00:00:00+00:00"  # aware UTC
NAIVE_BOUND = "2024-03-01T00:00:00"        # naive


def _fs(doc_published: str) -> FacetedSearch:
    fs = FacetedSearch()
    fs.add_document("c", {"title": "z", "published": doc_published})
    return fs


class TestNaiveAwareRangeSeam:
    """The seam: naive doc value vs aware filter bound (and reverse)."""

    def test_naive_doc_aware_bound_gte(self):
        r = _fs(NAIVE_DOC).search("", filters={"published": {"$gte": AWARE_BOUND}})
        assert r.total == 1

    def test_naive_doc_aware_bound_lte(self):
        # RECONCILED (cycle 342, QA-65 fix 24a4220 ON main): the TypeError is
        # gone. The prior xfail-strict pin asserted total == 1, a latent
        # validator bug - NAIVE_DOC is June, AWARE_BOUND is March, so
        # June <= March is False and the correct total is 0.
        r = _fs(NAIVE_DOC).search("", filters={"published": {"$lte": AWARE_BOUND}})
        assert r.total == 0

    def test_naive_doc_aware_bound_gt(self):
        r = _fs(NAIVE_DOC).search("", filters={"published": {"$gt": AWARE_BOUND}})
        assert r.total == 1

    def test_naive_doc_aware_bound_lt(self):
        # RECONCILED (cycle 342, QA-65 fix 24a4220 ON main): the TypeError is
        # gone. The prior xfail-strict pin asserted total == 1, a latent
        # validator bug - NAIVE_DOC is June, AWARE_BOUND is March, so
        # June < March is False and the correct total is 0.
        r = _fs(NAIVE_DOC).search("", filters={"published": {"$lt": AWARE_BOUND}})
        assert r.total == 0

    def test_aware_doc_naive_bound_gte(self):
        r = _fs(AWARE_DOC).search("", filters={"published": {"$gte": NAIVE_BOUND}})
        assert r.total == 1

    def test_naive_doc_aware_between(self):
        r = _fs(NAIVE_DOC).search(
            "",
            filters={
                "published": {
                    "$between": ["2024-01-01T00:00:00+00:00", "2024-12-01T00:00:00+00:00"]
                }
            },
        )
        assert r.total == 1


class TestBothAwareNoSeam:
    """Armor: when both sides are aware (or both naive) there is NO seam and
    the range filter works. These must stay green on current main."""

    def test_aware_doc_aware_bound_gte(self):
        r = _fs(AWARE_DOC).search("", filters={"published": {"$gte": AWARE_BOUND}})
        assert r.total == 1

    def test_aware_doc_aware_bound_lte(self):
        # AWARE_DOC (2024-06-01) is AFTER AWARE_BOUND (2024-03-01), so
        # doc <= bound is False -> excluded. (Both aware, no seam.)
        r = _fs(AWARE_DOC).search("", filters={"published": {"$lte": AWARE_BOUND}})
        assert r.total == 0

    def test_naive_doc_naive_bound_gte(self):
        # Both naive -> comparable, no TypeError.
        r = _fs(NAIVE_DOC).search("", filters={"published": {"$gte": NAIVE_BOUND}})
        assert r.total == 1

    def test_aware_doc_aware_between(self):
        r = _fs(AWARE_DOC).search(
            "",
            filters={
                "published": {
                    "$between": ["2024-01-01T00:00:00+00:00", "2024-12-01T00:00:00+00:00"]
                }
            },
        )
        assert r.total == 1


class TestRangeFilterGuards:
    """Armor: guard inputs on the range filter path (None/empty/unicode/
    out-of-range) that do NOT touch the naive-vs-aware seam."""

    def test_none_doc_value_excluded(self):
        fs = FacetedSearch()
        fs.add_document("a", {"title": "x", "published": None})
        r = fs.search("", filters={"published": {"$gte": AWARE_BOUND}})
        assert r.total == 0

    def test_non_date_string_doc_value_no_crash(self):
        # When BOTH the doc value and the bound are non-ISO strings, neither
        # parses to a datetime, so the filter falls back to a plain string
        # comparison and must not raise. (A non-date doc value vs a DATE bound
        # is a separate robustness gap, not the naive-vs-aware seam.)
        fs = FacetedSearch()
        fs.add_document("a", {"title": "x", "published": "zzz"})
        r = fs.search("", filters={"published": {"$gte": "aaa"}})
        assert r.total == 1  # "zzz" >= "aaa", no crash

    def test_aware_doc_out_of_range_excluded(self):
        # A doc published AFTER the $lte bound is excluded (correct range
        # semantics, both aware).
        fs = FacetedSearch()
        fs.add_document("a", {"title": "x", "published": "2025-06-01T00:00:00+00:00"})
        r = fs.search("", filters={"published": {"$lte": AWARE_BOUND}})
        assert r.total == 0

    def test_empty_filter_matches_all(self):
        fs = FacetedSearch()
        fs.add_document("a", {"title": "x", "published": AWARE_DOC})
        r = fs.search("", filters={})
        assert r.total == 1


class TestCliEndToEnd:
    def test_init_then_search_empty_index(self, tmp_path):
        # End-to-end: init a data dir, then search an empty index -> the
        # documented "No indexed content found." notice, exit code 0.
        env_dir = str(tmp_path / "dd")
        r1 = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r1.returncode == 0, r1.stderr
        r2 = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "hello",
             "--data-dir", env_dir],
            capture_output=True, text=True, timeout=60,
        )
        assert r2.returncode == 0, r2.stderr
        assert "No indexed content found" in r2.stdout


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-q"]))
