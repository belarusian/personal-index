"""Adversarial deep tests for personal_index.content_feed naive/aware sort seam.

Contract source: docs/content-feed.md (Status: spec). Cycle 347 added
test_url_filter_deep_adversarial.py; this cycle deepens content_feed, whose
most recent change (commit 2d3718e, QA-67) introduced ``_normalize_tz`` to
make the ``add_item`` sort tolerate a mix of naive and aware ``published``
datetimes (previously ``TypeError: can't compare offset-naive and offset-aware
datetimes``). The cycle-273 deep file predates that fix and never exercised
naive/aware mixing, so this seam was unprobed.

All assertions are re-derived against the ACTUAL result shape on current main
(naive treated as UTC via ``replace(tzinfo=timezone.utc)``), not the defect-era
shape. This is a regression-armor cycle: every test passes against current main.
"""

from __future__ import annotations

import subprocess
import sys
from datetime import datetime, timezone

from personal_index.content_feed import FeedFormat, FeedGenerator, FeedItem


# ---------------------------------------------------------------------------
# QA-67 seam: add_item sort tolerates naive/aware mixing (no TypeError)
# ---------------------------------------------------------------------------
class TestNaiveAwareSortSeam:
    def test_mixed_naive_aware_no_typeerror(self):
        # Pre-QA-67 this raised TypeError comparing naive vs aware.
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="naive", link="http://x/n",
                            published=datetime(2020, 1, 1)))
        g.add_item(FeedItem(title="aware", link="http://x/a",
                            published=datetime(2021, 1, 1, tzinfo=timezone.utc)))
        assert [i.title for i in g.items] == ["aware", "naive"]

    def test_naive_treated_as_utc_loses_to_later_aware(self):
        # naive 2020-01-01 == aware 2020-01-01T00:00:00Z; the +1s aware is newer.
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="naive", link="http://x/n",
                            published=datetime(2020, 1, 1)))
        g.add_item(FeedItem(title="aware", link="http://x/a",
                            published=datetime(2020, 1, 1, 0, 0, 1, tzinfo=timezone.utc)))
        assert [i.title for i in g.items] == ["aware", "naive"]

    def test_naive_newer_than_aware_wins(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="aware-old", link="http://x/a",
                            published=datetime(2019, 1, 1, tzinfo=timezone.utc)))
        g.add_item(FeedItem(title="naive-new", link="http://x/n",
                            published=datetime(2022, 1, 1)))
        assert [i.title for i in g.items] == ["naive-new", "aware-old"]

    def test_all_naive_sorts_fine(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="a", link="http://x/a", published=datetime(2019, 1, 1)))
        g.add_item(FeedItem(title="b", link="http://x/b", published=datetime(2021, 1, 1)))
        g.add_item(FeedItem(title="c", link="http://x/c", published=datetime(2020, 1, 1)))
        assert [i.title for i in g.items] == ["b", "c", "a"]

    def test_all_aware_sorts_fine(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="a", link="http://x/a",
                            published=datetime(2019, 1, 1, tzinfo=timezone.utc)))
        g.add_item(FeedItem(title="b", link="http://x/b",
                            published=datetime(2021, 1, 1, tzinfo=timezone.utc)))
        assert [i.title for i in g.items] == ["b", "a"]

    def test_mixed_sort_is_stable_under_cap(self):
        # Cap drops oldest; naive/aware mixing must not crash the cap path.
        g = FeedGenerator(title="t", link="http://x", max_items=2)
        g.add_item(FeedItem(title="oldest-naive", link="http://x/1",
                            published=datetime(2018, 1, 1)))
        g.add_item(FeedItem(title="mid-aware", link="http://x/2",
                            published=datetime(2019, 1, 1, tzinfo=timezone.utc)))
        g.add_item(FeedItem(title="newest-naive", link="http://x/3",
                            published=datetime(2020, 1, 1)))
        assert [i.title for i in g.items] == ["newest-naive", "mid-aware"]


