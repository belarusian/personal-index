"""Tests for content extraction module."""

import pytest
from personal_index.content import (
    ExtractedContent,
    extract_content,
    remove_stopwords,
    compute_tf,
)
from personal_index.text_utils import tokenize


SAMPLE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <title>Test Page Title</title>
    <meta name="description" content="This is a test description">
    <meta name="keywords" content="test, example, demo">
</head>
<body>
    <h1>Main Heading</h1>
    <h2>Sub Heading</h2>
    <p>This is the main content of the page.</p>
    <p>It has multiple paragraphs.</p>
    <a href="http://example.com/link1">Link 1</a>
    <a href="http://example.com/link2">Link 2</a>
    <script>var x = 1;</script>
    <style>body { color: red; }</style>
</body>
</html>
"""


class TestExtractedContent:
    def test_creation(self):
        content = ExtractedContent(url="http://example.com")
        assert content.url == "http://example.com"
        assert content.title == ""
        assert content.text == ""

    def test_get_searchable_text(self):
        content = ExtractedContent(
            url="http://example.com",
            title="My Title",
            text="Some content here",
            headings=["h1: Main"],
        )
        searchable = content.get_searchable_text()
        assert "My Title" in searchable
        assert "Some content here" in searchable
        assert "Main" in searchable

    def test_get_keywords(self):
        content = ExtractedContent(
            url="http://example.com",
            meta_keywords=["python", "coding"],
            headings=["h1: Python Tutorial"],
        )
        keywords = content.get_keywords()
        assert "python" in keywords
        assert "coding" in keywords


class TestExtractContent:
    def test_extract_title(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert content.title == "Test Page Title"

    def test_extract_meta_description(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert content.meta_description == "This is a test description"

    def test_extract_meta_keywords(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert "test" in content.meta_keywords
        assert "example" in content.meta_keywords
        assert "demo" in content.meta_keywords

    def test_extract_headings(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert any("Main Heading" in h for h in content.headings)
        assert any("Sub Heading" in h for h in content.headings)

    def test_extract_text(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert "main content" in content.text.lower()
        assert "multiple paragraphs" in content.text.lower()

    def test_removes_scripts(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert "var x = 1" not in content.text

    def test_removes_styles(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert "color: red" not in content.text

    def test_extract_links(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert "http://example.com/link1" in content.links
        assert "http://example.com/link2" in content.links

    def test_content_length(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert content.content_length > 0

    def test_language_detection(self):
        content = extract_content(SAMPLE_HTML, "http://example.com")
        assert content.language == "en"

    def test_status_code(self):
        content = extract_content(SAMPLE_HTML, "http://example.com", status_code=404)
        assert content.status_code == 404


class TestTokenize:
    def test_basic_tokenize(self):
        # text_utils.tokenize requires 2+ char tokens, so "a" is excluded
        tokens = tokenize("Hello World, this is a test!")
        assert tokens == ["hello", "world", "this", "is", "test"]

    def test_empty_string(self):
        tokens = tokenize("")
        assert tokens == []

    def test_numbers(self):
        tokens = tokenize("Version 2.0 has 100 items")
        assert "version" in tokens
        assert "100" in tokens

    def test_lowercase(self):
        tokens = tokenize("Hello World", lowercase=True)
        assert tokens == ["hello", "world"]

    def test_no_lowercase(self):
        tokens = tokenize("Hello World", lowercase=False)
        assert tokens == ["Hello", "World"]


class TestRemoveStopwords:
    def test_remove_common_stopwords(self):
        tokens = ["the", "quick", "brown", "fox", "jumps"]
        result = remove_stopwords(tokens)
        assert "the" not in result
        assert "quick" in result
        assert "brown" in result

    def test_custom_stopwords(self):
        tokens = ["python", "code", "test"]
        result = remove_stopwords(tokens, stopwords={"test"})
        assert "test" not in result
        assert "python" in result

    def test_empty_input(self):
        result = remove_stopwords([])
        assert result == []


class TestComputeTF:
    def test_basic_tf(self):
        tokens = ["hello", "world", "hello"]
        tf = compute_tf(tokens)
        assert tf["hello"] == 2 / 3
        assert tf["world"] == 1 / 3

    def test_empty_tokens(self):
        tf = compute_tf([])
        assert tf == {}

    def test_single_token(self):
        tokens = ["hello"]
        tf = compute_tf(tokens)
        assert tf["hello"] == 1.0
