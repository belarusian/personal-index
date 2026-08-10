import unittest
from personal_index.content_priority import calculate_priority, sort_by_priority
class TestPriority(unittest.TestCase):
    def test_calc(self): self.assertIsInstance(calculate_priority("item"), (int, float))
    def test_sort(self): self.assertIsInstance(sort_by_priority(["a","b"]), list)
if __name__=="__main__": unittest.main()
