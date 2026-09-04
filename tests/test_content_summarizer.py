"""Tests for content summarization module."""

from __future__ import annotations

from personal_index.content_summarizer import (
    SummaryResult,
    _score_sentence,
    _split_sentences,
    _tokenize,
    _word_frequency,
    summarize,
    summarize_page,
)


class TestSplitSentences:
    def test_basic_split(self):
        text = "Hello world. This is a test. Goodbye!"
        result = _split_sentences(text)
        assert len(result) == 3
        assert result[0] == "Hello world."
        assert result[1] == "This is a test."
        assert result[2] == "Goodbye!"

    def test_empty_text(self):
        assert _split_sentences("") == []

    def test_single_sentence(self):
        text = "Just one sentence."
        result = _split_sentences(text)
        assert len(result) == 1
        assert result[0] == "Just one sentence."

    def test_whitespace_normalization(self):
        text = "  First  sentence.   Second  sentence.  "
        result = _split_sentences(text)
        assert len(result) == 2
        assert result[0] == "First sentence."
        assert result[1] == "Second sentence."

    def test_question_and_exclamation(self):
        text = "What is this? That is amazing! Really cool."
        result = _split_sentences(text)
        assert len(result) == 3


class TestTokenize:
    def test_basic_tokenize(self):
        assert _tokenize("Hello world") == ["hello", "world"]

    def test_mixed_case(self):
        assert _tokenize("Hello World") == ["hello", "world"]

    def test_with_numbers(self):
        assert _tokenize("Python 3.10 is great") == ["python", "3", "10", "is", "great"]

    def test_empty_string(self):
        assert _tokenize("") == []


class TestWordFrequency:
    def test_basic_frequency(self):
        text = "the cat sat on the mat the cat"
        freq = _word_frequency(text)
        assert freq["cat"] == 2
        assert freq["sat"] == 1
        assert freq["mat"] == 1
        # "the" is a stopword
        assert "the" not in freq

    def test_empty_text(self):
        assert _word_frequency("") == {}

    def test_stopwords_excluded(self):
        text = "the and or but in on at"
        freq = _word_frequency(text)
        assert len(freq) == 0


class TestScoreSentence:
    def test_basic_scoring(self):
        word_freq = {"python": 3, "programming": 2, "language": 1}
        score = _score_sentence("Python is a programming language", word_freq)
        assert score > 0

    def test_empty_sentence(self):
        assert _score_sentence("", {"word": 1}) == 0.0

    def test_no_matching_words(self):
        word_freq = {"python": 3}
        score = _score_sentence("Hello world", word_freq)
        assert score == 0.0


class TestSummarize:
    def test_short_text_returns_as_is(self):
        text = "Short text."
        result = summarize(text, min_length=50)
        assert result.summary == text
        assert result.ratio == 1.0

    def test_empty_text(self):
        result = summarize("")
        assert result.summary == ""
        assert result.sentences == []

    def test_summarize_long_text(self):
        text = (
            "Python is a programming language. "
            "Python supports multiple paradigms. "
            "Python is widely used in web development. "
            "Python has a large standard library. "
            "Python is easy to learn. "
            "Python is popular among beginners. "
            "Python runs on many platforms. "
            "Python is open source software."
        )
        result = summarize(text, max_sentences=3)
        assert len(result.sentences) <= 3
        assert len(result.summary) < len(text)
        assert result.ratio < 1.0

    def test_max_sentences_respected(self):
        sentences = ". ".join([f"Sentence number {i}." for i in range(20)])
        result = summarize(sentences, max_sentences=2)
        assert len(result.sentences) <= 2

    def test_first_sentence_boost(self):
        text = (
            "Important first sentence about the topic. "
            "Less important second sentence. "
            "Less important third sentence. "
            "Less important fourth sentence. "
            "Less important fifth sentence."
        )
        result = summarize(text, max_sentences=1)
        # First sentence should be selected due to boost
        assert "Important first sentence" in result.summary

    def test_summary_result_str(self):
        result = SummaryResult(
            original_text="test",
            summary="sum",
            sentences=["sum"],
            ratio=0.5,
            word_count_original=10,
            word_count_summary=5,
        )
        assert str(result) == "sum"


class TestSummarizePage:
    def test_page_summarization(self):
        title = "Python Programming Tutorial"
        content = (
            "Python is a great language. "
            "It supports OOP and functional programming. "
            "Many developers love Python. "
            "Python is used in data science."
        )
        result = summarize_page(title, content, max_sentences=2)
        assert len(result.sentences) <= 2
        assert result.ratio <= 1.0

    def test_page_with_empty_content(self):
        result = summarize_page("Title", "", max_sentences=3)
        assert result.summary == ""


class TestModuleDocstringContract:
    def test_docstring_does_not_promise_tfidf(self):
        """Regression: module docstring must not over-promise capabilities.

        The module implements no TF-IDF / inverse-document-frequency scoring
        (only keyword frequency), so its docstring must not claim to use
        'TF-IDF' or 'idf' metrics (TICKET-328).
        """
        import personal_index.content_summarizer as cs

        doc = (cs.__doc__ or "").lower()
        assert "tf-idf" not in doc
        assert "idf" not in doc


class TestSummarizePageTitleDocstringContract:
    def test_docstring_does_not_promise_keyword_boost(self):
        """Regression: summarize_page docstring must not over-promise.

        The body only prepends the title to the content and summarizes the
        combined text (combined = f"{title}. {content}"); there is no
        title-specific keyword boost / re-weighting mechanism. The docstring
        must therefore not claim a 'keyword boost' (TICKET-339).
        """
        import inspect

        src = inspect.getsource(summarize_page)
        assert "keyword boost" not in src
        assert "prepended to the content" in src

    def test_title_is_prepended_to_content(self):
        """Behavior unchanged: the title is prepended to the content.

        summarize_page builds combined = f"{title}. {content}" and summarizes
        it, so the returned original_text must start with the title (the title
        becomes the first sentence of the combined text).
        """
        title = "Python Programming"
        content = (
            "Python is a popular language. "
            "It is used in data science. "
            "Many developers love Python. "
            "Python is used in web development. "
            "It has a large ecosystem of libraries. "
            "Python is beginner friendly. "
        )
        result = summarize_page(title, content, max_sentences=2)
        # The title is prepended, so original_text starts with the title.
        assert result.original_text.startswith(title)
        # The title becomes the first sentence of the combined text.
        assert result.sentences[0].startswith(title)