# ---------------------------------------------------------------------------
# naive/aware round-trip through to_dict/from_dict
# ---------------------------------------------------------------------------
class TestNaiveAwareRoundTrip:
    def test_naive_published_round_trips_as_naive(self):
        naive = datetime(2020, 1, 1)
        item = FeedItem(title="n", link="http://x/n", published=naive)
        d = item.to_dict()
        assert d["published"] == naive.isoformat()  # no offset suffix
        restored = FeedItem.from_dict(d)
        assert restored.published == naive
        assert restored.published.tzinfo is None

    def test_aware_published_round_trips_as_aware(self):
        aware = datetime(2020, 1, 1, tzinfo=timezone.utc)
        item = FeedItem(title="a", link="http://x/a", published=aware)
        d = item.to_dict()
        restored = FeedItem.from_dict(d)
        assert restored.published == aware
        assert restored.published.tzinfo is not None

    def test_mixed_generator_round_trip_preserves_order(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="new", link="http://x/new",
                            published=datetime(2021, 1, 1, tzinfo=timezone.utc)))
        g.add_item(FeedItem(title="old", link="http://x/old",
                            published=datetime(2019, 1, 1)))
        restored = FeedGenerator.from_dict(g.to_dict())
        assert [i.title for i in restored.items] == ["new", "old"]


# ---------------------------------------------------------------------------
# from_dict assigns items directly (no re-sort / no cap) — documented asymmetry
# ---------------------------------------------------------------------------
class TestFromDictDirectAssign:
    def test_from_dict_does_not_resort_mixed_tz(self):
        g = FeedGenerator(title="t", link="http://x", max_items=2)
        g.items = [
            FeedItem(title="old", link="http://x/old",
                     published=datetime(2019, 1, 1, tzinfo=timezone.utc)),
            FeedItem(title="new", link="http://x/new",
                     published=datetime(2021, 1, 1, tzinfo=timezone.utc)),
        ]
        restored = FeedGenerator.from_dict(g.to_dict())
        # from_dict assigns items directly, so order is preserved (NOT re-sorted).
        assert [i.title for i in restored.items] == ["old", "new"]


# ---------------------------------------------------------------------------
# generate() with naive/aware items (formatting must not crash)
# ---------------------------------------------------------------------------
class TestGenerateMixedTz:
    def test_rss_generate_with_mixed_tz(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="naive", link="http://x/n",
                            published=datetime(2020, 1, 1)))
        g.add_item(FeedItem(title="aware", link="http://x/a",
                            published=datetime(2021, 1, 1, tzinfo=timezone.utc)))
        out = g.generate(FeedFormat.RSS)
        assert "<item>" in out
        assert out.rstrip().endswith("</rss>")

    def test_atom_generate_with_mixed_tz(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="naive", link="http://x/n",
                            published=datetime(2020, 1, 1)))
        g.add_item(FeedItem(title="aware", link="http://x/a",
                            published=datetime(2021, 1, 1, tzinfo=timezone.utc)))
        out = g.generate(FeedFormat.ATOM)
        assert "<entry>" in out
        assert out.rstrip().endswith("</feed>")


# ---------------------------------------------------------------------------
# ttl / generator field adversarial inputs
# ---------------------------------------------------------------------------
class TestTtlAndGeneratorFields:
    def test_negative_ttl_serialized_as_is(self):
        g = FeedGenerator(title="t", link="http://x", ttl=-10)
        out = g.generate(FeedFormat.RSS)
        assert "<ttl>-10</ttl>" in out

    def test_zero_ttl_serialized(self):
        g = FeedGenerator(title="t", link="http://x", ttl=0)
        out = g.generate(FeedFormat.RSS)
        assert "<ttl>0</ttl>" in out

    def test_empty_generator_string_serialized(self):
        g = FeedGenerator(title="t", link="http://x", generator="")
        out = g.generate(FeedFormat.RSS)
        assert "<generator></generator>" in out


# ---------------------------------------------------------------------------
# negative max_items is GUARDED (per-add cap -> empty), NOT a negative-slice leak
# ---------------------------------------------------------------------------
class TestNegativeMaxItemsGuarded:
    def test_negative_max_items_never_leaks_partial_page(self):
        # The cap runs after EVERY add, so the list never grows past 1 element;
        # items[:-N] on a <=1-element list is empty. This is the clean guard
        # shape (incremental cap), NOT the terminal items[:max_items] leak.
        for neg in (-1, -2, -5, -100):
            g = FeedGenerator(title="t", link="http://x", max_items=neg)
            for i in range(20):
                g.add_item(FeedItem(title=str(i), link=f"http://x/{i}",
                                    published=datetime(2020, 1, 1, tzinfo=timezone.utc)))
            assert g.items == [], f"max_items={neg} leaked {len(g.items)} items"


# ---------------------------------------------------------------------------
# end-to-end CLI run (installed personal-index CLI must still work)
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_help_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "personal_index", "--help"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout.lower() or "personal" in result.stdout.lower()
