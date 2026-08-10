import unittest
from personal_index.content_changelog import generate_changelog, append_entry
class TestChangelog(unittest.TestCase):
    def test_generate(self): self.assertIsInstance(generate_changelog("content"), str)
    def test_append(self): self.assertTrue(append_entry("content", "feat: update"))
if __name__=="__main__": unittest.main()
