"""Tests for RSS feed reader module."""

from __future__ import annotations

import pytest

from personal_index.rss import (
    Feed,
    FeedEntry,
    RSSParser,
)


class TestFeedEntry:
    """Tests for FeedEntry dataclass."""

    def test_default_values(self):
        entry = FeedEntry()
        assert entry.title == ""
        assert entry.link == ""
        assert entry.categories == []
        assert entry.guid == ""

    def test_with_values(self):
        entry = FeedEntry(
            title="Test Post",
            link="http://example.com/post",
            summary="A summary",
            author="Alice",
            categories=["tech", "python"],
        )
        assert entry.title == "Test Post"
        assert entry.author == "Alice"
        assert entry.categories == ["tech", "python"]

    def test_to_dict(self):
        entry = FeedEntry(title="Test", link="http://x.com", author="Bob")
        d = entry.to_dict()
        assert d["title"] == "Test"
        assert d["link"] == "http://x.com"
        assert d["author"] == "Bob"


class TestFeed:
    """Tests for Feed dataclass."""

    def test_default_values(self):
        feed = Feed()
        assert feed.title == ""
        assert feed.entry_count == 0

    def test_entry_count(self):
        feed = Feed(entries=[FeedEntry(title="A"), FeedEntry(title="B")])
        assert feed.entry_count == 2

    def test_get_recent_entries(self):
        entries = [FeedEntry(title=f"Post {i}") for i in range(20)]
        feed = Feed(entries=entries)
        recent = feed.get_recent_entries(5)
        assert len(recent) == 5
        assert recent[0].title == "Post 0"

    def test_get_recent_less_than_available(self):
        entries = [FeedEntry(title=f"Post {i}") for i in range(3)]
        feed = Feed(entries=entries)
        recent = feed.get_recent_entries(10)
        assert len(recent) == 3


class TestRSSParser:
    """Tests for RSSParser class."""

    def setup_method(self):
        self.parser = RSSParser()

    def test_parse_empty(self):
        feed = self.parser.parse("")
        assert feed.entry_count == 0

    def test_parse_invalid_xml(self):
        feed = self.parser.parse("not xml")
        assert feed.entry_count == 0

    def test_parse_rss_basic(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <rss version="2.0">
            <channel>
                <title>Test Blog</title>
                <link>http://example.com</link>
                <description>A test blog</description>
                <item>
                    <title>Post One</title>
                    <link>http://example.com/post1</link>
                    <description>First post summary</description>
                    <pubDate>Mon, 01 Jan 2024 00:00:00 GMT</pubDate>
                    <guid>post-1</guid>
                </item>
                <item>
                    <title>Post Two</title>
                    <link>http://example.com/post2</link>
                    <description>Second post summary</description>
                </item>
            </channel>
        </rss>"""
        feed = self.parser.parse(xml, feed_url="http://example.com/feed.xml")
        assert feed.title == "Test Blog"
        assert feed.link == "http://example.com"
        assert feed.description == "A test blog"
        assert feed.entry_count == 2
        assert feed.entries[0].title == "Post One"
        assert feed.entries[0].published == "Mon, 01 Jan 2024 00:00:00 GMT"
        assert feed.entries[0].guid == "post-1"
        assert feed.entries[1].guid == "http://example.com/post2"

    def test_parse_rss_with_categories(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Blog</title>
                <link>http://example.com</link>
                <description>Blog</description>
                <item>
                    <title>Post</title>
                    <link>http://example.com/p</link>
                    <description>Desc</description>
                    <category>tech</category>
                    <category>python</category>
                </item>
            </channel>
        </rss>"""
        feed = self.parser.parse(xml)
        assert feed.entries[0].categories == ["tech", "python"]

    def test_parse_atom_basic(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Atom Blog</title>
            <link href="http://example.com" rel="alternate"/>
            <subtitle>An atom blog</subtitle>
            <author><name>Alice</name></author>
            <entry>
                <title>Atom Post</title>
                <link href="http://example.com/atom-post" rel="alternate"/>
                <summary>Atom summary</summary>
                <published>2024-01-01T00:00:00Z</published>
                <updated>2024-01-02T00:00:00Z</updated>
                <id>urn:uuid:1234</id>
            </entry>
        </feed>"""
        feed = self.parser.parse(xml)
        assert feed.title == "Atom Blog"
        assert feed.link == "http://example.com"
        assert feed.description == "An atom blog"
        assert feed.author == "Alice"
        assert feed.entry_count == 1
        assert feed.entries[0].title == "Atom Post"
        assert feed.entries[0].published == "2024-01-01T00:00:00Z"
        assert feed.entries[0].updated == "2024-01-02T00:00:00Z"
        assert feed.entries[0].guid == "urn:uuid:1234"

    def test_parse_atom_with_content(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Blog</title>
            <link href="http://example.com" rel="alternate"/>
            <entry>
                <title>Post</title>
                <link href="http://example.com/p" rel="alternate"/>
                <content>Full content here</content>
            </entry>
        </feed>"""
        feed = self.parser.parse(xml)
        assert feed.entries[0].content == "Full content here"

    def test_parse_rss_with_author(self):
        xml = """<?xml version="1.0"?>
        <rss version="2.0">
            <channel>
                <title>Blog</title>
                <link>http://example.com</link>
                <description>Blog</description>
                <item>
                    <title>Post</title>
                    <link>http://example.com/p</link>
                    <description>Desc</description>
                    <author>alice@example.com</author>
                </item>
            </channel>
        </rss>"""
        feed = self.parser.parse(xml)
        assert feed.entries[0].author == "alice@example.com"

    def test_feed_url_preserved(self):
        feed = self.parser.parse("", feed_url="http://example.com/feed.xml")
        assert feed.feed_url == "http://example.com/feed.xml"

    def test_is_feed_rss(self):
        assert self.parser.is_feed('<rss version="2.0"><channel></channel></rss>') is True

    def test_is_feed_atom(self):
        assert self.parser.is_feed('<feed xmlns="http://www.w3.org/2005/Atom"></feed>') is True

    def test_is_feed_not_feed(self):
        assert self.parser.is_feed('<html><body>Hello</body></html>') is False

    def test_is_feed_empty(self):
        assert self.parser.is_feed("") is False

    def test_parse_rss_no_channel(self):
        xml = '<rss version="2.0"></rss>'
        feed = self.parser.parse(xml)
        assert feed.entry_count == 0

    def test_parse_atom_with_categories(self):
        xml = """<?xml version="1.0"?>
        <feed xmlns="http://www.w3.org/2005/Atom">
            <title>Blog</title>
            <link href="http://example.com" rel="alternate"/>
            <entry>
                <title>Post</title>
                <link href="http://example.com/p" rel="alternate"/>
                <category term="tech"/>
                <category term="news"/>
            </entry>
        </feed>"""
        feed = self.parser.parse(xml)
        assert feed.entries[0].categories == ["tech", "news"]
