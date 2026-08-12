"""Tests for content_rollback module."""

import unittest

from personal_index.content_rollback import ContentRollback, RollbackPoint


class TestRollbackPoint(unittest.TestCase):
    def test_create_point(self):
        point = RollbackPoint(url="http://example.com", content="old content")
        self.assertEqual(point.url, "http://example.com")
        self.assertEqual(point.content, "old content")
        self.assertEqual(point.title, "")
        self.assertEqual(point.metadata, {})


class TestContentRollback(unittest.TestCase):
    def setUp(self):
        self.rollback = ContentRollback()

    def test_create_rollback_point(self):
        point = RollbackPoint(url="http://example.com", content="old content")
        self.rollback.create_rollback_point(point)
        points = self.rollback.get_rollback_points("http://example.com")
        self.assertEqual(len(points), 1)
        self.assertEqual(points[0].content, "old content")

    def test_multiple_rollback_points(self):
        point1 = RollbackPoint(url="http://example.com", content="v1")
        point2 = RollbackPoint(url="http://example.com", content="v2")
        self.rollback.create_rollback_point(point1)
        self.rollback.create_rollback_point(point2)
        points = self.rollback.get_rollback_points("http://example.com")
        self.assertEqual(len(points), 2)

    def test_rollback(self):
        point = RollbackPoint(url="http://example.com", content="old content")
        self.rollback.create_rollback_point(point)
        result = self.rollback.rollback("http://example.com")
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "old content")

    def test_rollback_empty(self):
        result = self.rollback.rollback("http://nonexistent.com")
        self.assertIsNone(result)

    def test_clear_specific_url(self):
        point1 = RollbackPoint(url="http://example.com", content="v1")
        point2 = RollbackPoint(url="http://other.com", content="v2")
        self.rollback.create_rollback_point(point1)
        self.rollback.create_rollback_point(point2)
        self.rollback.clear("http://example.com")
        self.assertEqual(len(self.rollback.get_rollback_points("http://example.com")), 0)
        self.assertEqual(len(self.rollback.get_rollback_points("http://other.com")), 1)

    def test_clear_all(self):
        point = RollbackPoint(url="http://example.com", content="v1")
        self.rollback.create_rollback_point(point)
        self.rollback.clear()
        self.assertEqual(len(self.rollback.get_rollback_points("http://example.com")), 0)


if __name__ == "__main__":
    unittest.main()
