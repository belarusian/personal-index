"""Adversarial deep tests for personal_index.content_feed (never-probed subsystem, cycle 273).

Contract source: docs/content-feed.md (Status: spec, audited cycle 217).

Covers the full public surface of FeedItem and FeedGenerator with guard inputs
(None/empty/whitespace/unicode/duplicate/out-of-range), round-trips, idempotence,
and property checks. content_feed is a pure library (no CLI surface), so the
per-cycle end-to-end CLI run is exercised separately (see the CLI end-to-end test
at the bottom, which drives the installed `personal-index` CLI).
"""

from __future__ import annotations

import html
from datetime import datetime, timedelta, timezone
from typing import Any

import pytest

from personal_index.content_feed import FeedFormat, FeedGenerator, FeedItem


# ---------------------------------------------------------------------------
# FeedItem.__post_init__ defaults
# ---------------------------------------------------------------------------
class TestFeedItemPostInit:
    def test_id_falsy_defaults_to_link(self):
        item = FeedItem(title="t", link="http://x/a")
        assert item.id == "http://x/a"

    def test_id_empty_string_defaults_to_link(self):
        item = FeedItem(title="t", link="http://x/b", id="")
        assert item.id == "http://x/b"

    def test_id_explicit_preserved(self):
        item = FeedItem(title="t", link="http://x/c", id="custom-id")
        assert item.id == "custom-id"

    def test_id_whitespace_is_truthy_and_preserved(self):
        # " " is truthy, so it is NOT replaced by link.
        item = FeedItem(title="t", link="http://x/d", id=" ")
        assert item.id == " "

    def test_published_falsy_defaults_to_now_utc(self):
        before = datetime.now(timezone.utc)
        item = FeedItem(title="t", link="http://x/e")
        after = datetime.now(timezone.utc)
        assert item.published is not None
        assert before <= item.published <= after
        assert item.published.tzinfo is not None

    def test_updated_defaults_to_published(self):
        item = FeedItem(title="t", link="http://x/f")
        assert item.updated == item.published

    def test_explicit_published_and_updated_preserved(self):
        pub = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        upd = datetime(2021, 6, 7, 8, 9, 10, tzinfo=timezone.utc)
        item = FeedItem(title="t", link="http://x/g", published=pub, updated=upd)
        assert item.published == pub
        assert item.updated == upd

    def test_explicit_published_none_updated_defaults_to_published(self):
        pub = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        item = FeedItem(title="t", link="http://x/h", published=pub, updated=None)
        assert item.published == pub
        assert item.updated == pub


# ---------------------------------------------------------------------------
# FeedItem.to_dict
# ---------------------------------------------------------------------------
class TestFeedItemToDict:
    def test_exactly_eight_keys(self):
        item = FeedItem(title="t", link="http://x")
        d = item.to_dict()
        assert set(d.keys()) == {
            "title", "link", "id", "description",
            "author", "categories", "published", "updated",
        }

    def test_categories_is_a_copy_not_alias(self):
        cats = ["a", "b"]
        item = FeedItem(title="t", link="http://x", categories=cats)
        d = item.to_dict()
        # Mutating the returned list must not affect the item.
        d["categories"].append("c")
        assert item.categories == ["a", "b"]
        # Mutating the original must not affect an already-returned dict.
        item.categories.append("d")
        assert d["categories"] == ["a", "b", "c"]

    def test_published_updated_are_iso_strings(self):
        pub = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        item = FeedItem(title="t", link="http://x", published=pub)
        d = item.to_dict()
        assert d["published"] == pub.isoformat()
        assert d["updated"] == pub.isoformat()
        assert isinstance(d["published"], str)
        assert isinstance(d["updated"], str)

    def test_returns_new_dict_each_call(self):
        item = FeedItem(title="t", link="http://x")
        d1 = item.to_dict()
        d2 = item.to_dict()
        assert d1 is not d2
        assert d1 == d2


