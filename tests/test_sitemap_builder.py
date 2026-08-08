"""Tests for the sitemap builder module."""

import pytest
from datetime import datetime, timezone
from personal_index.sitemap_builder import SitemapBuilder, SitemapEntry


class TestSitemapEntry:
    def test_default_values(self):
        entry = SitemapEntry("http://example.com")
        assert entry.url == "http://example.com"
        assert entry.change_frequency == "monthly"
        assert entry.priority == 0.5

    def test_custom_values(self):
        dt = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
        entry = SitemapEntry("http://example.com/page", dt, "daily", 0.8)
        assert entry.last_modified == dt
        assert entry.change_frequency == "daily"
        assert entry.priority == 0.8

    def test_priority_clamped(self):
        entry = SitemapEntry("http://example.com", priority=1.5)
        assert entry.priority == 1.0
        entry2 = SitemapEntry("http://example.com", priority=-0.5)
        assert entry2.priority == 0.0

    def test_to_element(self):
        entry = SitemapEntry("http://example.com/page", change_frequency="weekly", priority=0.7)
        elem = entry.to_element()
        assert elem.tag == "url"
        loc = elem.find("loc")
        assert loc is not None
        assert loc.text == "http://example.com/page"


class TestSitemapBuilder:
    def test_empty_sitemap(self):
        builder = SitemapBuilder()
        xml = builder.build()
        assert b"<urlset" in xml
        assert b"<?xml" in xml

    def test_single_entry(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com/page1")
        xml = builder.build().decode("utf-8")
        assert "http://example.com/page1" in xml
        assert "<loc>" in xml
        assert "<lastmod>" in xml
        assert "<changefreq>" in xml
        assert "<priority>" in xml

    def test_multiple_entries(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com/a")
        builder.add_entry("http://example.com/b")
        builder.add_entry("http://example.com/c")
        xml = builder.build().decode("utf-8")
        assert xml.count("<loc>") == 3

    def test_add_entries_batch(self):
        builder = SitemapBuilder()
        entries = [
            SitemapEntry("http://example.com/1"),
            SitemapEntry("http://example.com/2"),
        ]
        builder.add_entries(entries)
        assert builder.url_count == 2

    def test_sitemap_index(self):
        builder = SitemapBuilder()
        xml = builder.build_sitemap_index([
            "http://example.com/sitemap1.xml",
            "http://example.com/sitemap2.xml",
        ])
        assert b"<sitemapindex" in xml
        assert b"sitemap1.xml" in xml
        assert b"sitemap2.xml" in xml

    def test_split_into_chunks(self):
        builder = SitemapBuilder()
        for i in range(15):
            builder.add_entry(f"http://example.com/page{i}")
        chunks = builder.split_into_chunks(chunk_size=5)
        assert len(chunks) == 3
        assert len(chunks[0]) == 5
        assert len(chunks[1]) == 5
        assert len(chunks[2]) == 5

    def test_clear(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com/page")
        assert builder.url_count == 1
        builder.clear()
        assert builder.url_count == 0

    def test_url_count(self):
        builder = SitemapBuilder()
        assert builder.url_count == 0
        builder.add_entry("http://example.com/1")
        builder.add_entry("http://example.com/2")
        assert builder.url_count == 2

    def test_xml_declaration(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com")
        xml = builder.build().decode("utf-8")
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')

    def test_change_frequency_in_output(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com", change_frequency="daily")
        xml = builder.build().decode("utf-8")
        assert "<changefreq>daily</changefreq>" in xml

    def test_priority_in_output(self):
        builder = SitemapBuilder()
        builder.add_entry("http://example.com", priority=0.9)
        xml = builder.build().decode("utf-8")
        assert "<priority>0.9</priority>" in xml

    def test_large_sitemap(self):
        builder = SitemapBuilder()
        for i in range(1000):
            builder.add_entry(f"http://example.com/page{i}")
        xml = builder.build().decode("utf-8")
        assert xml.count("<loc>") == 1000
