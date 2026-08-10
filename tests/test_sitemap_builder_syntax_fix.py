"""Tests for TICKET-8: Verify sitemap_builder.py syntax is fixed."""
import unittest
from personal_index.sitemap_builder import SitemapBuilder, SitemapEntry


class TestSitemapBuilderSyntaxFix(unittest.TestCase):
    """Verify sitemap_builder.py parses correctly and methods work."""

    def test_module_imports(self):
        """Module should import without SyntaxError."""
        from personal_index import sitemap_builder
        self.assertIsNotNone(sitemap_builder)

    def test_add_entry_works(self):
        """add_entry should add an entry to the sitemap."""
        builder = SitemapBuilder(domain="example.com")
        builder.add_entry(url="http://example.com/page1")
        self.assertEqual(len(builder.entries), 1)
        self.assertEqual(builder.entries[0].url, "http://example.com/page1")

    def test_add_entry_with_all_params(self):
        """add_entry should accept all optional parameters."""
        from datetime import datetime
        builder = SitemapBuilder(domain="example.com")
        builder.add_entry(
            url="http://example.com/page2",
            last_modified=datetime(2024, 1, 1),
            change_frequency="weekly",
            priority=0.8,
        )
        self.assertEqual(len(builder.entries), 1)
        entry = builder.entries[0]
        self.assertEqual(entry.change_frequency, "weekly")
        self.assertEqual(entry.priority, 0.8)

    def test_add_entries_works(self):
        """add_entries should add multiple entries."""
        builder = SitemapBuilder(domain="example.com")
        entries = [
            SitemapEntry("http://example.com/1"),
            SitemapEntry("http://example.com/2"),
        ]
        builder.add_entries(entries)
        self.assertEqual(len(builder.entries), 2)

    def test_build_returns_bytes(self):
        """build should return bytes."""
        builder = SitemapBuilder(domain="example.com")
        builder.add_entry(url="http://example.com/page1")
        result = builder.build()
        self.assertIsInstance(result, bytes)


if __name__ == "__main__":
    unittest.main()
