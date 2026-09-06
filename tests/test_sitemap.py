"""Tests for sitemap parser."""

from __future__ import annotations

from personal_index.sitemap import (
    SitemapEntry,
    SitemapParser,
)


class TestSitemapEntry:
    """Tests for SitemapEntry dataclass."""

    def test_valid_entry(self):
        entry = SitemapEntry(loc="http://example.com")
        assert entry.is_valid() is True

    def test_invalid_entry_no_scheme(self):
        entry = SitemapEntry(loc="example.com")
        assert entry.is_valid() is False

    def test_invalid_entry_empty(self):
        entry = SitemapEntry(loc="")
        assert entry.is_valid() is False

    def test_https_entry(self):
        entry = SitemapEntry(loc="https://example.com")
        assert entry.is_valid() is True

    def test_default_values(self):
        entry = SitemapEntry(loc="http://example.com")
        assert entry.changefreq == "monthly"
        assert entry.priority == 0.5


class TestSitemapParser:
    """Tests for SitemapParser class."""

    def setup_method(self):
        self.parser = SitemapParser()

    def test_parse_empty(self):
        sitemap = self.parser.parse("")
        assert sitemap.url_count == 0

    def test_parse_invalid_xml(self):
        sitemap = self.parser.parse("not xml at all")
        assert sitemap.url_count == 0

    def test_parse_basic_sitemap(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url>
                <loc>http://example.com/page1</loc>
                <lastmod>2024-01-01</lastmod>
                <changefreq>daily</changefreq>
                <priority>0.8</priority>
            </url>
            <url>
                <loc>http://example.com/page2</loc>
            </url>
        </urlset>"""
        sitemap = self.parser.parse(xml)
        assert sitemap.url_count == 2
        assert sitemap.entries[0].loc == "http://example.com/page1"
        assert sitemap.entries[0].lastmod == "2024-01-01"
        assert sitemap.entries[0].changefreq == "daily"
        assert sitemap.entries[0].priority == 0.8
        assert sitemap.entries[1].changefreq == "monthly"
        assert sitemap.entries[1].priority == 0.5

    def test_parse_sitemap_index(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap>
                <loc>http://example.com/sitemap1.xml</loc>
            </sitemap>
            <sitemap>
                <loc>http://example.com/sitemap2.xml</loc>
            </sitemap>
        </sitemapindex>"""
        sitemap = self.parser.parse(xml)
        assert sitemap.sitemap_count == 2
        assert "http://example.com/sitemap1.xml" in sitemap.sitemaps

    def test_parse_text_sitemap(self):
        text = "http://example.com/page1\nhttp://example.com/page2\n# comment\n\nhttp://example.com/page3"
        sitemap = self.parser.parse_text_sitemap(text)
        assert sitemap.url_count == 3

    def test_parse_text_sitemap_empty(self):
        sitemap = self.parser.parse_text_sitemap("")
        assert sitemap.url_count == 0

    def test_parse_text_sitemap_with_comments(self):
        text = "# This is a comment\nhttp://example.com/page1\n# Another comment"
        sitemap = self.parser.parse_text_sitemap(text)
        assert sitemap.url_count == 1

    def test_get_urls(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://example.com/a</loc></url>
            <url><loc>http://example.com/b</loc></url>
        </urlset>"""
        sitemap = self.parser.parse(xml)
        urls = sitemap.get_urls()
        assert "http://example.com/a" in urls
        assert "http://example.com/b" in urls

    def test_filter_by_priority(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://example.com/high</loc><priority>0.9</priority></url>
            <url><loc>http://example.com/low</loc><priority>0.1</priority></url>
        </urlset>"""
        sitemap = self.parser.parse(xml)
        high = self.parser.filter_by_priority(sitemap, min_priority=0.5)
        assert len(high) == 1
        assert high[0].loc == "http://example.com/high"

    def test_filter_by_changefreq(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://example.com/daily</loc><changefreq>daily</changefreq></url>
            <url><loc>http://example.com/monthly</loc><changefreq>monthly</changefreq></url>
        </urlset>"""
        sitemap = self.parser.parse(xml)
        daily = self.parser.filter_by_changefreq(sitemap, freq="daily")
        assert len(daily) == 1
        assert daily[0].loc == "http://example.com/daily"

    def test_source_url_preserved(self):
        sitemap = self.parser.parse("", source_url="http://example.com/sitemap.xml")
        assert sitemap.source_url == "http://example.com/sitemap.xml"

    def test_url_count_property(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <url><loc>http://example.com/a</loc></url>
        </urlset>"""
        sitemap = self.parser.parse(xml)
        assert sitemap.url_count == 1

    def test_sitemap_count_property(self):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
        <sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
            <sitemap><loc>http://example.com/s1.xml</loc></sitemap>
        </sitemapindex>"""
        sitemap = self.parser.parse(xml)
        assert sitemap.sitemap_count == 1


class TestSitemapGetUrlsFiltering:
    """Pin the corrected get_urls claim: only valid http/https entries are returned."""

    def test_get_urls_excludes_invalid_entries(self):
        from personal_index.sitemap import Sitemap

        valid = SitemapEntry(loc="https://example.com/page")
        invalid = SitemapEntry(loc="example.com/bare")
        sitemap = Sitemap(entries=[valid, invalid])
        urls = sitemap.get_urls()
        assert urls == ["https://example.com/page"]
        assert len(urls) == 1


class TestSitemapParseContract:
    """Pin the corrected SitemapParser.parse claim: guards + urlset dispatch."""

    def setup_method(self):
        from personal_index.sitemap import SitemapParser

        self.parser = SitemapParser()

    def test_parse_urlset_main_branch(self):
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            "<url><loc>http://example.com/a</loc></url>"
            "<url><loc>http://example.com/b</loc></url>"
            "</urlset>"
        )
        sitemap = self.parser.parse(xml, source_url="http://example.com/sitemap.xml")
        assert sitemap.source_url == "http://example.com/sitemap.xml"
        assert sitemap.url_count == 2
        assert [e.loc for e in sitemap.entries] == [
            "http://example.com/a",
            "http://example.com/b",
        ]
        assert sitemap.sitemaps == []

    def test_parse_empty_guard(self):
        sitemap = self.parser.parse("", source_url="http://example.com/s.xml")
        assert sitemap.source_url == "http://example.com/s.xml"
        assert sitemap.url_count == 0
        assert sitemap.sitemaps == []

    def test_parse_error_guard(self):
        sitemap = self.parser.parse("this is not xml", source_url="http://example.com/s.xml")
        assert sitemap.source_url == "http://example.com/s.xml"
        assert sitemap.url_count == 0
        assert sitemap.sitemaps == []


class TestSitemapGetRecentEntriesContract:
    """Pinning tests for SitemapParser.get_recent_entries exact contract."""

    def setup_method(self):
        self.parser = SitemapParser()

    def test_recent_entries_main_and_guard_paths(self):
        from datetime import datetime, timedelta, timezone

        now = datetime.now(timezone.utc)
        recent = (now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
        old = (now - timedelta(days=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
        xml = (
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            f"<url><loc>http://example.com/recent</loc><lastmod>{recent}</lastmod></url>"
            f"<url><loc>http://example.com/old</loc><lastmod>{old}</lastmod></url>"
            "<url><loc>http://example.com/nomod</loc></url>"
            "<url><loc>http://example.com/bad</loc><lastmod>not-a-date</lastmod></url>"
            "</urlset>"
        )
        sitemap = self.parser.parse(xml)
        result = self.parser.get_recent_entries(sitemap, days=30)
        # main path: recent included; old excluded (90 > 30)
        # guard paths: no-lastmod and unparseable-lastmod both skipped
        assert [e.loc for e in result] == ["http://example.com/recent"]

    def test_recent_entries_empty_sitemap(self):
        sitemap = self.parser.parse("", source_url="http://example.com/s.xml")
        assert self.parser.get_recent_entries(sitemap, days=30) == []
