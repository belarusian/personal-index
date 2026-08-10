"""Tests for content_diff module."""

import unittest
from personal_index.content_diff import DiffResult, compute_diff


class TestDiffResult(unittest.TestCase):
    def test_create_result(self):
        result = DiffResult(url="http://example.com")
        self.assertEqual(result.url, "http://example.com")
        self.assertEqual(result.added_lines, 0)
        self.assertEqual(result.removed_lines, 0)
        self.assertEqual(result.changed_lines, 0)
        self.assertEqual(result.diff_text, "")


class TestComputeDiff(unittest.TestCase):
    def test_identical_content(self):
        old = "hello\nworld\n"
        new = "hello\nworld\n"
        result = compute_diff(old, new, "http://example.com")
        self.assertEqual(result.added_lines, 0)
        self.assertEqual(result.removed_lines, 0)

    def test_added_lines(self):
        old = "hello\n"
        new = "hello\nworld\n"
        result = compute_diff(old, new, "http://example.com")
        self.assertGreater(result.added_lines, 0)
        self.assertEqual(result.removed_lines, 0)

    def test_removed_lines(self):
        old = "hello\nworld\n"
        new = "hello\n"
        result = compute_diff(old, new, "http://example.com")
        self.assertEqual(result.added_lines, 0)
        self.assertGreater(result.removed_lines, 0)

    def test_changed_lines(self):
        old = "hello\nworld\n"
        new = "hello\nearth\n"
        result = compute_diff(old, new, "http://example.com")
        self.assertGreater(result.changed_lines, 0)

    def test_empty_content(self):
        result = compute_diff("", "", "http://example.com")
        self.assertEqual(result.added_lines, 0)
        self.assertEqual(result.removed_lines, 0)


if __name__ == "__main__":
    unittest.main()
