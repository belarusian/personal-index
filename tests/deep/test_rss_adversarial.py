"""Adversarial deep tests for personal_index.rss (RSSParser / Feed / FeedEntry).

Probes the RSS/Atom parser contract: guard inputs (None/empty/whitespace/
unicode/malformed XML), round-trips (to_dict), idempotence, property checks
(entry_count, get_recent_entries), and the negative-slice "top N" contract
(get_recent_entries(count) uses self.entries[:count] - the same defect class
as QA-1/QA-2). One end-to-end run through the installed CLI.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from personal_index.rss import Feed, FeedEntry, RSSParser

RSS_SAMPLE = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>My Feed</title>
    <link>https://example.com</link>
    <description>A test feed</description>
    <item>
      <title>First</title>
      <link>https://example.com/1</link>
      <description>First desc</description>
      <category>tech</category>
      <category>news</category>
    </item>
    <item>
      <title>Second</title>
      <link>https://example.com/2</link>
    </item>
  </channel>
</rss>
"""

ATOM_SAMPLE = """<?xml version="1.0" encoding="utf-8"?>
<feed xmlns="http://www.w3.org/2005/Atom">
  <title>Atom Feed</title>
  <link rel="alternate" href="https://example.com/atom"/>
  <subtitle>An atom feed</subtitle>
  <entry>
    <title>Entry A</title>
    <link rel="alternate" href="https://example.com/a"/>
    <summary>Summary A</summary>
    <category term="atom-tag"/>
  </entry>
</feed>
"""


@pytest.fixture
def parser() -> RSSParser:
    return RSSParser()


# ---------------------------------------------------------------------------
# Guard inputs
# ---------------------------------------------------------------------------

def test_parse_empty_string_returns_empty_feed(parser):
    feed = parser.parse("")
    assert feed.entry_count == 0
    assert feed.title == ""
    assert feed.feed_url == ""


def test_parse_whitespace_only_returns_empty_feed(parser):
    feed = parser.parse("   \n\t  ")
    assert feed.entry_count == 0


def test_parse_malformed_xml_returns_empty_feed(parser):
    feed = parser.parse("<rss><channel><item><title>unclosed")
    assert feed.entry_count == 0


def test_parse_non_feed_xml_returns_empty_feed(parser):
    feed = parser.parse("<html><body><p>hi</p></body></html>")
    assert feed.entry_count == 0


def test_parse_none_like_empty_is_guarded(parser):
    # parse() takes a str; empty string is the guard path.
    feed = parser.parse("")
    assert isinstance(feed, Feed)


def test_parse_rss_roundtrip(parser):
    feed = parser.parse(RSS_SAMPLE, feed_url="https://example.com/feed")
    assert feed.title == "My Feed"
    assert feed.link == "https://example.com"
    assert feed.description == "A test feed"
    assert feed.entry_count == 2
    assert feed.feed_url == "https://example.com/feed"
    first = feed.entries[0]
    assert first.title == "First"
    assert first.link == "https://example.com/1"
    assert first.summary == "First desc"
    assert first.categories == ["tech", "news"]


def test_parse_atom_roundtrip(parser):
    feed = parser.parse(ATOM_SAMPLE, feed_url="https://example.com/atom")
    assert feed.title == "Atom Feed"
    assert feed.link == "https://example.com/atom"
    assert feed.description == "An atom feed"
    assert feed.entry_count == 1
    entry = feed.entries[0]
    assert entry.title == "Entry A"
    assert entry.link == "https://example.com/a"
    assert entry.summary == "Summary A"
    assert entry.categories == ["atom-tag"]


def test_parse_unicode_content(parser):
    xml = (
        '<rss version="2.0"><channel>'
        '<title>Ünïcödé 日本語</title>'
        '<item><title>Émoji 🎉</title><link>https://x/1</link></item>'
        '</channel></rss>'
    )
    feed = parser.parse(xml)
    assert feed.title == "Ünïcödé 日本語"
    assert feed.entries[0].title == "Émoji 🎉"


def test_parse_item_missing_fields_defaults(parser):
    xml = '<rss version="2.0"><channel><item></item></channel></rss>'
    feed = parser.parse(xml)
    assert feed.entry_count == 1
    e = feed.entries[0]
    assert e.title == ""
    assert e.link == ""
    assert e.summary == ""
    assert e.categories == []
    assert e.published is None


