"""Tests for personal_index.text_utils."""

import pytest
from personal_index.text_utils import (
    clean_html,
    tokenize,
    remove_stopwords,
    extract_keywords,
    truncate_text,
    compute_text_similarity,
    extract_email_addresses,
    extract_urls,
    STOPWORDS,
)


class TestCleanHtml:
    def test_remove_tags(self):
        html = "<p>Hello <b>World</b></p>"
        assert clean_html(html) == "Hello World"

    def test_remove_scripts(self):
        html = "<p>Text</p><script>alert('xss')</script>"
        result = clean_html(html)
        assert "Text" in result
        assert "alert" not in result

    def test_remove_styles(self):
        html = "<p>Text</p><style>.hidden { display: none; }</style>"
        result = clean_html(html)
        assert "Text" in result
        assert "display" not in result

    def test_decode_entities(self):
        html = "&lt;hello&gt; &amp; world"
        result = clean_html(html)
        assert "<hello>" in result
        assert "&" in result

    def test_normalize_whitespace(self):
        html = "<p>  Hello   World  </p>"
        result = clean_html(html)
        assert result == "Hello World"


class TestTokenize:
    def test_basic_tokenize(self):
        tokens = tokenize("Hello world")
        assert tokens == ["hello", "world"]

    def test_tokenize_with_punctuation(self):
        tokens = tokenize("Hello, world!")
        assert tokens == ["hello", "world"]

    def test_tokenize_preserve_case(self):
        tokens = tokenize("Hello World", lowercase=False)
        assert tokens == ["Hello", "World"]

    def test_tokenize_with_numbers(self):
        tokens = tokenize("Python 3.10 is great")
        assert "python" in tokens
        assert "3" in tokens or "10" in tokens

    def test_tokenize_empty(self):
        tokens = tokenize("")
        assert tokens == []


class TestRemoveStopwords:
    def test_remove_common_stopwords(self):
        tokens = ["the", "quick", "brown", "fox"]
        result = remove_stopwords(tokens)
        assert "the" not in result
        assert "quick" in result
        assert "brown" in result
        assert "fox" in result

    def test_custom_stopwords(self):
        tokens = ["python", "code", "test"]
        result = remove_stopwords(tokens, stopwords={"test"})
        assert "test" not in result
        assert "python" in result

    def test_no_stopwords_to_remove(self):
        tokens = ["python", "programming"]
        result = remove_stopwords(tokens)
        assert len(result) == 2


class TestExtractKeywords:
    def test_extract_top_keywords(self):
        text = "python python python programming programming code"
        keywords = extract_keywords(text, top_n=3)
        assert len(keywords) <= 3
        assert keywords[0][0] == "python"
        assert keywords[0][1] == 3

    def test_extract_with_stopwords(self):
        text = "the the the python python code"
        keywords = extract_keywords(text, top_n=3)
        assert keywords[0][0] == "python"

    def test_extract_empty_text(self):
        keywords = extract_keywords("", top_n=5)
        assert keywords == []


class TestTruncateText:
    def test_no_truncation_needed(self):
        text = "Short text"
        assert truncate_text(text, max_length=100) == text

    def test_truncation(self):
        text = "A" * 200
        result = truncate_text(text, max_length=50)
        assert len(result) <= 50
        assert "..." in result

    def test_truncation_at_word_boundary(self):
        text = " ".join(["word"] * 50)
        result = truncate_text(text, max_length=30)
        assert "..." in result
        # Should not split a word
        assert "..word" not in result


class TestComputeTextSimilarity:
    def test_identical_texts(self):
        assert compute_text_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        assert compute_text_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        sim = compute_text_similarity("hello world foo", "hello world bar")
        assert 0.0 < sim < 1.0

    def test_empty_texts(self):
        assert compute_text_similarity("", "") == 1.0

    def test_one_empty(self):
        assert compute_text_similarity("hello", "") == 0.0


class TestExtractEmailAddresses:
    def test_extract_single_email(self):
        text = "Contact us at test@example.com for info"
        emails = extract_email_addresses(text)
        assert "test@example.com" in emails

    def test_extract_multiple_emails(self):
        text = "Email a@b.com or c@d.org"
        emails = extract_email_addresses(text)
        assert len(emails) == 2

    def test_no_emails(self):
        text = "No emails here"
        assert extract_email_addresses(text) == []


class TestExtractUrls:
    def test_extract_http_url(self):
        text = "Visit https://example.com for more"
        urls = extract_urls(text)
        assert "https://example.com" in urls

    def test_extract_https_url(self):
        text = "Go to https://example.com/path?q=1"
        urls = extract_urls(text)
        assert len(urls) > 0

    def test_no_urls(self):
        text = "No URLs here"
        assert extract_urls(text) == []
