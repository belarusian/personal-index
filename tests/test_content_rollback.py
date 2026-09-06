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

    def test_rollback_returns_indexed_point_without_mutation(self):
        # TICKET-320: rollback is a pure accessor — it returns the point at
        # the given index (0 = oldest) and does not mutate the stored list.
        p1 = RollbackPoint(url="http://example.com", content="v1")
        p2 = RollbackPoint(url="http://example.com", content="v2")
        self.rollback.create_rollback_point(p1)
        self.rollback.create_rollback_point(p2)

        result = self.rollback.rollback("http://example.com", index=0)
        self.assertIsNotNone(result)
        self.assertEqual(result.content, "v1")  # 0 = oldest

        result_last = self.rollback.rollback("http://example.com", index=1)
        self.assertEqual(result_last.content, "v2")

        # No mutation: both points remain stored, in original order.
        stored = self.rollback.get_rollback_points("http://example.com")
        self.assertEqual([pt.content for pt in stored], ["v1", "v2"])

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


class TestClearDocstring533(unittest.TestCase):
    """Pin the ContentRollback.clear two-path contract (TICKET-533)."""

    def test_docstring_states_exact_contract(self):
        doc = ContentRollback.clear.__doc__
        assert doc is not None
        # Key contract phrases the docstring must state.
        assert "pop" in doc
        assert "clear" in doc
        assert "url" in doc
        assert "None" in doc


if __name__ == "__main__":
    unittest.main()
