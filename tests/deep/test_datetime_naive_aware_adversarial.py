"""Adversarial deep tests for the naive-vs-aware datetime comparison seam.

CLASS SWEEP (cycle 332): content_scoring._score_recency normalizes a naive
parsed timestamp to UTC-aware before comparing it to an aware cutoff
(``date.replace(tzinfo=timezone.utc)``). Two other public sites parse a
possibly-naive ISO string with ``datetime.fromisoformat`` and then compare it
to an internal ``datetime.now(timezone.utc)`` WITHOUT normalizing naive ->
aware first:

  * SitemapParser.get_recent_entries  (personal_index/sitemap.py)
  * ProgressTracker.elapsed_seconds   (personal_index/progress.py)

For a *naive* ISO timestamp (no tz suffix) ``fromisoformat`` succeeds (it is
NOT "unparseable"), but ``naive < aware`` / ``aware - naive`` raises
``TypeError``. In get_recent_entries that TypeError is swallowed by
``except (ValueError, TypeError): pass`` so the entry is silently dropped even
though the docstring contract says only *unparseable* lastmod values are
skipped. In elapsed_seconds the subtraction is OUTSIDE the try, so the
TypeError propagates and the property hard-crashes.

The xfail-strict pins document the two defects; the armor pins pin the
correct behavior that must hold regardless (aware timestamps work, unparseable
values are skipped, idempotence, e2e CLI).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.progress import ProgressTracker
from personal_index.sitemap import Sitemap, SitemapEntry, SitemapParser


def _old_naive_iso() -> str:
    """A naive ISO timestamp ~6 years in the past (no tz suffix)."""
    return (datetime.now(timezone.utc) - timedelta(days=2000)).replace(
        tzinfo=None
    ).isoformat()


def _old_aware_iso() -> str:
    """An aware ISO timestamp ~6 years in the past (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=2000)).isoformat()


def _recent_naive_iso() -> str:
    """A naive ISO timestamp ~1 day in the past (no tz suffix)."""
    return (datetime.now(timezone.utc) - timedelta(days=1)).replace(
        tzinfo=None
    ).isoformat()