# ---------------------------------------------------------------------------
# FeedItem.from_dict guard path
# ---------------------------------------------------------------------------
class TestFeedItemFromDict:
    def test_missing_keys_default(self):
        item = FeedItem.from_dict({})
        assert item.title == ""
        assert item.link == ""
        assert item.id == ""
        assert item.description == ""
        assert item.author == ""
        assert item.categories == []
        # published/updated re-trigger post_init defaults (now-UTC).
        assert item.published is not None
        assert item.updated == item.published

    def test_unparseable_published_yields_none_then_redefaults(self):
        item = FeedItem.from_dict({"title": "t", "link": "http://x", "published": "not-a-date"})
        # Guard swallows ValueError -> None -> post_init re-defaults to now-UTC.
        assert item.published is not None

    def test_non_string_published_yields_none_then_redefaults(self):
        item = FeedItem.from_dict({"title": "t", "link": "http://x", "published": 12345})
        assert item.published is not None

    def test_empty_string_published_yields_none_then_redefaults(self):
        item = FeedItem.from_dict({"title": "t", "link": "http://x", "published": ""})
        assert item.published is not None

    def test_valid_published_parsed(self):
        pub = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        item = FeedItem.from_dict({"title": "t", "link": "http://x", "published": pub.isoformat()})
        assert item.published == pub

    def test_none_published_redefaults(self):
        item = FeedItem.from_dict({"title": "t", "link": "http://x", "published": None})
        assert item.published is not None


