"""End-to-end tests for content extraction."""

from __future__ import annotations

from personal_index.content_extractor import ContentExtractor


class TestContentExtractionE2E:
    """Test content extraction with realistic HTML."""

    def test_extract_basic_page(self):
        """Extract title and content from basic HTML."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Welcome</h1>
                <p>This is the main content of the page.</p>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert result.title == "Test Page"
        assert "Welcome" in result.text
        assert "main content" in result.text

    def test_extract_with_script_tags(self):
        """Script tags should be removed."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Page</title></head>
            <body>
                <p>Real content here</p>
                <script>alert('test');</script>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert "alert" not in result.text.lower()
        assert "Real content" in result.text

    def test_extract_with_style_tags(self):
        """Style tags should be removed."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Page</title></head>
            <body>
                <p>Content</p>
                <style>.class { color: red; }</style>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert "color" not in result.text.lower()
        assert "Content" in result.text

    def test_extract_with_nested_tags(self):
        """Handle nested HTML structure."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Nested</title></head>
            <body>
                <div class="container">
                    <article>
                        <h1>Article Title</h1>
                        <p>Article content with <strong>bold text</strong>.</p>
                    </article>
                </div>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert "Nested" in result.title
        assert "Article content" in result.text

    def test_extract_empty_body(self):
        """Handle page with empty body."""
        extractor = ContentExtractor()
        html = "<html><head><title>Empty</title></head><body></body></html>"
        result = extractor.extract(html)
        assert result.title == "Empty"
        # Text includes title by default
        assert "Empty" in result.text

    def test_extract_no_title(self):
        """Handle page without title tag."""
        extractor = ContentExtractor()
        html = "<html><body><p>Content only</p></body></html>"
        result = extractor.extract(html)
        # Should use a default or empty title
        assert isinstance(result.title, str)

    def test_extract_with_links(self):
        """Links should be preserved in content."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Links</title></head>
            <body>
                <p>Check out <a href="https://example.com">this link</a> for more info.</p>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert "link" in result.text.lower()

    def test_extract_with_images(self):
        """Image alt text should be included."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Images</title></head>
            <body>
                <img src="test.png" alt="Test image description">
            </body>
        </html>
        """
        result = extractor.extract(html)
        # Check images list
        assert len(result.images) == 1
        assert "description" in result.images[0][0].lower()

    def test_extract_preserves_text_order(self):
        """Text order should be preserved."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Order</title></head>
            <body>
                <p>First paragraph.</p>
                <p>Second paragraph.</p>
                <p>Third paragraph.</p>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert result.text.index("First") < result.text.index("Second")
        assert result.text.index("Second") < result.text.index("Third")

    def test_extract_with_tables(self):
        """Table content should be included."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Tables</title></head>
            <body>
                <table>
                    <tr><td>Cell 1</td><td>Cell 2</td></tr>
                </table>
            </body>
        </html>
        """
        result = extractor.extract(html)
        assert "Cell" in result.text
