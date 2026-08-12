"""Integration tests for link_preview with the scraper and content pipeline."""

from __future__ import annotations

from personal_index.link_preview import LinkPreviewGenerator
from personal_index.scraper import HTMLScraper, ScraperConfig


class TestLinkPreviewWithScraper:
    """Test that LinkPreviewGenerator works alongside HTMLScraper."""

    def _make_realistic_html(self) -> str:
        """Create a realistic HTML page with full OG and Twitter tags."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <title>My Blog - Understanding Python</title>
    <meta name="description" content="A blog about Python programming">
    <meta property="og:title" content="Understanding Python Decorators">
    <meta property="og:description" content="A deep dive into Python decorators and how they work">
    <meta property="og:image" content="/static/images/decorators.png">
    <meta property="og:url" content="https://myblog.com/posts/decorators">
    <meta property="og:type" content="article">
    <meta property="og:site_name" content="My Blog">
    <meta property="og:locale" content="en_US">
    <meta name="twitter:card" content="summary_large_image">
    <meta name="twitter:title" content="Twitter Title">
    <meta name="twitter:description" content="Twitter Desc">
    <meta name="twitter:image" content="https://myblog.com/twitter-img.png">
</head>
<body>
    <h1>Understanding Python Decorators</h1>
    <p>Decorators are a powerful feature in Python...</p>
    <a href="/posts/next">Next Post</a>
</body>
</html>"""

    def test_scraper_and_generator_together(self):
        """Scraper extracts content, generator creates preview from same HTML."""
        html = self._make_realistic_html()
        base_url = "https://myblog.com/posts/decorators"

        scraper = HTMLScraper()
        scraped = scraper.scrape(html, base_url)

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, base_url)

        # Scraper prefers <title> tag over og:title
        assert scraped.title == "My Blog - Understanding Python"
        assert scraped.word_count > 0
        assert len(scraped.links) > 0

        # Generator prefers og:title over <title> tag (different priority)
        assert preview.title == "Understanding Python Decorators"
        assert preview.description == "A deep dive into Python decorators and how they work"
        assert preview.image_url == "https://myblog.com/static/images/decorators.png"
        assert preview.type == "article"
        assert preview.site_name == "My Blog"
        assert preview.twitter_card == "summary_large_image"

    def test_generator_og_priority_differs_from_scraper(self):
        """Generator prefers og:title; scraper prefers <title> tag."""
        html = """<!DOCTYPE html>
        <html><head>
            <title>Generic Page Title</title>
            <meta property="og:title" content="Specific OG Title">
        </head><body><p>Content</p></body></html>"""

        scraper = HTMLScraper()
        scraped = scraper.scrape(html, "http://example.com")

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")

        # Scraper prefers <title> tag
        assert scraped.title == "Generic Page Title"
        # Generator prefers og:title — this is the key difference
        assert preview.title == "Specific OG Title"

    def test_generator_with_minimal_html(self):
        """Generator handles minimal HTML that scraper also handles."""
        html = "<html><head><title>Minimal</title></head><body><p>Hi</p></body></html>"

        scraper = HTMLScraper()
        scraped = scraper.scrape(html, "http://example.com")

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")

        assert scraped.title == "Minimal"
        assert preview.title == "Minimal"
        assert preview.description == ""

    def test_generator_with_no_metadata(self):
        """Generator returns empty preview for HTML with no metadata."""
        html = "<html><head></head><body><p>No metadata here</p></body></html>"

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "http://example.com")

        assert preview.title == ""
        assert preview.description == ""
        assert preview.image_url == ""

    def test_image_url_resolution_with_scraper_base_url(self):
        """Relative image URLs are resolved using the same base_url as scraper."""
        html = """<!DOCTYPE html>
        <html><head>
            <meta property="og:title" content="Test">
            <meta property="og:image" content="assets/logo.png">
        </head><body><p>Content</p></body></html>"""

        base_url = "https://example.com/page/"

        scraper = HTMLScraper()
        scraped = scraper.scrape(html, base_url)

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, base_url)

        assert scraped.url == base_url
        assert preview.image_url == "https://example.com/page/assets/logo.png"

    def test_full_pipeline_with_tables_and_links(self):
        """Full pipeline: scraper extracts tables/links, generator extracts preview."""
        html = """<!DOCTYPE html>
        <html><head>
            <title>Rich Page</title>
            <meta property="og:title" content="OG Rich Page">
            <meta property="og:description" content="A rich page with tables">
            <meta property="og:image" content="https://example.com/og.jpg">
        </head><body>
            <table><tr><th>Name</th><th>Value</th></tr><tr><td>A</td><td>1</td></tr></table>
            <a href="/link1">Link 1</a>
            <a href="/link2">Link 2</a>
        </body></html>"""

        config = ScraperConfig(extract_tables=True)
        scraper = HTMLScraper(config)
        scraped = scraper.scrape(html, "https://example.com")

        generator = LinkPreviewGenerator()
        preview = generator.generate(html, "https://example.com")

        # Scraper extracted tables and links
        assert len(scraped.tables) == 1
        assert len(scraped.links) == 2

        # Generator extracted preview
        assert preview.title == "OG Rich Page"
        assert preview.description == "A rich page with tables"
        assert preview.image_url == "https://example.com/og.jpg"

    def test_generator_handles_empty_string_like_scraper(self):
        """Both handle empty input gracefully."""
        scraper = HTMLScraper()
        scraped = scraper.scrape("", "http://example.com")
        assert scraped.title == ""

        generator = LinkPreviewGenerator()
        preview = generator.generate("", "http://example.com")
        assert preview.title == ""
