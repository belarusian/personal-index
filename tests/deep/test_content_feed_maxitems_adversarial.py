"""Cycle 345 VALIDATOR probe: content_feed max_items cap + from_dict asymmetry.

content_feed changed on main via the QA-67 fix (2d3718e, 2026-09-21) which
added the `_normalize_tz` helper to the `add_item` sort. The module-specific
deep file (test_content_feed_adversarial.py, last touched 2026-09-14) predates
that change, so this cycle deepens the cap / round-trip surface that the fix
touched.

Contract source: docs/content-feed.md (Status: spec, audited cycle 217).

Key documented behaviors pinned here:
  * `add_item` is the ONLY path that enforces the cap + ordering (doc line 45).
    A NEGATIVE `max_items` is guarded: the incremental `items[:max_items]`
    truncation after each add yields an EMPTY list (not a Python negative-slice
    leak of all-but-last), because the cap runs after EVERY add, not once at
    the end.
  * `from_dict` assigns `gen.items = items` directly, BYPASSING `add_item`, so
    NO re-sort/cap on load (doc line 60, ARCH-54 "contract hole"). The round-trip
    is lossless for the nine FIELDS (max_items value preserved) but the item
    CAP is NOT re-applied on load.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from personal_index.content_feed import FeedFormat, FeedGenerator, FeedItem


def _item(link: str, minutes_ago: int) -> FeedItem:
    return FeedItem(
        title=link,
        link=link,
        published=datetime.now(timezone.utc) - timedelta(minutes=minutes_ago),
    )


# ---------------------------------------------------------------------------
# Negative max_items is guarded (incremental cap -> empty, not a slice leak)
# ---------------------------------------------------------------------------
class TestNegativeMaxItemsGuarded:
    def test_negative_max_items_yields_empty(self):
        # A negative bound must NOT leak Python negative-slice semantics
        # (items[:-1] = all-but-last). Because add_item re-caps after EVERY
        # add, a negative bound truncates to empty on the first add.
        g = FeedGenerator(title="t", link="http://x", max_items=-1)
        for i in range(4):
            g.add_item(_item(f"http://x/{i}", i))
        assert g.items == []

    def test_negative_max_items_various(self):
        for neg in (-1, -2, -5, -100):
            g = FeedGenerator(title="t", link="http://x", max_items=neg)
            for i in range(5):
                g.add_item(_item(f"http://x/{i}", i))
            assert g.items == [], f"max_items={neg} leaked {len(g.items)} items"

    def test_zero_max_items_yields_empty(self):
        g = FeedGenerator(title="t", link="http://x", max_items=0)
        g.add_item(_item("a", 1))
        assert g.items == []

    def test_positive_cap_drops_oldest(self):
        g = FeedGenerator(title="t", link="http://x", max_items=2)
        g.add_item(_item("oldest", 300))
        g.add_item(_item("middle", 100))
        g.add_item(_item("newest", 1))
        assert [i.link for i in g.items] == ["newest", "middle"]


# ---------------------------------------------------------------------------
# from_dict documented asymmetry (ARCH-54): cap NOT re-applied on load
# ---------------------------------------------------------------------------
class TestFromDictCapAsymmetry:
    def test_from_dict_does_not_reapply_cap(self):
        # doc line 60: from_dict assigns gen.items = items directly, bypassing
        # add_item, so no re-sort/cap on load. 5 items with max_items=2 stay 5.
        d = {
            "title": "t",
            "link": "http://x",
            "max_items": 2,
            "items": [
                {"title": str(i), "link": f"http://x/{i}"} for i in range(5)
            ],
        }
        g = FeedGenerator.from_dict(d)
        assert len(g.items) == 5
        assert g.max_items == 2

    def test_from_dict_preserves_max_items_field(self):
        # The round-trip is lossless for the nine FIELDS: the max_items VALUE
        # survives even though the item cap is not re-applied.
        d = {
            "title": "t",
            "link": "http://x",
            "max_items": 7,
            "items": [{"title": str(i), "link": f"http://x/{i}"} for i in range(3)],
        }
        g = FeedGenerator.from_dict(d)
        rt = FeedGenerator.from_dict(g.to_dict())
        assert rt.max_items == 7
        assert len(rt.items) == 3

    def test_from_dict_empty_items(self):
        g = FeedGenerator.from_dict({"title": "t", "link": "http://x"})
        assert g.items == []
        assert g.max_items == 100  # default


# ---------------------------------------------------------------------------
# Out-of-range max_items (huge) is a no-op cap
# ---------------------------------------------------------------------------
class TestHugeMaxItems:
    def test_huge_max_items_keeps_all(self):
        g = FeedGenerator(title="t", link="http://x", max_items=10**9)
        for i in range(5):
            g.add_item(_item(f"http://x/{i}", i))
        assert len(g.items) == 5


# ---------------------------------------------------------------------------
# generate() with a None published (post-init default is now-utc, so it is
# never actually None here, but pin the format path defensively)
# ---------------------------------------------------------------------------
class TestGenerateNonePublished:
    def test_rss_pubdate_present_for_default_published(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="np", link="http://x/np"))
        rss = g.generate(FeedFormat.RSS)
        assert "<pubDate>" in rss

    def test_atom_published_present_for_default_published(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="np", link="http://x/np"))
        atom = g.generate(FeedFormat.ATOM)
        assert "<published>" in atom


# ---------------------------------------------------------------------------
# Unicode round-trip through to_dict/from_dict (cap + fields)
# ---------------------------------------------------------------------------
class TestUnicodeRoundTrip:
    def test_unicode_title_and_language_round_trip(self):
        g = FeedGenerator(title="t\u00bd\u00e9", link="http://x", language="fr-\u00e9")
        g.add_item(FeedItem(title="<b>&amp;</b>", link="http://x/u"))
        rt = FeedGenerator.from_dict(g.to_dict())
        assert rt.title == "t\u00bd\u00e9"
        assert rt.language == "fr-\u00e9"
        assert rt.items[0].title == "<b>&amp;</b>"

    def test_generate_escapes_unicode_and_entities(self):
        g = FeedGenerator(title="t\u00bd\u00e9", link="http://x")
        g.add_item(FeedItem(title="<b>&amp;</b>", link="http://x/u"))
        rss = g.generate(FeedFormat.RSS)
        assert "&lt;b&gt;&amp;amp;&lt;/b&gt;" in rss
        assert "t\u00bd\u00e9" in rss
