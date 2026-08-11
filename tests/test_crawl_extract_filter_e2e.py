"""End-to-end tests for crawl → extract → filter chain.

Tests each pipeline stage individually and in combination.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.scraper import HTMLScraper, ScrapedContent, ScraperConfig
from personal_index.tags import TagStore


class TestExtractStep:
    """Test the extract step of the pipeline."""

    def test_extract_html_content(self):
        extractor = ContentExtractor()
        html = """
        <html><head><title>Python Guide</title>
        <meta name="description" content="Learn Python programming"></head>
        <body><h1>Python Programming Guide</h1>
        <p>Python is a versatile programming language.</p>
        <p>It is used for web development, data science, and AI.</p></body></html>
        """
        result = extractor.extract(html)
        assert "Python Guide" in result.title
        assert "Python is a versatile" in result.text
        assert result.word_count > 10

    def test_extract_empty_html(self):
        extractor = ContentExtractor()
        result = extractor.extract("")
        assert result.title == ""
        assert result.text == ""
        assert result.word_count == 0

    def test_extract_with_meta_tags(self):
        extractor = ContentExtractor()
        html = """
        <html><head>
        <title>Test Page</title>
        <meta name="description" content="A test page">
        <meta name="keywords" content="test, example, demo">
        <meta name="author" content="Test Author">
        </head><body><p>Content here.</p></body></html>
        """
        result = extractor.extract(html)
        assert result.title == "Test Page"
        assert result.meta_description == "A test page"
        assert result.author == "Test Author"

    def test_extract_strips_scripts(self):
        extractor = ContentExtractor()
        html = """
        <html><body>
        <p>Real content.</p>
        <script>alert('malicious');</script>
        <p>More real content.</p>
        </body></html>
        """
        result = extractor.extract(html)
        assert "malicious" not in result.text
        assert "Real content" in result.text

    def test_extract_word_count(self):
        extractor = ContentExtractor()
        html = "<html><body><p>One two three four five.</p></body></html>"
        result = extractor.extract(html)
        assert result.word_count == 5


class TestFilterStep:
    """Test the filter step of the pipeline."""

    def test_filter_includes_good_content(self):
        config = FilterConfig(min_content_length=10)
        filter_ = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/good",
            title="Good Article",
            content="This is a good article with enough content to pass the filter.",
        )
        assert filter_.should_include(page) is True

    def test_filter_excludes_short_content(self):
        config = FilterConfig(min_content_length=100)
        filter_ = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short.",
        )
        assert filter_.should_include(page) is False

    def test_filter_excludes_blocked_domain(self):
        config = FilterConfig(blocked_domains=["spam.com"])
        filter_ = ContentFilter(config=config)
        page = CrawledPage(
            url="https://spam.com/page",
            title="Spam",
            content="This is spam content that should be filtered out completely.",
        )
        assert filter_.should_include(page) is False

    def test_filter_with_interest_match(self):
        store = InterestStore()
        store.add(Interest(name="python", keywords=["python"]))
        config = FilterConfig(require_interest_match=True, min_content_length=10)
        filter_ = ContentFilter(config=config, interest_store=store)

        matching = CrawledPage(
            url="https://example.com/python",
            title="Python",
            content="Python programming language.",
        )
        non_matching = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking",
            content="How to cook pasta.",
        )
        assert filter_.should_include(matching) is True
        assert filter_.should_include(non_matching) is False

    def test_filter_get_reasons(self):
        config = FilterConfig(min_content_length=100)
        filter_ = ContentFilter(config=config)
        page = CrawledPage(
            url="https://example.com/short",
            title="X",
            content="Short",
        )
        reasons = filter_.get_filter_reasons(page)
        assert len(reasons) > 0


class TestScoreStep:
    """Test the scoring step of the pipeline."""

    def test_scorer_basic(self):
        scorer = ContentScorer()
        score = scorer.score(
            keyword_matches=3,
            total_keywords=5,
            word_count=500,
            domain_authority=0.8,
        )
        assert 0 <= score.total <= 1.0

    def test_scorer_no_matches(self):
        scorer = ContentScorer()
        score = scorer.score(
            keyword_matches=0,
            total_keywords=10,
            word_count=100,
        )
        assert score.total < 0.5

    def test_scorer_high_relevance(self):
        scorer = ContentScorer()
        score = scorer.score(
            keyword_matches=10,
            total_keywords=10,
            word_count=1000,
            domain_authority=1.0,
        )
        assert score.total > 0.5

    def test_scorer_with_weights(self):
        weights = ScoreWeights(relevance=0.5, quality=0.3)
        scorer = ContentScorer(weights=weights)
        score = scorer.score(
            keyword_matches=5,
            total_keywords=5,
            word_count=500,
        )
        assert 0 <= score.total <= 1.0

    def test_score_page_integration(self):
        scorer = ContentScorer()
        store = InterestStore()
        store.add(Interest(name="python", keywords=["python", "programming"]))

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python programming language for web development.",
        )
        score = scorer.score_page(page, store)
        assert score.total > 0
        assert score.relevance > 0


class TestTagStep:
    """Test the tagging step of the pipeline."""

    def test_tag_store_add_and_retrieve(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.add_tag_to_page("https://example.com/page", "python")
        tags = store.get_tags_for_page("https://example.com/page")
        assert len(tags) == 1
        assert tags[0].name == "python"

    def test_tag_store_multiple_tags(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.add_tag_to_page("https://example.com/page", "python")
        store.add_tag_to_page("https://example.com/page", "blog")
        tags = store.get_tags_for_page("https://example.com/page")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "blog" in tag_names

    def test_tag_store_persistence(self, tmp_path):
        path = str(tmp_path / "tags.json")
        store1 = TagStore(store_path=path)
        store1.add_tag_to_page("https://example.com/page", "python")

        store2 = TagStore(store_path=path)
        tags = store2.get_tags_for_page("https://example.com/page")
        assert len(tags) == 1

    def test_tag_store_list_all_tags(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.add_tag_to_page("https://example.com/p1", "python")
        store.add_tag_to_page("https://example.com/p2", "javascript")
        store.add_tag_to_page("https://example.com/p1", "blog")
        tags = store.list_tags()
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "javascript" in tag_names
        assert "blog" in tag_names

    def test_tag_store_get_pages_for_tag(self, tmp_path):
        store = TagStore(store_path=str(tmp_path / "tags.json"))
        store.add_tag_to_page("https://example.com/p1", "python")
        store.add_tag_to_page("https://example.com/p2", "python")
        store.add_tag_to_page("https://example.com/p3", "javascript")
        pages = store.get_pages_for_tag("python")
        assert "https://example.com/p1" in pages
        assert "https://example.com/p2" in pages
        assert "https://example.com/p3" not in pages


class TestIndexStep:
    """Test the indexing step of the pipeline."""

    def test_index_add_and_search(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "index.json"))
        page = CrawledPage(
            url="https://example.com/page",
            title="Python Guide",
            content="Python programming language.",
        )
        idx.add_page(page)
        results = idx.search("python")
        assert len(results) == 1

    def test_index_persistence(self, tmp_path):
        path = str(tmp_path / "index.json")
        idx1 = SearchIndex(db_path=path)
        idx1.add_page(CrawledPage(
            url="https://example.com/page",
            title="Test",
            content="Test content.",
        ))

        idx2 = SearchIndex(db_path=path)
        assert idx2.get_page_count() == 1

    def test_index_remove(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "index.json"))
        idx.add_page(CrawledPage(
            url="https://example.com/page",
            title="Test",
            content="Test content.",
        ))
        assert idx.get_page_count() == 1
        idx.remove_page("https://example.com/page")
        assert idx.get_page_count() == 0

    def test_index_multiple_pages(self, tmp_path):
        idx = SearchIndex(db_path=str(tmp_path / "index.json"))
        for i in range(5):
            idx.add_page(CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"Content for page {i} about programming.",
            ))
        assert idx.get_page_count() == 5
        results = idx.search("programming")
        assert len(results) == 5


class TestCrawlExtractFilterChain:
    """Test the crawl → extract → filter chain together."""

    def test_chain_with_html(self, tmp_path):
        """Test: raw HTML → extract → filter → score → tag → index."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        pipe.interest_store.add(Interest(name="python", keywords=["python"]))

        html = """
        <html><head><title>Python Tutorial</title></head>
        <body><h1>Learn Python</h1>
        <p>Python is a great programming language for web development and software engineering.</p>
        <p>It supports multiple programming paradigms including object-oriented and functional programming.</p>
        <p>Python is widely used in data science, machine learning, and automation.</p></body></html>
        """
        page = CrawledPage(
            url="https://example.com/python-tutorial",
            title="",
            content=html,
            raw_html=html,
        )
        result = pipe.add_page_directly(page)
        assert result is True

        # Verify search works
        results = pipe.search("python")
        assert len(results) >= 1

    def test_chain_filters_bad_content(self, tmp_path):
        """Test chain properly filters out bad content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=50,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        # Good page
        good = CrawledPage(
            url="https://example.com/good",
            title="Good",
            content="This is a good article with enough content to pass the filter check.",
        )
        assert pipe.add_page_directly(good) is True

        # Bad page (too short)
        bad = CrawledPage(
            url="https://example.com/bad",
            title="Bad",
            content="Short.",
        )
        assert pipe.add_page_directly(bad) is False

        assert pipe.search_index.get_page_count() == 1

    def test_chain_with_multiple_interests(self, tmp_path):
        """Test chain with multiple interests and auto-tagging."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
            require_interest_match=False,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)
        pipe.interest_store.add(Interest(name="python", keywords=["python"]))
        pipe.interest_store.add(Interest(name="javascript", keywords=["javascript"]))

        pages = [
            CrawledPage(
                url="https://example.com/blog/python",
                title="Python",
                content="Python programming language.",
            ),
            CrawledPage(
                url="https://example.com/blog/javascript",
                title="JavaScript",
                content="JavaScript for web development.",
            ),
        ]
        for page in pages:
            pipe.add_page_directly(page)

        # Both should be indexed
        assert pipe.search_index.get_page_count() == 2

        # Check tags
        python_tags = pipe.tag_store.get_tags_for_page("https://example.com/blog/python")
        python_tag_names = [t.name for t in python_tags]
        assert "python" in python_tag_names
        assert "blog" in python_tag_names
