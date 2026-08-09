"""Tests for content_sitemap module - generate sitemap of saved content."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from personal_index.content_sitemap import (
    SitemapGenerator,
    SitemapEntry,
    SitemapDocument,
    SitemapIndexEntry,
    SitemapFormat,
)


class TestSitemapEntry:
    """Tests for SitemapEntry model."""

    def test_create_entry(self):
        entry = SitemapEntry(url="https://example.com/page")
        assert entry.url == "https://example.com/page"
        assert entry.priority == 0.5
        assert entry.changefreq == "monthly"

    def test_entry_with_custom_priority(self):
        entry = SitemapEntry(
            url="https://example.com",
            priority=1.0,
            changefreq="daily",
        )
        assert entry.priority == 1.0
        assert entry.changefreq == "daily"

    def test_entry_with_lastmod(self):
        now = datetime.now(timezone.utc)
        entry = SitemapEntry(url="https://example.com", lastmod=now)
        assert entry.lastmod == now

    def test_entry_to_xml(self):
        entry = SitemapEntry(
            url="https://example.com/page",
            priority=0.8,
            changefreq="weekly",
        )
        xml = entry.to_xml()
        assert "<loc>https://example.com/page</loc>" in xml
        assert "<priority>0.8</priority>" in xml
        assert "<changefreq>weekly</changefreq>" in xml

    def test_entry_to_xml_with_lastmod(self):
        entry = SitemapEntry(
            url="https://example.com/page",
            lastmod=datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc),
        )
        xml = entry.to_xml()
        assert "<lastmod>2024-01-15</lastmod>" in xml


class TestSitemapDocument:
    """Tests for SitemapDocument model."""

    def test_create_document(self):
        doc = SitemapDocument()
        assert len(doc.entries) == 0

    def test_add_entry(self):
        doc = SitemapDocument()
        doc.add_entry(SitemapEntry(url="https://example.com/page"))
        assert len(doc.entries) == 1

    def test_to_xml(self):
        doc = SitemapDocument()
        doc.add_entry(SitemapEntry(url="https://example.com/page"))
        xml = doc.to_xml()
        assert '<?xml version="1.0" encoding="UTF-8"?>' in xml
        assert "<urlset" in xml
        assert "</urlset>" in xml
        assert "<loc>https://example.com/page</loc>" in xml

    def test_to_xml_empty(self):
        doc = SitemapDocument()
        xml = doc.to_xml()
        assert "<urlset" in xml
        assert "</urlset>" in xml

    def test_entry_count(self):
        doc = SitemapDocument()
        doc.add_entry(SitemapEntry(url="https://example.com/1"))
        doc.add_entry(SitemapEntry(url="https://example.com/2"))
        assert doc.entry_count == 2


class TestSitemapIndexEntry:
    """Tests for SitemapIndexEntry model."""

    def test_create_index_entry(self):
        entry = SitemapIndexEntry(
            sitemap_url="https://example.com/sitemap-1.xml",
        )
        assert entry.sitemap_url == "https://example.com/sitemap-1.xml"

    def test_index_entry_to_xml(self):
        entry = SitemapIndexEntry(
            sitemap_url="https://example.com/sitemap-1.xml",
            lastmod=datetime(2024, 1, 15, tzinfo=timezone.utc),
        )
        xml = entry.to_xml()
        assert "<sitemap>" in xml
        assert "<loc>https://example.com/sitemap-1.xml</loc>" in xml


class TestSitemapFormat:
    """Tests for SitemapFormat enum."""

    def test_format_values(self):
        assert SitemapFormat.XML.value == "xml"
        assert SitemapFormat.TEXT.value == "text"
        assert SitemapFormat.JSON.value == "json"


class TestSitemapGenerator:
    """Tests for SitemapGenerator class."""

    def test_init(self):
        gen = SitemapGenerator()
        assert gen.max_entries_per_sitemap == 50000

    def test_add_url(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page", title="Test Page")
        assert len(gen._entries) == 1

    def test_add_url_with_priority(self):
        gen = SitemapGenerator()
        gen.add_url(
            "https://example.com/page",
            priority=0.9,
            changefreq="daily",
        )
        entry = gen._entries[0]
        assert entry.priority == 0.9
        assert entry.changefreq == "daily"

    def test_add_duplicate_url(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page")
        gen.add_url("https://example.com/page")
        assert len(gen._entries) == 1

    def test_generate_xml(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page")
        xml = gen.generate(SitemapFormat.XML)
        assert "<?xml" in xml
        assert "<urlset" in xml
        assert "<loc>https://example.com/page</loc>" in xml

    def test_generate_text(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page1")
        gen.add_url("https://example.com/page2")
        text = gen.generate(SitemapFormat.TEXT)
        assert "https://example.com/page1" in text
        assert "https://example.com/page2" in text

    def test_generate_json(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page", title="Test")
        import json
        data = gen.generate(SitemapFormat.JSON)
        parsed = json.loads(data)
        assert len(parsed["urls"]) == 1
        assert parsed["urls"][0]["loc"] == "https://example.com/page"

    def test_generate_empty(self):
        gen = SitemapGenerator()
        xml = gen.generate(SitemapFormat.XML)
        assert "<urlset" in xml

    def test_bulk_add_urls(self):
        gen = SitemapGenerator()
        urls = [
            ("https://example.com/1", "Page 1"),
            ("https://example.com/2", "Page 2"),
            ("https://example.com/3", "Page 3"),
        ]
        gen.bulk_add_urls(urls)
        assert len(gen._entries) == 3

    def test_clear_entries(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page")
        gen.clear()
        assert len(gen._entries) == 0

    def test_entry_count(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/1")
        gen.add_url("https://example.com/2")
        assert gen.entry_count == 2

    def test_generate_index(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page")
        index_xml = gen.generate_index(
            base_url="https://example.com",
            sitemap_prefix="sitemap",
        )
        assert "<sitemapindex" in index_xml
        assert "<sitemap>" in index_xml

    def test_priority_clamping(self):
        gen = SitemapGenerator()
        gen.add_url("https://example.com/page", priority=1.5)
        assert gen._entries[0].priority == 1.0
        gen.add_url("https://example.com/page2", priority=-0.5)
        assert gen._entries[1].priority == 0.0

    def test_lastmod_formatting(self):
        gen = SitemapGenerator()
        now = datetime.now(timezone.utc)
        gen.add_url("https://example.com/page", lastmod=now)
        xml = gen.generate(SitemapFormat.XML)
        assert "<lastmod>" in xml
