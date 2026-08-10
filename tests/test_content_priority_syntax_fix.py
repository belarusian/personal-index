"""Tests for TICKET-7: Verify content_priority.py syntax is fixed."""
import unittest
from personal_index.content_priority import (
    PriorityLevel,
    PriorityScorer,
    PriorityFilter,
    PriorityConfig,
)


class TestContentPrioritySyntaxFix(unittest.TestCase):
    """Verify content_priority.py parses correctly and methods work."""

    def test_module_imports(self):
        """Module should import without SyntaxError."""
        from personal_index import content_priority
        self.assertIsNotNone(content_priority)

    def test_filter_by_level_works(self):
        """filter_by_level should return filtered results."""
        filter_engine = PriorityFilter()
        items = [{"url": "http://example.com", "title": "Test"}]
        result = filter_engine.filter_by_level(items, PriorityLevel.LOW)
        self.assertIsInstance(result, list)

    def test_get_top_n_works(self):
        """get_top_n should return top N items."""
        filter_engine = PriorityFilter()
        items = [{"url": f"http://example.com/{i}", "title": f"Item {i}"} for i in range(5)]
        result = filter_engine.get_top_n(items, n=3)
        self.assertEqual(len(result), 3)

    def test_group_by_level_works(self):
        """group_by_level should return dict of levels."""
        filter_engine = PriorityFilter()
        items = [{"url": "http://example.com", "title": "Test"}]
        result = filter_engine.group_by_level(items)
        self.assertIsInstance(result, dict)


if __name__ == "__main__":
    unittest.main()
