import unittest
from personal_index.content_summarizer import summarize, extract_keywords
class TestSummarizer(unittest.TestCase):
    def test_summarize(self): self.assertIsInstance(summarize("long text"), str)
    def test_keywords(self): self.assertIsInstance(extract_keywords("text"), list)
if __name__=="__main__": unittest.main()
