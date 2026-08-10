import unittest
from personal_index.content_diff import compute_diff, apply_patch
class TestDiff(unittest.TestCase):
    def test_compute(self): self.assertIsInstance(compute_diff("old", "new"), str)
    def test_apply(self): self.assertEqual(apply_patch("base", "diff"), "result")
if __name__=="__main__": unittest.main()
