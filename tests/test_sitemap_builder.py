"""Tests for the sitemap builder module."""

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

    def test_to_element_pins_documented_contract(self):
        """Pin the corrected to_element docstring: exactly four SubElements.

        The reworded docstring claims to_element attaches EXACTLY four
        SubElements (loc/lastmod/changefreq/priority) with the documented text
        formats. This test pins that claim against the returned Element and
        asserts the ABSENCE of any sibling SubElement (no extra tag), so the
        doc-only fix is witnessed.
        """
        entry = SitemapEntry(
            "http://example.com/page",
            change_frequency="weekly",
            priority=0.7,
        )
        elem = entry.to_element()
        assert elem.tag == "url"
        # Exactly the four documented SubElements, no more, no less.
        tags = [child.tag for child in elem]
        assert tags == ["loc", "lastmod", "changefreq", "priority"]
        # Documented text formats.
        assert elem.find("loc").text == "http://example.com/page"
        assert elem.find("changefreq").text == "weekly"
        assert elem.find("priority").text == "0.7"
        # lastmod is the documented "%Y-%m-%dT%H:%M:%SZ" format (Z-suffixed).
        lastmod = elem.find("lastmod").text
        assert lastmod is not None
        assert lastmod.endswith("Z")
        # Verify ISO-like format by parsing back.
        from datetime import datetime
        datetime.strptime(lastmod, "%Y-%m-%dT%H:%M:%SZ")
        # ABSENCE of any sibling SubElement: no nested <url> or extra tag.
        assert elem.find("url") is None
        assert len(list(elem)) == 4


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

    def test_add_entry_stores_exact_fields(self):
        # Pins the corrected add_entry claim: the entry stores the exact
        # change_frequency and priority passed, and auto-fills last_modified
        # (the sibling field the caller did not supply).
        builder = SitemapBuilder()
        builder.add_entry("http://example.com/x", change_frequency="hourly", priority=0.3)
        entry = builder.entries[-1]
        assert entry.change_frequency == "hourly"
        assert entry.priority == 0.3
        # last_modified was not passed -> auto-filled default, not None
        assert entry.last_modified is not None

    def test_split_by_size_enforces_byte_budget(self):
        # Option A: entries whose total serialized size exceeds
        # MAX_SITEMAP_SIZE_BYTES while staying under MAX_URLS_PER_SITEMAP.
        # split_by_size() must break chunks so no chunk serializes to more
        # than MAX_SITEMAP_SIZE_BYTES bytes.
        loc_len = 1200
        n = 45_000  # under MAX_URLS_PER_SITEMAP (50_000)
        assert n < SitemapBuilder.MAX_URLS_PER_SITEMAP
        builder = SitemapBuilder()
        for i in range(n):
            builder.add_entry("http://example.com/" + "x" * loc_len + f"/{i}")
        # Total serialized size exceeds the 50 MB budget.
        assert len(builder.build()) > SitemapBuilder.MAX_SITEMAP_SIZE_BYTES
        chunks = builder.split_by_size()
        assert len(chunks) >= 2  # the byte budget forced a split
        for chunk in chunks:
            sub = SitemapBuilder()
            sub.add_entries(chunk)
            assert len(sub.build()) <= SitemapBuilder.MAX_SITEMAP_SIZE_BYTES
        # Every entry is preserved across the split (no loss, no dup).
        assert sum(len(c) for c in chunks) == n

    def test_split_by_size_empty_builder_returns_empty_list(self):
        # Guard path: an empty builder has nothing to split.
        builder = SitemapBuilder()
        assert builder.split_by_size() == []

    def test_build_empty_builder_returns_declaration_and_empty_urlset(self):
        # Guard path: build() on an empty builder returns the XML declaration
        # plus an empty <urlset> (no entries).
        builder = SitemapBuilder()
        xml = builder.build().decode("utf-8")
        assert xml.startswith('<?xml version="1.0" encoding="UTF-8"?>')
        assert "<urlset" in xml
        assert "<loc>" not in xml  # no entries

    def test_docstrings_state_enforced_limits(self):
        # build() and split_into_chunks() docstrings must state which limits
        # are enforced and which are not (pin stable lowercase fragments).
        build_doc = SitemapBuilder.build.__doc__.lower()
        assert "no size limit" in build_doc
        assert "max_urls_per_sitemap" in build_doc
        assert "max_sitemap_size_bytes" in build_doc
        split_doc = SitemapBuilder.split_into_chunks.__doc__.lower()
        assert "url count only" in split_doc
        assert "max_sitemap_size_bytes" in split_doc
        size_doc = SitemapBuilder.split_by_size.__doc__.lower()
        assert "max_sitemap_size_bytes" in size_doc


class TestSitemapNamespace:
    """QA-23: build()/build_sitemap_index() emit the sitemap namespace."""

    def test_build_root_carries_sitemap_namespace(self):
        from xml.etree.ElementTree import fromstring

        from personal_index.sitemap_builder import SM_NS

        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        root = fromstring(b.build())
        assert root.tag == f"{{{SM_NS}}}urlset"

    def test_build_no_literal_nsmap_attribute(self):
        b = SitemapBuilder()
        b.add_entry("https://x.com/1")
        raw = b.build().decode("utf-8")
        assert "nsmap=" not in raw
        assert "xmlns" in raw

    def test_build_url_children_namespaced(self):
        from xml.etree.ElementTree import fromstring

        from personal_index.sitemap_builder import SM_NS

        b = SitemapBuilder()
        for i in range(3):
            b.add_entry(f"https://x.com/{i}")
        root = fromstring(b.build())
        assert len(root.findall(f"{{{SM_NS}}}url")) == 3

    def test_index_root_carries_sitemap_namespace(self):
        from xml.etree.ElementTree import fromstring

        from personal_index.sitemap_builder import SM_NS

        b = SitemapBuilder()
        root = fromstring(b.build_sitemap_index(["https://x.com/s1.xml"]))
        assert root.tag == f"{{{SM_NS}}}sitemapindex"

    def test_roundtrip_through_parser_recovers_urls(self):
        from personal_index.sitemap import SitemapParser

        b = SitemapBuilder()
        urls = [f"https://x.com/page/{i}" for i in range(4)]
        for u in urls:
            b.add_entry(u, change_frequency="weekly", priority=0.9)
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.get_urls() == urls

    def test_roundtrip_preserves_fields(self):
        from personal_index.sitemap import SitemapParser

        b = SitemapBuilder()
        b.add_entry("https://x.com/a", change_frequency="hourly", priority=0.3)
        parsed = SitemapParser().parse(b.build().decode("utf-8"))
        assert parsed.entries[0].changefreq == "hourly"
        assert parsed.entries[0].priority == 0.3
        assert parsed.entries[0].lastmod is not None
        assert parsed.entries[0].lastmod.endswith("Z")
