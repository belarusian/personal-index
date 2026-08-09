"""Tests for content_feed module - RSS/Atom feed of recent saves."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta
from personal_index.content_feed import (
    FeedItem,
    FeedGenerator,
    FeedFormat,
)


class TestFeedItem:
    """Tests for FeedItem dataclass."""

    def test_create_feed_item_basic(self):
        item = FeedItem(title="Test Article", link="http://example.com")
        assert item.title == "Test Article"
        assert item.link == "http://example.com"
        assert item.id == "http://example.com"

    def test_create_feed_item_with_all_fields(self):
        item = FeedItem(
            title="Test",
            link="http://example.com",
            description="A description",
            author="alice",
            categories=["tech", "python"],
            published=datetime(2024, 1, 1, tzinfo=timezone.utc),
            updated=datetime(2024, 1, 2, tzinfo=timezone.utc),
        )
        assert item.description == "A description"
        assert item.author == "alice"
        assert item.categories == ["tech", "python"]

    def test_feed_item_default_published(self):
        item = FeedItem(title="Test", link="http://example.com")
        assert item.published is not None

    def test_feed_item_to_dict(self):
        item = FeedItem(title="T", link="http://example.com", description="D")
        d = item.to_dict()
        assert d["title"] == "T"
        assert d["link"] == "http://example.com"

    def test_feed_item_from_dict(self):
        data = {
            "title": "Test",
            "link": "http://example.com",
            "description": "Desc",
            "author": "alice",
            "categories": ["tech"],
        }
        item = FeedItem.from_dict(data)
        assert item.title == "Test"
        assert item.author == "alice"

    def test_feed_item_serialization_roundtrip(self):
        item = FeedItem(
            title="Round",
            link="http://example.com",
            description="Trip",
            author="test",
            categories=["a", "b"],
        )
        d = item.to_dict()
        item2 = FeedItem.from_dict(d)
        assert item2.title == item.title
        assert item2.link == item.link
        assert item2.author == item.author
        assert item2.categories == item.categories


class TestFeedFormat:
    """Tests for FeedFormat enum."""

    def test_rss_format(self):
        assert FeedFormat.RSS.value == "rss"

    def test_atom_format(self):
        assert FeedFormat.ATOM.value == "atom"

    def test_from_string(self):
        assert FeedFormat("rss") == FeedFormat.RSS
        assert FeedFormat("atom") == FeedFormat.ATOM


class TestFeedGenerator:
    """Tests for FeedGenerator."""

    def setup_method(self):
        self.generator = FeedGenerator(
            title="My Feed",
            link="http://example.com/feed",
            description="A test feed",
        )

    def test_generator_has_title(self):
        assert self.generator.title == "My Feed"

    def test_generator_has_description(self):
        assert self.generator.description == "A test feed"

    def test_add_item(self):
        item = FeedItem(title="Article 1", link="http://example.com/1")
        self.generator.add_item(item)
        assert len(self.generator.items) == 1

    def test_add_multiple_items(self):
        for i in range(5):
            self.generator.add_item(
                FeedItem(title=f"Article {i}", link=f"http://example.com/{i}")
            )
        assert len(self.generator.items) == 5

    def test_add_item_with_max_items(self):
        gen = FeedGenerator(
            title="Test", link="http://example.com", max_items=3,
        )
        for i in range(5):
            gen.add_item(
                FeedItem(title=f"Article {i}", link=f"http://example.com/{i}")
            )
        assert len(gen.items) == 3

    def test_add_items_from_list(self):
        items = [
            FeedItem(title=f"A{i}", link=f"http://example.com/{i}")
            for i in range(3)
        ]
        self.generator.add_items(items)
        assert len(self.generator.items) == 3

    def test_generate_rss(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<rss" in rss
        assert "<channel>" in rss
        assert "Article 1" in rss
        assert "My Feed" in rss

    def test_generate_rss_has_xml_declaration(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<?xml" in rss

    def test_generate_rss_has_channel_title(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<title>My Feed</title>" in rss

    def test_generate_rss_has_item_title(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<title>Article 1</title>" in rss

    def test_generate_rss_has_item_link(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<link>http://example.com/1</link>" in rss

    def test_generate_rss_has_item_description(self):
        self.generator.add_item(
            FeedItem(
                title="Article 1",
                link="http://example.com/1",
                description="A description",
            )
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "A description" in rss

    def test_generate_rss_has_item_author(self):
        self.generator.add_item(
            FeedItem(
                title="Article 1",
                link="http://example.com/1",
                author="alice",
            )
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "alice" in rss

    def test_generate_rss_has_item_categories(self):
        self.generator.add_item(
            FeedItem(
                title="Article 1",
                link="http://example.com/1",
                categories=["tech", "python"],
            )
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "tech" in rss
        assert "python" in rss

    def test_generate_rss_has_item_pubdate(self):
        pub = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1", published=pub)
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "Mon, 15 Jan 2024" in rss

    def test_generate_rss_escapes_html(self):
        self.generator.add_item(
            FeedItem(
                title="<script>alert('xss')</script>",
                link="http://example.com/1",
            )
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<script>" not in rss
        assert "&lt;script&gt;" in rss

    def test_generate_rss_empty_feed(self):
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<rss" in rss
        assert "<channel>" in rss
        assert "<item>" not in rss

    def test_generate_atom(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<feed" in atom
        assert "<title>My Feed</title>" in atom
        assert "Article 1" in atom

    def test_generate_atom_has_xml_declaration(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<?xml" in atom

    def test_generate_atom_has_entry(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<entry>" in atom
        assert "</entry>" in atom

    def test_generate_atom_has_id(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<id>" in atom

    def test_generate_atom_has_updated(self):
        self.generator.add_item(
            FeedItem(title="Article 1", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<updated>" in atom

    def test_generate_atom_has_author(self):
        self.generator.add_item(
            FeedItem(
                title="Article 1",
                link="http://example.com/1",
                author="alice",
            )
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "alice" in atom

    def test_generate_atom_has_categories(self):
        self.generator.add_item(
            FeedItem(
                title="Article 1",
                link="http://example.com/1",
                categories=["tech"],
            )
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "tech" in atom

    def test_generate_atom_escapes_html(self):
        self.generator.add_item(
            FeedItem(
                title="<b>Bold</b>",
                link="http://example.com/1",
            )
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<b>" not in atom

    def test_generate_atom_empty_feed(self):
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<feed" in atom
        assert "<entry>" not in atom

    def test_generate_with_language(self):
        gen = FeedGenerator(
            title="Test", link="http://example.com", language="en",
        )
        gen.add_item(FeedItem(title="A", link="http://example.com/1"))
        rss = gen.generate(FeedFormat.RSS)
        assert "language" in rss or "lang" in rss

    def test_generate_with_ttl(self):
        gen = FeedGenerator(
            title="Test", link="http://example.com", ttl=60,
        )
        gen.add_item(FeedItem(title="A", link="http://example.com/1"))
        rss = gen.generate(FeedFormat.RSS)
        assert "ttl" in rss or "TTL" in rss

    def test_generate_with_generator_name(self):
        gen = FeedGenerator(
            title="Test", link="http://example.com", generator="personal-index",
        )
        gen.add_item(FeedItem(title="A", link="http://example.com/1"))
        rss = gen.generate(FeedFormat.RSS)
        assert "personal-index" in rss

    def test_items_sorted_by_published(self):
        now = datetime.now(timezone.utc)
        self.generator.add_item(
            FeedItem(title="Old", link="http://example.com/1", published=now - timedelta(days=1))
        )
        self.generator.add_item(
            FeedItem(title="New", link="http://example.com/2", published=now)
        )
        rss = self.generator.generate(FeedFormat.RSS)
        new_pos = rss.find("New")
        old_pos = rss.find("Old")
        assert new_pos < old_pos

    def test_clear_items(self):
        self.generator.add_item(
            FeedItem(title="A", link="http://example.com/1")
        )
        self.generator.clear()
        assert len(self.generator.items) == 0

    def test_get_feed_type(self):
        assert self.generator.get_feed_type(FeedFormat.RSS) == "application/rss+xml"
        assert self.generator.get_feed_type(FeedFormat.ATOM) == "application/atom+xml"

    def test_to_dict(self):
        self.generator.add_item(
            FeedItem(title="A", link="http://example.com/1")
        )
        d = self.generator.to_dict()
        assert d["title"] == "My Feed"
        assert len(d["items"]) == 1

    def test_from_dict(self):
        data = {
            "title": "Test",
            "link": "http://example.com",
            "description": "Desc",
            "items": [
                {"title": "A", "link": "http://example.com/1"},
            ],
        }
        gen = FeedGenerator.from_dict(data)
        assert gen.title == "Test"
        assert len(gen.items) == 1

    def test_serialization_roundtrip(self):
        self.generator.add_item(
            FeedItem(title="A", link="http://example.com/1", author="alice")
        )
        d = self.generator.to_dict()
        gen2 = FeedGenerator.from_dict(d)
        assert gen2.title == self.generator.title
        assert len(gen2.items) == 1
        assert gen2.items[0].author == "alice"

    def test_generate_rss_has_last_build_date(self):
        self.generator.add_item(
            FeedItem(title="A", link="http://example.com/1")
        )
        rss = self.generator.generate(FeedFormat.RSS)
        assert "<lastBuildDate>" in rss

    def test_generate_atom_has_feed_id(self):
        self.generator.add_item(
            FeedItem(title="A", link="http://example.com/1")
        )
        atom = self.generator.generate(FeedFormat.ATOM)
        assert "<id>http://example.com/feed</id>" in atom
