"""Adversarial deep tests for personal_index.content_feed INTERNAL helpers.

Cycle 375 — VALIDATOR probe. The cycle-273 file pins the public surface
(FeedItem / FeedGenerator) end-to-end but never pins the module-level
``_normalize_tz`` helper or the ``FeedGenerator._format_rss_date`` /
``_format_atom_date`` date formatters directly. These are the naive/aware
seam and the RSS/Atom timestamp contract, so they get their own regression
armor here.

Contract source: personal_index/content_feed.py docstrings.
- _normalize_tz: None -> aware datetime.min sentinel; naive -> UTC-aware via
  replace(tzinfo=utc); aware -> returned unchanged. Guarantees a naive and an
  aware published never raise TypeError at the sort.
- _format_rss_date: RFC-822-ish "%a, %d %b %Y %H:%M:%S %z"; None -> now(utc).
- _format_atom_date: ISO-8601; None -> now(utc).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from personal_index.content_feed import (
    FeedFormat,
    FeedGenerator,
    _normalize_tz,
)


# ---------------------------------------------------------------------------
# _normalize_tz — the naive/aware sort seam
# ---------------------------------------------------------------------------
class TestNormalizeTz:
    def test_none_maps_to_aware_min_sentinel(self) -> None:
        r = _normalize_tz(None)
        assert r == datetime.min.replace(tzinfo=timezone.utc)
        assert r.tzinfo is not None

    def test_naive_becomes_utc_aware_same_wall_time(self) -> None:
        naive = datetime(2026, 9, 22, 10, 52, 28)
        r = _normalize_tz(naive)
        assert r.tzinfo is not None
        assert r.utcoffset() == timedelta(0)
        # wall clock preserved by replace()
        assert (r.year, r.month, r.day, r.hour, r.minute, r.second) == (
            2026, 9, 22, 10, 52, 28,
        )

    def test_aware_returned_unchanged(self) -> None:
        aware = datetime(2026, 9, 22, 10, 52, 28, tzinfo=timezone.utc)
        r = _normalize_tz(aware)
        assert r is aware

    def test_non_utc_aware_offset_preserved(self) -> None:
        plus2 = timezone(timedelta(hours=2))
        aware = datetime(2026, 9, 22, 10, 0, 0, tzinfo=plus2)
        r = _normalize_tz(aware)
        assert r.utcoffset() == timedelta(hours=2)

    def test_idempotent(self) -> None:
        naive = datetime(2026, 1, 1, 0, 0, 0)
        once = _normalize_tz(naive)
        twice = _normalize_tz(once)
        assert once == twice
        assert twice.tzinfo is not None

    def test_naive_and_aware_compare_without_typeerror(self) -> None:
        # the whole point of the helper: mixed naive/aware must sort cleanly
        naive = _normalize_tz(datetime(2026, 1, 1, 0, 0, 0))
        aware = _normalize_tz(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        # both now UTC-aware and equal
        assert naive == aware
        ordered = sorted([aware, naive])
        assert len(ordered) == 2

    def test_none_sorts_before_any_real_timestamp(self) -> None:
        sentinel = _normalize_tz(None)
        real = _normalize_tz(datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc))
        assert sentinel < real


# ---------------------------------------------------------------------------
# FeedGenerator._format_rss_date — RFC-822-ish timestamp
# ---------------------------------------------------------------------------
class TestFormatRssDate:
    def _gen(self) -> FeedGenerator:
        return FeedGenerator(title="t", link="https://x.example")

    def test_none_returns_nonempty_now_utc(self) -> None:
        s = self._gen()._format_rss_date(None)
        assert isinstance(s, str)
        assert len(s) >= 20
        # now(utc) carries a +0000 offset
        assert s.endswith("+0000")

    def test_aware_datetime_carries_offset(self) -> None:
        aware = datetime(2026, 9, 22, 10, 52, 28, tzinfo=timezone.utc)
        s = self._gen()._format_rss_date(aware)
        assert s.endswith("+0000")
        assert "2026" in s
        assert "Sep" in s

    def test_naive_datetime_has_empty_z(self) -> None:
        # naive -> strftime %z yields '' (no offset suffix)
        naive = datetime(2026, 9, 22, 10, 52, 28)
        s = self._gen()._format_rss_date(naive)
        assert "2026" in s
        assert "+0000" not in s

    def test_non_utc_offset_rendered(self) -> None:
        plus2 = timezone(timedelta(hours=2))
        aware = datetime(2026, 9, 22, 10, 0, 0, tzinfo=plus2)
        s = self._gen()._format_rss_date(aware)
        assert s.endswith("+0200")


# ---------------------------------------------------------------------------
# FeedGenerator._format_atom_date — ISO-8601 timestamp
# ---------------------------------------------------------------------------
class TestFormatAtomDate:
    def _gen(self) -> FeedGenerator:
        return FeedGenerator(title="t", link="https://x.example")

    def test_none_returns_iso_now_utc(self) -> None:
        s = self._gen()._format_atom_date(None)
        assert isinstance(s, str)
        assert "T" in s
        assert s.endswith("+00:00")

    def test_aware_datetime_iso_with_offset(self) -> None:
        aware = datetime(2026, 9, 22, 10, 52, 28, tzinfo=timezone.utc)
        s = self._gen()._format_atom_date(aware)
        assert s == "2026-09-22T10:52:28+00:00"

    def test_naive_datetime_iso_no_offset(self) -> None:
        naive = datetime(2026, 9, 22, 10, 52, 28)
        s = self._gen()._format_atom_date(naive)
        assert s == "2026-09-22T10:52:28"

    def test_non_utc_offset_iso(self) -> None:
        plus2 = timezone(timedelta(hours=2))
        aware = datetime(2026, 9, 22, 10, 0, 0, tzinfo=plus2)
        s = self._gen()._format_atom_date(aware)
        assert s.endswith("+02:00")


# ---------------------------------------------------------------------------
# get_feed_type — MIME contract (direct, not via generate)
# ---------------------------------------------------------------------------
class TestGetFeedType:
    def _gen(self) -> FeedGenerator:
        return FeedGenerator(title="t", link="https://x.example")

    def test_rss_mime(self) -> None:
        assert self._gen().get_feed_type(FeedFormat.RSS) == "application/rss+xml"

    def test_atom_mime(self) -> None:
        assert self._gen().get_feed_type(FeedFormat.ATOM) == "application/atom+xml"


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(pytest.main([__file__, "-v"]))