def test_parse_empty_channel(parser):
    xml = '<rss version="2.0"><channel></channel></rss>'
    feed = parser.parse(xml)
    assert feed.entry_count == 0
    assert feed.title == ""


# ---------------------------------------------------------------------------
# is_feed
# ---------------------------------------------------------------------------

def test_is_feed_true_for_rss(parser):
    assert RSSParser.is_feed("<rss version='2.0'><channel></channel></rss>") is True


def test_is_feed_true_for_atom(parser):
    assert RSSParser.is_feed('<feed xmlns="http://www.w3.org/2005/Atom"></feed>') is True


def test_is_feed_false_for_empty(parser):
    assert RSSParser.is_feed("") is False


def test_is_feed_false_for_whitespace(parser):
    assert RSSParser.is_feed("   \n\t") is False


def test_is_feed_false_for_plain_html(parser):
    assert RSSParser.is_feed("<html><body>hi</body></html>") is False


def test_is_feed_case_insensitive(parser):
    assert RSSParser.is_feed("<RSS version='2.0'><channel></channel></RSS>") is True


# ---------------------------------------------------------------------------
# to_dict round-trip
# ---------------------------------------------------------------------------

def test_feed_entry_to_dict_roundtrip():
    e = FeedEntry(
        title="t", link="l", summary="s", content="c",
        author="a", published="p", updated="u",
        categories=["x", "y"], guid="g",
    )
    d = e.to_dict()
    assert d == {
        "title": "t", "link": "l", "summary": "s", "content": "c",
        "author": "a", "published": "p", "updated": "u",
        "categories": ["x", "y"], "guid": "g",
    }


def test_feed_entry_to_dict_defaults():
    e = FeedEntry()
    d = e.to_dict()
    assert d["title"] == ""
    assert d["published"] is None
    assert d["categories"] == []


# ---------------------------------------------------------------------------
# get_recent_entries contract (top-N / limit)
# ---------------------------------------------------------------------------

def _feed_with(n: int) -> Feed:
    return Feed(entries=[FeedEntry(title=str(i)) for i in range(n)])


def test_get_recent_entries_zero_returns_empty():
    assert _feed_with(5).get_recent_entries(0) == []


def test_get_recent_entries_small_count():
    got = _feed_with(5).get_recent_entries(2)
    assert [e.title for e in got] == ["0", "1"]


def test_get_recent_entries_out_of_range_returns_all():
    got = _feed_with(3).get_recent_entries(99)
    assert [e.title for e in got] == ["0", "1", "2"]


def test_get_recent_entries_default():
    got = _feed_with(3).get_recent_entries()
    assert [e.title for e in got] == ["0", "1", "2"]


def test_get_recent_entries_empty_feed():
    assert _feed_with(0).get_recent_entries(5) == []


def test_get_recent_entries_negative_count_returns_empty():
    feed = _feed_with(5)
    got = feed.get_recent_entries(-1)
    assert got == [], f"expected [] for negative count, got {[e.title for e in got]}"


def test_get_recent_entries_is_idempotent():
    feed = _feed_with(5)
    first = feed.get_recent_entries(3)
    second = feed.get_recent_entries(3)
    assert [e.title for e in first] == [e.title for e in second]
    # the source feed is not mutated by slicing
    assert feed.entry_count == 5


# ---------------------------------------------------------------------------
# property: entry_count
# ---------------------------------------------------------------------------

def test_entry_count_property():
    assert _feed_with(0).entry_count == 0
    assert _feed_with(7).entry_count == 7


# ---------------------------------------------------------------------------
# end-to-end CLI run
# ---------------------------------------------------------------------------

def test_cli_end_to_end_init_import_search():
    with tempfile.TemporaryDirectory() as tmp:
        data_dir = Path(tmp)
        # init
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "init", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        # import a local file
        f = data_dir / "page.html"
        f.write_text("<html><body><h1>python programming</h1><p>python is great</p></body></html>")
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "import", str(f), "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        # search
        r = subprocess.run(
            [sys.executable, "-m", "personal_index", "search", "python", "--data-dir", str(data_dir)],
            capture_output=True, text=True,
        )
        assert r.returncode == 0, r.stderr
        assert "python" in (r.stdout + r.stderr).lower()
