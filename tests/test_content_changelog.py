"""Tests for content_changelog module."""

import unittest
from personal_index.content_changelog import ChangeEntry, ContentChangelog


class TestChangeEntry(unittest.TestCase):
    def test_create_entry(self):
        entry = ChangeEntry(url="http://example.com", change_type="modified", timestamp="2024-01-01")
        self.assertEqual(entry.url, "http://example.com")
        self.assertEqual(entry.change_type, "modified")
        self.assertEqual(entry.details, {})

    def test_create_entry_with_details(self):
        entry = ChangeEntry(url="http://example.com", change_type="added", timestamp="2024-01-01", details={"key": "value"})
        self.assertEqual(entry.details, {"key": "value"})


class TestContentChangelog(unittest.TestCase):
    def setUp(self):
        self.changelog = ContentChangelog()

    def test_add_entry(self):
        entry = ChangeEntry(url="http://example.com", change_type="modified", timestamp="2024-01-01")
        self.changelog.add_entry(entry)
        entries = self.changelog.get_entries()
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, "http://example.com")

    def test_get_entries_filtered(self):
        entry1 = ChangeEntry(url="http://example.com", change_type="modified", timestamp="2024-01-01")
        entry2 = ChangeEntry(url="http://other.com", change_type="added", timestamp="2024-01-02")
        self.changelog.add_entry(entry1)
        self.changelog.add_entry(entry2)
        entries = self.changelog.get_entries("http://example.com")
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].url, "http://example.com")

    def test_clear(self):
        entry = ChangeEntry(url="http://example.com", change_type="modified", timestamp="2024-01-01")
        self.changelog.add_entry(entry)
        self.changelog.clear()
        self.assertEqual(len(self.changelog.get_entries()), 0)


if __name__ == "__main__":
    unittest.main()
