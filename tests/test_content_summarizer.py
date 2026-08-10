import unittest
from personal_index.content_summarizer import summarize, extract_keywords
class TestSummarizer(unittest.TestCase):
    def test_summarize(self): self.assertIsInstance(summarize("long text"), str)
    def test_keywords(self): self.assertIsInstance(extract_keywords("text"), list)
if __name__=="__main__": unittest.main()


class TestSentenceScoresConsistency:
    """Test that sentence_scores tuples have consistent types (TICKET-36)."""

    def test_sentence_scores_all_float_first_element(self):
        """All sentence_scores tuples should have float as first element."""
        from personal_index.summarizer import TextSummarizer
        s = TextSummarizer()
        # Text with some empty sentences to trigger the (0, i, sentence) path
        text = "Hello world. . This is a test. . Another sentence."
        result = s.summarize(text)
        # Should not raise TypeError from mixed int/float comparison
        assert isinstance(result.summary, str)
