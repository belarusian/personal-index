"""Tests for the HTML scraper module."""

from personal_index.scraper import HTMLScraper, ScraperConfig


class TestScraperConfig:
    def test_default_config(self):
        config = ScraperConfig()
        assert config.extract_meta is True
        assert config.extract_links is True
        assert config.extract_images is True
        assert config.extract_headings is True
        assert config.extract_tables is False
        assert config.remove_scripts is True
        assert config.max_content_length == 1_000_000

    def test_custom_config(self):
        config = ScraperConfig(extract_tables=True, max_content_length=500)
        assert config.extract_tables is True
        assert config.max_content_length == 500


class TestHTMLScraper:
    def _make_html(self, body_content: str, title: str = "Test Page",
                   meta_desc: str = "", meta_keywords: str = "") -> str:
        meta = ""
        if meta_desc:
            meta += f'<meta name="description" content="{meta_desc}">'
        if meta_keywords:
            meta += f'<meta name="keywords" content="{meta_keywords}">'
        return f"""<!DOCTYPE html>
<html><head><title>{title}</title>{meta}</head>
<body>{body_content}</body></html>"""

    def test_basic_scrape(self):
        html = self._make_html("<p>Hello world</p>", "My Page", "A description")
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert result.title == "My Page"
        assert result.meta_description == "A description"
        assert "Hello world" in result.paragraphs

    def test_extract_headings(self):
        html = self._make_html("<h1>Main</h1><h2>Sub</h2><h3>Deep</h3>")
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert "h1: Main" in result.headings
        assert "h2: Sub" in result.headings
        assert "h3: Deep" in result.headings

    def test_extract_links(self):
        html = self._make_html('<a href="/page1">Link 1</a><a href="http://other.com">Link 2</a>')
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert len(result.links) == 2
        urls = [link["url"] for link in result.links]
        assert "http://example.com/page1" in urls
        assert "http://other.com" in urls

    def test_extract_images(self):
        html = self._make_html('<img src="/img.png" alt="Photo"><img src="missing">')
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert len(result.images) == 2
        assert result.images[0]["alt"] == "Photo"

    def test_extract_tables(self):
        html = self._make_html("<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>")
        config = ScraperConfig(extract_tables=True)
        scraper = HTMLScraper(config)
        result = scraper.scrape(html)
        assert len(result.tables) == 1
        assert result.tables[0]["rows"][0] == ["A", "B"]

    def test_scripts_removed(self):
        html = self._make_html("<script>alert('xss')</script><p>Safe</p>")
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert "xss" not in result.raw_text
        assert "Safe" in result.raw_text

    def test_duplicate_links_deduped(self):
        html = self._make_html('<a href="/same">A</a><a href="/same">B</a>')
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert len(result.links) == 1

    def test_word_count(self):
        html = self._make_html("<p>One two three four five</p>")
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert result.word_count == 5

    def test_empty_html(self):
        html = "<html><head></head><body></body></html>"
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert result.title == ""
        assert result.word_count == 0
        assert len(result.paragraphs) == 0

    def test_max_content_length(self):
        big_text = "word " * 10000
        html = self._make_html(f"<p>{big_text}</p>")
        config = ScraperConfig(max_content_length=100)
        scraper = HTMLScraper(config)
        result = scraper.scrape(html)
        assert len(result.raw_text) <= 100

    def test_charset_detection(self):
        html = '<html><head><meta charset="iso-8859-1"></head><body><p>Test</p></body></html>'
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert result.charset == "iso-8859-1"

    def test_og_tags_fallback(self):
        html = """<html><head>
        <meta property="og:title" content="OG Title">
        <meta property="og:description" content="OG Desc">
        </head><body><p>Content</p></body></html>"""
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert result.title == "OG Title"
        assert result.meta_description == "OG Desc"

    def test_link_text_extraction(self):
        html = self._make_html('<a href="/page" title="Tooltip">Click here</a>')
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert result.links[0]["text"] == "Click here"
        assert result.links[0]["title"] == "Tooltip"

    def test_image_dimensions(self):
        html = self._make_html('<img src="/pic.jpg" width="800" height="600">')
        scraper = HTMLScraper()
        result = scraper.scrape(html, "http://example.com")
        assert result.images[0]["width"] == "800"
        assert result.images[0]["height"] == "600"

    def test_multiple_paragraphs(self):
        html = self._make_html("<p>First</p><p>Second</p><p>Third</p>")
        scraper = HTMLScraper()
        result = scraper.scrape(html)
        assert len(result.paragraphs) == 3
