import unittest
from personal_index.content_priority import calculate_priority, sort_by_priority, PriorityScorer


class TestPriority(unittest.TestCase):
    def test_calc(self):
        self.assertIsInstance(calculate_priority("item"), (int, float))

    def test_sort(self):
        self.assertIsInstance(sort_by_priority(["a", "b"]), list)

    def test_score_topical_with_title_match_returns_float(self):
        """_score_topical should handle float matches (TICKET-38)."""
        scorer = PriorityScorer()
        content = {
            'title': 'Python Programming',
            'content': '',
            'tags': [],
            'user_interests': ['python']
        }
        result = scorer._score_topical(content)
        self.assertIsInstance(result, float)
        self.assertTrue(0.0 <= result <= 1.0)


if __name__ == "__main__":
    unittest.main()