def _recent_aware_iso() -> str:
    """An aware ISO timestamp ~1 day in the past (UTC)."""
    return (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()


# ---------------------------------------------------------------------------
# SitemapParser.get_recent_entries
# ---------------------------------------------------------------------------
class TestSitemapRecentEntriesNaive:
    @pytest.mark.xfail(strict=True, reason="QA-63: naive lastmod silently skipped (naive<aware TypeError swallowed)")
    def test_naive_old_timestamp_is_included(self):
        """DEFECT (QA-63): a parseable naive lastmod is silently skipped.

        The docstring contract says only *unparseable* lastmod values are
        skipped. A naive ISO string parses fine via fromisoformat, so it MUST
        be considered and included when within the window. Instead the
        ``naive < aware`` TypeError is swallowed and the entry is dropped.
        """
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=_old_naive_iso())])
        result = SitemapParser().get_recent_entries(sm, days=3650)
        assert [e.loc for e in result] == ["http://x"]

    def test_aware_old_timestamp_is_included(self):
        """ARMOR: an aware lastmod within the window is included (works today)."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=_old_aware_iso())])
        result = SitemapParser().get_recent_entries(sm, days=3650)
        assert [e.loc for e in result] == ["http://x"]

    def test_aware_recent_timestamp_is_included(self):
        """ARMOR: a recent aware lastmod is included."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=_recent_aware_iso())])
        result = SitemapParser().get_recent_entries(sm, days=30)
        assert [e.loc for e in result] == ["http://x"]

    def test_unparseable_lastmod_is_skipped(self):
        """ARMOR: a genuinely unparseable lastmod is skipped (contract holds)."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod="not-a-date")])
        result = SitemapParser().get_recent_entries(sm, days=3650)
        assert result == []

    def test_none_lastmod_is_skipped(self):
        """ARMOR: a None lastmod is skipped (falsy guard)."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=None)])
        result = SitemapParser().get_recent_entries(sm, days=3650)
        assert result == []

    def test_empty_lastmod_is_skipped(self):
        """ARMOR: an empty-string lastmod is skipped (falsy guard)."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod="")])
        result = SitemapParser().get_recent_entries(sm, days=3650)
        assert result == []

    @pytest.mark.xfail(strict=True, reason="QA-63: naive lastmod silently skipped (naive<aware TypeError swallowed)")
    def test_naive_recent_timestamp_is_included(self):
        """DEFECT (QA-63): a recent naive lastmod is also silently skipped."""
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=_recent_naive_iso())])
        result = SitemapParser().get_recent_entries(sm, days=30)
        assert [e.loc for e in result] == ["http://x"]

    def test_get_recent_entries_idempotent(self):
        """ARMOR: repeated calls return the same entry set (no mutation)."""
        lastmod = _old_aware_iso()
        sm = Sitemap(entries=[SitemapEntry(loc="http://x", lastmod=lastmod)])
        first = SitemapParser().get_recent_entries(sm, days=3650)
        second = SitemapParser().get_recent_entries(sm, days=3650)
        assert [e.loc for e in first] == [e.loc for e in second] == ["http://x"]
        assert sm.entries[0].lastmod == lastmod


# ---------------------------------------------------------------------------
# ProgressTracker.elapsed_seconds
# ---------------------------------------------------------------------------
class TestProgressElapsedSecondsNaive:
    @pytest.mark.xfail(strict=True, reason="QA-63: naive started_at hard-crashes elapsed_seconds (aware-naive TypeError outside try)")
    def test_naive_started_at_returns_float(self):
        """DEFECT (QA-63): a naive started_at hard-crashes elapsed_seconds.

        ``fromisoformat`` succeeds on a naive ISO string, but the subtraction
        ``now - start`` (now is UTC-aware) is OUTSIDE the try block, so the
        TypeError propagates. content_scoring normalizes naive -> UTC; the
        tracker should too, and return a non-negative float.
        """
        pt = ProgressTracker(operation_name="op", total_steps=10, current_step=5)
        pt.started_at = _old_naive_iso()
        elapsed = pt.elapsed_seconds
        assert isinstance(elapsed, float)
        assert elapsed > 0.0

    def test_aware_started_at_returns_float(self):
        """ARMOR: an aware started_at returns a positive float (works today)."""
        pt = ProgressTracker(operation_name="op", total_steps=10, current_step=5)
        pt.started_at = _old_aware_iso()
        elapsed = pt.elapsed_seconds
        assert isinstance(elapsed, float)
        assert elapsed > 0.0

    def test_none_started_at_returns_zero(self):
        """ARMOR: a None started_at returns 0.0 (falsy guard)."""
        pt = ProgressTracker(operation_name="op", total_steps=10, current_step=5)
        pt.started_at = None
        assert pt.elapsed_seconds == 0.0

    def test_unparseable_started_at_returns_zero(self):
        """ARMOR: an unparseable started_at returns 0.0 (contract holds)."""
        pt = ProgressTracker(operation_name="op", total_steps=10, current_step=5)
        pt.started_at = "not-a-date"
        assert pt.elapsed_seconds == 0.0

    def test_elapsed_seconds_idempotent(self):
        """ARMOR: repeated reads do not mutate started_at and stay non-negative."""
        started = _old_aware_iso()
        pt = ProgressTracker(operation_name="op", total_steps=10, current_step=5)
        pt.started_at = started
        first = pt.elapsed_seconds
        second = pt.elapsed_seconds
        assert first >= 0.0 and second >= 0.0
        # elapsed only advances forward, never regresses
        assert second >= first
        assert pt.started_at == started


# ---------------------------------------------------------------------------
# End-to-end CLI run (installed CLI, independent of the defect)
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_status_command_runs(self, tmp_path):
        """ARMOR: the installed CLI runs end-to-end (status on empty data dir)."""
        runner = CliRunner()
        result = runner.invoke(main, ["status", "--data-dir", str(tmp_path)])
        assert result.exit_code == 0, result.output

    def test_help_runs(self):
        """ARMOR: the installed CLI help runs end-to-end."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0, result.output
        assert "personal-index" in result.output
