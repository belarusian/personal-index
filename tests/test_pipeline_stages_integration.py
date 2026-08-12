"""Integration tests for individual pipeline stages and their connections."""

from __future__ import annotations

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.tags import TagStore


class TestCrawlToExtract:
    """Test the crawl → extract stage connection."""

    def test_extractor_processes_html(self):
        """Test content extractor processes HTML correctly."""
        extractor = ContentExtractor()
        html = """
        <html><head><title>Test Page</title></head>
        <body><h1>Main Heading</h1><p>Paragraph content here.</p></body>
        </html>
        """
        result = extractor.extract(html)
        assert result.title == "Test Page"
        assert "Paragraph content" in result.text

    def test_extractor_handles_empty_html(self):
        """Test extractor handles empty input."""
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.title == ""
        assert result.text == ""

    def test_extractor_handles_minimal_html(self):
        """Test extractor with minimal HTML."""
        extractor = ContentExtractor()
        html = "<html><body><p>Hello world</p></body></html>"
        result = extractor.extract(html)
        assert "Hello world" in result.text


class TestExtractToFilter:
    """Test the extract → filter stage connection."""

    def test_filter_accepts_long_content(self):
        """Test filter accepts content above minimum length."""
        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="This is a sufficiently long piece of content for testing.",
        )
        filter_ = ContentFilter(config=FilterConfig(min_content_length=10))
        assert filter_.should_include(page) is True

    def test_filter_rejects_short_content(self):
        """Test filter rejects content below minimum length."""
        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="Short",
        )
        filter_ = ContentFilter(config=FilterConfig(min_content_length=50))
        assert filter_.should_include(page) is False

    def test_filter_rejects_short_title(self):
        """Test filter rejects pages with short titles."""
        page = CrawledPage(
            url="https://example.com/page",
            title="Hi",
            content="This is a sufficiently long piece of content for testing.",
        )
        filter_ = ContentFilter(config=FilterConfig(min_title_length=5))
        assert filter_.should_include(page) is False

    def test_filter_with_interest_match(self):
        """Test filter with interest matching enabled."""
        interest_store = InterestStore()
        interest_store.add(Interest(
            name="python", keywords=["python", "programming"]
        ))
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Learn Python programming.",
        )
        filter_ = ContentFilter(
            config=FilterConfig(
                min_content_length=10,
                require_interest_match=True,
            ),
            interest_store=interest_store,
        )
        assert filter_.should_include(page) is True

    def test_filter_blocks_domain(self):
        """Test filter blocks specified domains."""
        page = CrawledPage(
            url="https://spam.example.com/page",
            title="Spam",
            content="This is a sufficiently long piece of content for testing.",
        )
        filter_ = ContentFilter(
            config=FilterConfig(
                blocked_domains=["spam.example.com"],
            )
        )
        assert filter_.should_include(page) is False


class TestFilterToScore:
    """Test the filter → score stage connection."""

    def test_scorer_scores_page(self):
        """Test scorer produces valid score using score_page."""
        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="This is test content with some keywords.",
            word_count=8,
        )
        scorer = ContentScorer()
        result = scorer.score_page(page)
        assert 0.0 <= result.total <= 1.0

    def test_scorer_scores_empty_page(self):
        """Test scorer handles empty page."""
        page = CrawledPage(
            url="https://example.com/empty",
            title="",
            content="",
        )
        scorer = ContentScorer()
        result = scorer.score_page(page)
        assert result.total >= 0.0

    def test_scorer_with_custom_weights(self):
        """Test scorer with custom weights."""
        page = CrawledPage(
            url="https://example.com/page",
            title="Test",
            content="Content here.",
            word_count=3,
        )
        weights = ScoreWeights(relevance=0.5, quality=0.5)
        scorer = ContentScorer(weights=weights)
        result = scorer.score_page(page)
        assert result.total >= 0.0


class TestScoreToTag:
    """Test the score → tag stage connection."""

    def test_tagging_after_scoring(self, tmp_path):
        """Test tags are applied after scoring."""
        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Tutorial",
            content="Learn Python programming.",
            relevance_score=0.8,
        )
        # Simulate keyword extraction tagging
        tag_store.add_tag_to_page(page.url, "python")
        tag_store.add_tag_to_page(page.url, "tutorial")

        tags = tag_store.get_tags_for_page(page.url)
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "tutorial" in tag_names

    def test_tag_persistence(self, tmp_path):
        """Test tags persist after save."""
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        store1.add_tag_to_page("https://example.com", "test")
        store1._save()

        store2 = TagStore(store_path=path)
        tags = store2.get_tags_for_page("https://example.com")
        tag_names = [t.name for t in tags]
        assert "test" in tag_names


class TestTagToIndex:
    """Test the tag → index stage connection."""

    def test_index_with_tags(self, tmp_path):
        """Test indexing preserves page data."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/page",
            title="Test Page",
            content="Test content for indexing.",
            relevance_score=0.7,
        )
        index.add_page(page)
        assert index.get_page_count() == 1

        retrieved = index.get_page("https://example.com/page")
        assert retrieved is not None
        assert retrieved.title == "Test Page"

    def test_index_search_after_add(self, tmp_path):
        """Test search works immediately after adding."""
        index = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Guide",
            content="Learn Python programming.",
        )
        index.add_page(page)

        results = index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].title


class TestFullStageChain:
    """Test the complete chain: extract → filter → score → tag → index."""

    def test_full_chain(self, tmp_path):
        """Test all stages work together."""
        # Setup
        extractor = ContentExtractor()
        interest_store = InterestStore(
            store_path=str(tmp_path / "interests.json")
        )
        interest_store.add(Interest(name="tech", keywords=["programming"]))
        filter_ = ContentFilter(
            config=FilterConfig(min_content_length=10, require_interest_match=False),
            interest_store=interest_store,
        )
        scorer = ContentScorer()
        tag_store = TagStore(store_path=str(tmp_path / "tags.json"))
        index = SearchIndex(db_path=str(tmp_path / "index.json"))

        # Extract
        html = "<html><body><h1>Programming Guide</h1><p>Learn programming and coding skills.</p></body></html>"
        extracted = extractor.extract(html)

        # Create page from extraction
        page = CrawledPage(
            url="https://example.com/guide",
            title=extracted.title or "Programming Guide",
            content=extracted.text,
            word_count=extracted.word_count,
        )

        # Filter
        assert filter_.should_include(page) is True

        # Score
        score_result = scorer.score_page(page, interest_store=interest_store)
        page.relevance_score = score_result.total

        # Tag
        tag_store.add_tag_to_page(page.url, "programming")

        # Index
        index.add_page(page)

        # Verify
        assert index.get_page_count() == 1
        results = index.search("programming")
        assert len(results) == 1
