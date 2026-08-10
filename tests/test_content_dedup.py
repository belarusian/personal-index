import unittest
from personal_index.content_dedup import find_duplicates, remove_duplicates
class TestDedup(unittest.TestCase):
    def test_find(self): self.assertIsInstance(find_duplicates(["a","a","b"]), list)
    def test_remove(self): self.assertTrue(remove_duplicates(["a","a","b"]))
if __name__=="__main__": unittest.main()