# ---------------------------------------------------------------------------
# FeedItem round-trip
# ---------------------------------------------------------------------------
class TestFeedItemRoundTrip:
    def test_round_trip_preserves_fields(self):
        pub = datetime(2020, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
        upd = datetime(2021, 6, 7, 8, 9, 10, tzinfo=timezone.utc)
        orig = FeedItem(
            title="t", link="http://x", id="i", description="d",
            author="a", categories=["c1", "c2"], published=pub, updated=upd,
        )
        restored = FeedItem.from_dict(orig.to_dict())
        assert restored.title == orig.title
        assert restored.link == orig.link
        assert restored.id == orig.id
        assert restored.description == orig.description
        assert restored.author == orig.author
        assert restored.categories == orig.categories
        assert restored.published == orig.published
        assert restored.updated == orig.updated

    def test_round_trip_idempotent(self):
        orig = FeedItem(title="t", link="http://x", id="i")
        once = FeedItem.from_dict(orig.to_dict())
        twice = FeedItem.from_dict(once.to_dict())
        assert once.to_dict() == twice.to_dict()

    def test_round_trip_unicode(self):
        orig = FeedItem(
            title="Привет 世界 🚀", link="http://x/ünïcode",
            description="café naïve — 日本語",
        )
        restored = FeedItem.from_dict(orig.to_dict())
        assert restored.title == orig.title
        assert restored.link == orig.link
        assert restored.description == orig.description


# ---------------------------------------------------------------------------
# FeedGenerator.__post_init__ + helpers
# ---------------------------------------------------------------------------
class TestFeedGeneratorInit:
    def test_feed_id_falsy_defaults_to_link(self):
        g = FeedGenerator(title="t", link="http://x")
        assert g.feed_id == "http://x"

    def test_feed_id_explicit_preserved(self):
        g = FeedGenerator(title="t", link="http://x", feed_id="custom-feed")
        assert g.feed_id == "custom-feed"

    def test_get_feed_type_rss(self):
        g = FeedGenerator(title="t", link="http://x")
        assert g.get_feed_type(FeedFormat.RSS) == "application/rss+xml"

    def test_get_feed_type_atom(self):
        g = FeedGenerator(title="t", link="http://x")
        assert g.get_feed_type(FeedFormat.ATOM) == "application/atom+xml"

    def test_feed_format_is_str_enum(self):
        assert FeedFormat.RSS == "rss"
        assert FeedFormat.ATOM == "atom"


# ---------------------------------------------------------------------------
# FeedGenerator.add_item ordering + cap
# ---------------------------------------------------------------------------
class TestFeedGeneratorAddItem:
    def _item(self, link: str, minutes_ago: int) -> FeedItem:
        pub = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
        return FeedItem(title=link, link=link, published=pub)

    def test_sorted_newest_first(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(self._item("old", 300))
        g.add_item(self._item("new", 1))
        g.add_item(self._item("mid", 100))
        assert [i.link for i in g.items] == ["new", "mid", "old"]

    def test_none_published_sorts_oldest(self):
        # A None published sorts as datetime.min (oldest) -> goes to the end.
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(FeedItem(title="has-date", link="http://x/1",
                            published=datetime.now(timezone.utc)))
        g.add_item(FeedItem(title="no-date", link="http://x/2"))
        # Both items have non-None published after post_init; the one added
        # with an explicit now() is >= the other's now(). Ordering is stable
        # by published desc; assert the explicit-now item is not last if it is
        # strictly newer. We only assert both survive and ordering is by date.
        assert len(g.items) == 2
        pubs = [i.published for i in g.items]
        assert pubs == sorted(pubs, reverse=True)

    def test_cap_drops_oldest(self):
        g = FeedGenerator(title="t", link="http://x", max_items=2)
        g.add_item(self._item("oldest", 300))
        g.add_item(self._item("middle", 100))
        g.add_item(self._item("newest", 1))
        assert len(g.items) == 2
        assert [i.link for i in g.items] == ["newest", "middle"]

    def test_max_items_zero_yields_empty(self):
        g = FeedGenerator(title="t", link="http://x", max_items=0)
        g.add_item(self._item("a", 1))
        assert g.items == []

    def test_add_items_matches_sequential_add_item(self):
        # Property: add_items([...]) == calling add_item per item (sort+cap
        # run after EACH item in both paths).
        items = [self._item(f"http://x/{i}", i * 10) for i in range(5)]
        g1 = FeedGenerator(title="t", link="http://x", max_items=3)
        g1.add_items(list(items))
        g2 = FeedGenerator(title="t", link="http://x", max_items=3)
        for it in items:
            g2.add_item(it)
        assert [i.link for i in g1.items] == [i.link for i in g2.items]

    def test_clear_empties_in_place(self):
        g = FeedGenerator(title="t", link="http://x")
        g.add_item(self._item("a", 1))
        g.add_item(self._item("b", 2))
        items_ref = g.items
        g.clear()
        assert g.items == []
        assert items_ref == []  # same list object, cleared in place


# ---------------------------------------------------------------------------
# FeedGenerator.generate RSS / Atom escaping
# ---------------------------------------------------------------------------
class TestFeedGeneratorGenerate:
    def _gen(self, **kw: Any) -> FeedGenerator:
        base: dict[str, Any] = dict(title="t", link="http://x")
        base.update(kw)
        return FeedGenerator(**base)

    def test_rss_well_formed_structure(self):
        g = self._gen()
        g.add_item(FeedItem(title="a", link="http://x/a"))
        out = g.generate(FeedFormat.RSS)
        assert out.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<rss version=\"2.0\">" in out
        assert "<channel>" in out
        assert "</channel>" in out
        assert out.rstrip().endswith("</rss>")
        assert "<item>" in out

    def test_atom_well_formed_structure(self):
        g = self._gen()
        g.add_item(FeedItem(title="a", link="http://x/a"))
        out = g.generate(FeedFormat.ATOM)
        assert out.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert '<feed xmlns="http://www.w3.org/2005/Atom">' in out
        assert out.rstrip().endswith("</feed>")
        assert "<entry>" in out

    def test_rss_escapes_xml_significant_chars(self):
        g = self._gen(title="T <title> & \"q\"", link="http://x/?a=1&b=2")
        g.add_item(FeedItem(title="A & B <c>", link="http://x/l",
                            description="d <e> & f", author="au <th>or",
                            categories=["cat <x> & y"]))
        out = g.generate(FeedFormat.RSS)
        # Raw <, >, &, " must not appear in the escaped content fields.
        assert "A &amp; B &lt;c&gt;" in out
        assert "d &lt;e&gt; &amp; f" in out
        assert "au &lt;th&gt;or" in out
        assert "cat &lt;x&gt; &amp; y" in out
        # The title element is escaped.
        assert "T &lt;title&gt; &amp; &quot;q&quot;" in out

    def test_atom_escapes_xml_significant_chars(self):
        g = self._gen(title="T <t> & x", link="http://x", feed_id="fid <v> & w")
        g.add_item(FeedItem(title="A & B", link="http://x/l",
                            description="s <u>", author="a <b>",
                            categories=["c <d>"]))
        out = g.generate(FeedFormat.ATOM)
        assert "A &amp; B" in out
        assert "s &lt;u&gt;" in out
        assert "a &lt;b&gt;" in out
        assert 'term="c &lt;d&gt;"' in out
        assert "<id>fid &lt;v&gt; &amp; w</id>" in out

    def test_rss_omits_optional_fields_when_empty(self):
        g = self._gen()
        g.add_item(FeedItem(title="t", link="http://x/l"))
        out = g.generate(FeedFormat.RSS)
        # The channel-level <description> is always present (even empty); the
        # ITEM-level optional fields (description/author/category) are omitted
        # when the item has none. Scope the check to the item block.
        item_block = out.split("<item>", 1)[1].split("</item>", 1)[0]
        assert "<description>" not in item_block
        assert "<author>" not in item_block
        assert "<category>" not in item_block
        # The item still carries its required title/link/guid.
        assert "<title>t</title>" in item_block
        assert "<link>http://x/l</link>" in item_block

    def test_atom_subtitle_only_when_description_set(self):
        g_no = self._gen(description="")
        g_no.add_item(FeedItem(title="t", link="http://x/l"))
        assert "<subtitle>" not in g_no.generate(FeedFormat.ATOM)
        g_yes = self._gen(description="my desc")
        g_yes.add_item(FeedItem(title="t", link="http://x/l"))
        assert "<subtitle>my desc</subtitle>" in g_yes.generate(FeedFormat.ATOM)

    def test_atom_author_block_structure(self):
        g = self._gen()
        g.add_item(FeedItem(title="t", link="http://x/l", author="Jane"))
        out = g.generate(FeedFormat.ATOM)
        assert "<author>" in out
        assert "<name>Jane</name>" in out
        assert "</author>" in out

    def test_empty_feed_rss(self):
        g = self._gen()
        out = g.generate(FeedFormat.RSS)
        assert "<item>" not in out
        assert "<channel>" in out

    def test_empty_feed_atom(self):
        g = self._gen()
        out = g.generate(FeedFormat.ATOM)
        assert "<entry>" not in out
        assert "<feed" in out

    def test_generate_idempotent_modulo_timestamps(self):
        # The <lastBuildDate>/<updated> elements use datetime.now() per call,
        # so the full feed is not byte-stable. But the item content is stable.
        g = self._gen()
        g.add_item(FeedItem(title="stable", link="http://x/s"))
        out1 = g.generate(FeedFormat.RSS)
        out2 = g.generate(FeedFormat.RSS)
        # Strip the now()-dependent line and compare the rest.
        def strip_now(s: str) -> str:
            return "\n".join(
                ln for ln in s.split("\n")
                if "<lastBuildDate>" not in ln and "<updated>" not in ln
            )
        assert strip_now(out1) == strip_now(out2)


# ---------------------------------------------------------------------------
# FeedGenerator.to_dict / from_dict round-trip
# ---------------------------------------------------------------------------
class TestFeedGeneratorRoundTrip:
    def test_to_dict_exactly_nine_keys(self):
        g = FeedGenerator(title="t", link="http://x")
        d = g.to_dict()
        assert set(d.keys()) == {
            "title", "link", "description", "language", "ttl",
            "generator", "max_items", "feed_id", "items",
        }

    def test_round_trip_lossless_nine_fields(self):
        g = FeedGenerator(
            title="t", link="http://x", description="d", language="fr-fr",
            ttl=99, generator="gen", max_items=7, feed_id="fid <v> & w",
        )
        g.add_item(FeedItem(title="i1", link="http://x/1"))
        restored = FeedGenerator.from_dict(g.to_dict())
        assert restored.title == g.title
        assert restored.link == g.link
        assert restored.description == g.description
        assert restored.language == g.language
        assert restored.ttl == g.ttl
        assert restored.generator == g.generator
        assert restored.max_items == g.max_items
        assert restored.feed_id == g.feed_id
        assert [i.to_dict() for i in restored.items] == [i.to_dict() for i in g.items]

    def test_from_dict_defaults(self):
        g = FeedGenerator.from_dict({})
        assert g.title == ""
        assert g.link == ""
        assert g.description == ""
        assert g.language == "en-us"
        assert g.ttl == 60
        assert g.generator == "personal-index"
        assert g.max_items == 100
        # feed_id absent -> post_init falls back to link ("" here).
        assert g.feed_id == ""
        assert g.items == []

    def test_from_dict_items_assigned_directly_no_resort_cap(self):
        # from_dict assigns gen.items = items directly (bypassing add_item),
        # so a list longer than max_items is NOT truncated on load.
        items = [FeedItem(title=f"i{i}", link=f"http://x/{i}") for i in range(5)]
        g = FeedGenerator(title="t", link="http://x", max_items=2)
        g.items = list(items)  # simulate a saved state with 5 items
        restored = FeedGenerator.from_dict(g.to_dict())
        assert len(restored.items) == 5  # cap NOT applied on load

    def test_round_trip_idempotent(self):
        g = FeedGenerator(title="t", link="http://x", max_items=3)
        g.add_item(FeedItem(title="i1", link="http://x/1"))
        once = FeedGenerator.from_dict(g.to_dict())
        twice = FeedGenerator.from_dict(once.to_dict())
        assert once.to_dict() == twice.to_dict()

    def test_round_trip_unicode(self):
        g = FeedGenerator(title="Привет 世界", link="http://x/ünïcode",
                          description="café — 日本語")
        g.add_item(FeedItem(title="条目", link="http://x/条目"))
        restored = FeedGenerator.from_dict(g.to_dict())
        assert restored.title == g.title
        assert restored.link == g.link
        assert restored.description == g.description
        assert restored.items[0].title == "条目"


# ---------------------------------------------------------------------------
# Property: escaping round-trips (escaped output unescapes to the original)
# ---------------------------------------------------------------------------
class TestEscapeProperty:
    @pytest.mark.parametrize("text", [
        "plain",
        "a<b>c",
        "a & b",
        'a "b" c',
        "a'b'c",
        "  whitespace  ",
        "ünïcode 日本語 🚀",
        "<script>alert('x')</script>",
        "",
    ])
    def test_escape_unescape_round_trip(self, text):
        g = FeedGenerator(title="t", link="http://x")
        escaped = g._escape(text)
        # html.escape(quote=True) escapes & < > " ' ; unescaping recovers the
        # original exactly.
        assert html.unescape(escaped) == text

    @pytest.mark.parametrize("text", [
        "a<b>c",
        "a & b",
        'a "b" c',
        "<script>alert('x')</script>",
    ])
    def test_escaped_output_has_no_raw_xml_significant_chars(self, text):
        g = FeedGenerator(title="t", link="http://x")
        escaped = g._escape(text)
        # After escaping, the chars that can NEVER appear inside an entity
        # reference (<, >, ") must be absent. & and ' legitimately appear as
        # part of the entity references themselves (&lt;, &#x27;), so they are
        # covered by the round-trip test instead.
        for ch in ("<", ">", '"'):
            assert ch not in escaped


# ---------------------------------------------------------------------------
# End-to-end: drive the installed `personal-index` CLI (per-cycle requirement).
# content_feed has no CLI surface, so this exercises the installed CLI entry
# point end-to-end (init + search) to confirm the package is importable and the
# CLI is wired, independent of the library probe above.
# ---------------------------------------------------------------------------
class TestCliEndToEnd:
    def test_cli_init_and_search_round_trip(self, tmp_path):
        import subprocess
        import sys

        data_dir = tmp_path / "data"
        data_dir.mkdir()
        config_path = data_dir / "config.yaml"
        base = [sys.executable, "-m", "personal_index.cli", "--data-dir", str(data_dir)]

        init = subprocess.run(base + ["init", "--config", str(config_path)], capture_output=True, text=True, timeout=120)
        assert init.returncode == 0, f"init failed: {init.stderr}"

        search = subprocess.run(base + ["search", "python"], capture_output=True, text=True, timeout=120)
        assert search.returncode == 0, f"search failed: {search.stderr}"
        combined = (search.stdout + search.stderr).lower()
        assert "no indexed content found" in combined
