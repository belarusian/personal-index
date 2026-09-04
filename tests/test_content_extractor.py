"""Tests for personal_index.content_extractor."""

import pytest

from personal_index.content_extractor import ContentExtractor, ExtractedContent


@pytest.fixture
def extractor():
    return ContentExtractor(max_text_length=10000)


class TestExtractedContent:
    """Tests for ExtractedContent."""

    def test_defaults(self):
        content = ExtractedContent()
        assert content.title == ""
        assert content.text == ""
        assert content.meta_description == ""
        assert content.meta_keywords == []
        assert content.headings == []
        assert content.word_count == 0


class TestContentExtractor:
    """Tests for ContentExtractor."""

    def test_empty_html(self, extractor):
        content = extractor.extract("")
        assert content.title == ""
        assert content.text == ""

    def test_extract_title(self, extractor):
        html = "<html><head><title>Test Page</title></head><body></body></html>"
        content = extractor.extract(html)
        assert content.title == "Test Page"

    def test_extract_og_title(self, extractor):
        html = """
        <html>
        <head>
            <meta property="og:title" content="OG Title">
        </head>
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert content.title == "OG Title"

    def test_extract_meta_description(self, extractor):
        html = """
        <html>
        <head>
            <meta name="description" content="A test description">
        </head>
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert content.meta_description == "A test description"

    def test_extract_meta_keywords(self, extractor):
        html = """
        <html>
        <head>
            <meta name="keywords" content="python, programming, test">
        </head>
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert "python" in content.meta_keywords
        assert "programming" in content.meta_keywords

    def test_extract_headings(self, extractor):
        html = """
        <html>
        <body>
            <h1>Main Title</h1>
            <h2>Subtitle</h2>
            <h3>Section</h3>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert "Main Title" in content.headings
        assert "Subtitle" in content.headings
        assert "Section" in content.headings

    def test_extract_links(self, extractor):
        html = """
        <html>
        <body>
            <a href="https://example.com">Example</a>
            <a href="https://test.com">Test</a>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert len(content.links) == 2
        assert ("Example", "https://example.com") in content.links

    def test_extract_images(self, extractor):
        html = """
        <html>
        <body>
            <img src="image1.jpg" alt="First Image">
            <img src="image2.png" alt="Second Image">
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert len(content.images) == 2
        assert ("First Image", "image1.jpg") in content.images

    def test_extract_text(self, extractor):
        html = """
        <html>
        <body>
            <p>This is the main content of the page.</p>
            <p>Another paragraph with more text.</p>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert "main content" in content.text
        assert "Another paragraph" in content.text

    def test_extract_removes_scripts(self, extractor):
        html = """
        <html>
        <body>
            <p>Visible text</p>
            <script>alert('xss')</script>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert "Visible text" in content.text
        assert "alert" not in content.text

    def test_extract_removes_styles(self, extractor):
        html = """
        <html>
        <body>
            <p>Visible text</p>
            <style>body { color: red; }</style>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert "Visible text" in content.text
        assert "color" not in content.text

    def test_word_count(self, extractor):
        html = """
        <html>
        <body>
            <p>One two three four five</p>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert content.word_count == 5

    def test_max_text_length(self, extractor):
        html = """
        <html>
        <body>
            <p>""" + "word " * 10000 + """</p>
        </body>
        </html>
        """
        content = extractor.extract(html)
        assert len(content.text) <= 10000

    def test_canonical_url(self, extractor):
        html = """
        <html>
        <head>
            <link rel="canonical" href="https://example.com/canonical">
        </head>
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert content.canonical_url == "https://example.com/canonical"

    def test_language(self, extractor):
        html = """
        <html lang="en">
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert content.language == "en"

    def test_author(self, extractor):
        html = """
        <html>
        <head>
            <meta name="author" content="John Doe">
        </head>
        <body></body>
        </html>
        """
        content = extractor.extract(html)
        assert content.author == "John Doe"

    def test_readability_score_empty(self, extractor):
        content = ExtractedContent()
        score = extractor.extract_readability_score(content)
        assert score == 0.0

    def test_readability_score_short(self, extractor):
        content = ExtractedContent(text="Short text")
        score = extractor.extract_readability_score(content)
        assert score == 0.0

    def test_readability_score_good(self, extractor):
        text = " ".join(["word"] * 200) + "."
        content = ExtractedContent(
            text=text,
            headings=["Title"],
            meta_description="A description",
        )
        score = extractor.extract_readability_score(content)
        assert score > 0.5

    def test_readability_score_exact_components(self, extractor):
        """Pin the corrected docstring claim: score = min(words/500,0.4) + min(headings*0.1,0.3) + 0.3."""
        text = " ".join(["word"] * 200)
        content = ExtractedContent(
            text=text,
            headings=["Title"],
            meta_description="A description",
        )
        score = extractor.extract_readability_score(content)
        # 200 words: min(200/500, 0.4) = 0.4
        # 1 heading: min(1*0.1, 0.3) = 0.1
        # meta_description: 0.3
        # total: 0.8
        assert score == 0.8
