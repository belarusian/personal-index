"""Tests for text utilities module."""

import pytest
from personal_index.text_utils import (
    extract_text_from_html,
    extract_title_from_html,
    extract_meta_description,
    tokenize,
    generate_snippet,
    compute_text_similarity,
    truncate_text,
    count_words,
    extract_links_from_html,
)


class TestExtractTextFromHtml:
    def test_basic_extraction(self):
        html = "<html><body><p>Hello World</p></body></html>"
        text = extract_text_from_html(html)
        assert "Hello World" in text

    def test_removes_scripts(self):
        html = "<html><body><script>alert('xss')</script><p>Safe</p></body></html>"
        text = extract_text_from_html(html)
        assert "alert" not in text
        assert "Safe" in text

    def test_removes_styles(self):
        html = "<html><body><style>.hidden { display: none; }</style><p>Visible</p></body></html>"
        text = extract_text_from_html(html)
        assert "display" not in text
        assert "Visible" in text

    def test_handles_empty_input(self):
        assert extract_text_from_html("") == ""
        assert extract_text_from_html(None) == ""

    def test_handles_html_entities(self):
        html = "<p>Hello &amp; World</p>"
        text = extract_text_from_html(html)
        assert "&" in text

    def test_cleans_whitespace(self):
        html = "<p>  Hello    World  </p>"
        text = extract_text_from_html(html)
        assert text == "Hello World"

    def test_removes_noscript(self):
        html = "<html><body><noscript>No JS</noscript><p>Content</p></body></html>"
        text = extract_text_from_html(html)
        assert "No JS" not in text
        assert "Content" in text


class TestExtractTitleFromHtml:
    def test_basic_title(self):
        html = "<html><head><title>My Page</title></head></html>"
        assert extract_title_from_html(html) == "My Page"

    def test_title_with_attributes(self):
        html = "<html><head><title class=\"x\">My Page</title></head></html>"
        assert extract_title_from_html(html) == "My Page"

    def test_no_title(self):
        html = "<html><body>No title here</body></html>"
        assert extract_title_from_html(html) == ""

    def test_empty_input(self):
        assert extract_title_from_html("") == ""
        assert extract_title_from_html(None) == ""


class TestExtractMetaDescription:
    def test_basic_meta(self):
        html = '<meta name="description" content="A test description">'
        assert extract_meta_description(html) == "A test description"

    def test_reversed_attributes(self):
        html = '<meta content="A test description" name="description">'
        assert extract_meta_description(html) == "A test description"

    def test_no_meta(self):
        html = "<html><body>No meta</body></html>"
        assert extract_meta_description(html) == ""

    def test_empty_input(self):
        assert extract_meta_description("") == ""
        assert extract_meta_description(None) == ""


class TestTokenize:
    def test_basic_tokenization(self):
        tokens = tokenize("Hello World this is a test")
        assert "hello" in tokens
        assert "world" in tokens
        assert "test" in tokens

    def test_filters_stopwords(self):
        tokens = tokenize("The quick brown fox")
        assert "the" not in tokens
        assert "quick" in tokens
        assert "brown" in tokens
        assert "fox" in tokens

    def test_lowercase(self):
        tokens = tokenize("HELLO WORLD")
        assert "hello" in tokens
        assert "world" in tokens

    def test_empty_input(self):
        assert tokenize("") == []
        assert tokenize(None) == []

    def test_filters_short_words(self):
        tokens = tokenize("a I am")
        assert len(tokens) == 0

    def test_keeps_numbers(self):
        tokens = tokenize("Python 3.10 is great")
        assert "3" in tokens or "10" in tokens


class TestGenerateSnippet:
    def test_basic_snippet(self):
        text = "This is a long text about Python programming"
        snippet = generate_snippet(text, "python", max_length=30)
        assert "Python" in snippet or "python" in snippet.lower()

    def test_truncates_long_text(self):
        text = "A" * 500
        snippet = generate_snippet(text, "a", max_length=100)
        assert len(snippet) <= 105  # max_length + ellipsis

    def test_empty_text(self):
        assert generate_snippet("", "query") == ""

    def test_no_query_terms(self):
        text = "Some text here"
        snippet = generate_snippet(text, "!!!", max_length=100)
        assert snippet == "Some text here"


class TestComputeTextSimilarity:
    def test_identical_texts(self):
        assert compute_text_similarity("hello world", "hello world") == 1.0

    def test_completely_different(self):
        assert compute_text_similarity("hello world", "foo bar") == 0.0

    def test_partial_overlap(self):
        sim = compute_text_similarity("hello world foo", "hello world bar")
        assert 0 < sim < 1

    def test_empty_texts(self):
        assert compute_text_similarity("", "hello") == 0.0
        assert compute_text_similarity("hello", "") == 0.0


class TestTruncateText:
    def test_no_truncation_needed(self):
        text = "Short text"
        assert truncate_text(text, max_length=100) == text

    def test_truncation(self):
        text = "A" * 200
        result = truncate_text(text, max_length=100)
        assert len(result) <= 103
        assert result.endswith("...")

    def test_preserves_word_boundaries(self):
        text = "Hello World Foo Bar"
        result = truncate_text(text, max_length=10)
        assert " " not in result or result.endswith("...")


class TestCountWords:
    def test_basic_count(self):
        assert count_words("Hello World") == 2

    def test_empty(self):
        assert count_words("") == 0
        assert count_words(None) == 0

    def test_multiple_spaces(self):
        assert count_words("Hello   World") == 2


class TestExtractLinksFromHtml:
    def test_absolute_links(self):
        html = '<a href="https://example.com/page">Link</a>'
        links = extract_links_from_html(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_relative_links(self):
        html = '<a href="/page">Link</a>'
        links = extract_links_from_html(html, "https://example.com")
        assert "https://example.com/page" in links

    def test_excludes_javascript(self):
        html = '<a href="javascript:void(0)">Link</a>'
        links = extract_links_from_html(html, "https://example.com")
        assert len(links) == 0

    def test_excludes_mailto(self):
        html = '<a href="mailto:test@example.com">Link</a>'
        links = extract_links_from_html(html, "https://example.com")
        assert len(links) == 0

    def test_excludes_hash(self):
        html = '<a href="#section">Link</a>'
        links = extract_links_from_html(html, "https://example.com")
        assert len(links) == 0
