import unittest
from personal_index.export_markdown import export_to_md, save_markdown
class TestExport(unittest.TestCase):
    def test_export(self): self.assertIsInstance(export_to_md({"title": "Test"}), str)
    def test_save(self): self.assertTrue(save_markdown({"title": "Test"}, "out.md"))
if __name__=="__main__": unittest.main()
