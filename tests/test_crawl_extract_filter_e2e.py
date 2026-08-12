"""End-to-end tests for crawl → extract → filter pipeline stages."""

from __future__ import annotations

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.scraper import HTMLScraper


class TestCrawlExtractFilterE2E:
    """Test the crawl → extract → filter pipeline end-to-end."""

    def test_extract_from_html(self):
        """Test HTML extraction produces usable content."""
        extractor = ContentExtractor()
        html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Python Web Development Guide</title>
            <meta name="description" content="A comprehensive guide to Python web development">
        </head>
        <body>
            <h1>Python Web Development</h1>
            <p>Python is a versatile programming language used for web development.</p>
            <p>Django and Flask are popular Python web frameworks.</p>
        </body>
        </html>
        """
        result = extractor.extract(html)
        assert result.title == "Python Web Development Guide"
        assert "Python" in result.text
        assert "web development" in result.text.lower()
        assert result.word_count > 10

    def test_extract_from_realistic_html(self):
        """Test extraction from realistic HTML with noise."""
        extractor = ContentExtractor()
        html = """
        <html>
        <head><title>Blog Post</title></head>
        <body>
            <nav><a href="/">Home</a><a href="/about">About</a></nav>
            <script>var x = 1;</script>
            <style>.hidden { display: none; }</style>
            <main>
                <h1>Real Blog Post</h1>
                <p>This is the actual content of the blog post about programming.</p>
                <p>It discusses various programming languages and frameworks.</p>
            </main>
            <footer>Copyright 2024</footer>
        </body>
        </html>
        """
        result = extractor.extract(html)
        assert "Real Blog Post" in result.text
        assert "programming" in result.text.lower()
        assert "var x = 1" not in result.text

    def test_filter_chain_with_extractor(self, tmp_path):
        """Test that extraction output feeds correctly into filter."""
        extractor = ContentExtractor()
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        html = """
        <html><head><title>Python Tutorial</title></head>
        <body><p>Python and Django are great for web development.</p></body></html>
        """
        extracted = extractor.extract(html)
        page = CrawledPage(
            url="https://example.com/python",
            title=extracted.title,
            content=extracted.text,
        )
        assert content_filter.should_include(page)

    def test_filter_rejects_unrelated_content(self, tmp_path):
        """Test that filter rejects content not matching interests."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        html = """
        <html><head><title>Cooking</title></head>
        <body><p>How to cook pasta with tomato sauce.</p></body></html>
        """
        extractor = ContentExtractor()
        extracted = extractor.extract(html)
        page = CrawledPage(
            url="https://example.com/cooking",
            title=extracted.title,
            content=extracted.text,
        )
        assert not content_filter.should_include(page)

    def test_scraper_basic(self):
        """Test HTMLScraper basic functionality."""
        scraper = HTMLScraper()
        html = "<html><body><p>Hello world</p></body></html>"
        result = scraper.scrape(html)
        assert result.title == ""  # No title tag
        assert "Hello world" in result.raw_text

    def test_scraper_with_title(self):
        """Test HTMLScraper extracts title."""
        scraper = HTMLScraper()
        html = "<html><head><title>My Page</title></head><body><p>Content</p></body></html>"
        result = scraper.scrape(html)
        assert result.title == "My Page"
        assert "Content" in result.raw_text

    def test_full_extract_filter_score_chain(self, tmp_path):
        """Test the full extract → filter → score chain."""
        from personal_index.content_scoring import ContentScorer

        # Setup
        extractor = ContentExtractor()
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django", "flask"]))
        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)
        scorer = ContentScorer()

        # Process HTML
        html = """
        <html><head><title>Python Web Frameworks</title></head>
        <body>
            <h1>Python Web Frameworks</h1>
            <p>Django and Flask are popular Python web frameworks.</p>
            <p>Python is widely used for web development.</p>
        </body></html>
        """

        # Extract
        extracted = extractor.extract(html)
        assert extracted.title == "Python Web Frameworks"

        # Build page
        page = CrawledPage(
            url="https://example.com/python-frameworks",
            title=extracted.title,
            content=extracted.text,
        )

        # Filter
        assert content_filter.should_include(page)

        # Score
        score_result = scorer.score_page(page, store)
        assert score_result.total > 0

    def test_pipeline_with_multiple_interests(self, tmp_path):
        """Test pipeline with multiple interests configured."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="web", keywords=["html", "css", "javascript"]))
        store.add(Interest(name="devops", keywords=["docker", "kubernetes", "ci/cd"]))

        filter_cfg = FilterConfig(min_content_length=10, require_interest_match=True)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)

        # Page matching python interest
        page1 = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )
        assert content_filter.should_include(page1)

        # Page matching web interest
        page2 = CrawledPage(
            url="https://example.com/web",
            title="Web Dev",
            content="HTML and CSS are fundamental web technologies.",
        )
        assert content_filter.should_include(page2)

        # Page matching no interest
        page3 = CrawledPage(
            url="https://example.com/other",
            title="Other",
            content="This content is about cooking recipes and gardening.",
        )
        assert not content_filter.should_include(page3)

    def test_extractor_handles_unicode(self):
        """Test that extractor handles unicode content."""
        extractor = ContentExtractor()
        html = "<html><body><p>日本語のコンテンツ</p><p>Émojis 🎉 and symbols ©</p></body></html>"
        result = extractor.extract(html)
        assert len(result.text) > 0

    def test_extractor_handles_empty_html(self):
        """Test that extractor handles empty HTML."""
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.title == ""
        assert result.text == ""
        assert result.word_count == 0

    def test_extractor_handles_malformed_html(self):
        """Test that extractor handles malformed HTML."""
        extractor = ContentExtractor()
        html = "<html><body><p>Unclosed paragraph<div>Mixed tags</body>"
        result = extractor.extract(html)
        assert len(result.text) > 0
