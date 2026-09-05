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


class TestContentChangelogGetEntriesPinning(unittest.TestCase):
    """Pin the corrected get_entries docstring claim against the returned object."""

    def _entry(self, url, change_type, ts):
        return ChangeEntry(url=url, change_type=change_type, timestamp=ts)

    def test_filtered_returns_only_exact_match_entries(self):
        # Normal case: truthy url -> only entries with e.url == url (exact match).
        cl = ContentChangelog()
        e1 = self._entry("http://example.com", "modified", "2024-01-01")
        e2 = self._entry("http://other.com", "added", "2024-01-02")
        e3 = self._entry("http://example.com", "deleted", "2024-01-03")
        cl.add_entry(e1)
        cl.add_entry(e2)
        cl.add_entry(e3)
        result = cl.get_entries("http://example.com")
        # Returned object: a list of exactly the two exact-match entries, in order.
        self.assertEqual(len(result), 2)
        self.assertEqual([e.url for e in result], ["http://example.com", "http://example.com"])
        self.assertEqual([e.change_type for e in result], ["modified", "deleted"])
        # Exact match, not substring/prefix: a prefix of a stored url matches nothing.
        self.assertEqual(cl.get_entries("http://example"), [])

    def test_falsy_url_guard_returns_all_entries(self):
        # Guard path: falsy url (None and "") -> a copy of ALL entries.
        cl = ContentChangelog()
        e1 = self._entry("http://example.com", "modified", "2024-01-01")
        e2 = self._entry("http://other.com", "added", "2024-01-02")
        cl.add_entry(e1)
        cl.add_entry(e2)
        for falsy in (None, ""):
            result = cl.get_entries(falsy)
            self.assertEqual(len(result), 2)
            self.assertEqual([e.url for e in result], ["http://example.com", "http://other.com"])
            # Returned object is a NEW list (a copy), not the internal list.
            result.append(self._entry("http://x.com", "added", "2024-02-01"))
            self.assertEqual(len(cl.get_entries()), 2)

    def test_empty_changelog_returns_empty_list(self):
        cl = ContentChangelog()
        self.assertEqual(cl.get_entries(), [])
        self.assertEqual(cl.get_entries("http://example.com"), [])


if __name__ == "__main__":
    unittest.main()
