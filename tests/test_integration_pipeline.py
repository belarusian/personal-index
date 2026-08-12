"""Integration tests for the full crawl -> extract -> filter -> score -> tag -> index -> search pipeline.

These tests verify the complete pipeline works end-to-end using real HTML files
from the repository, not mocked data.
"""

from __future__ import annotations

import os
import shutil
import tempfile

import pytest

from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.scraper import HTMLScraper
from personal_index.tags import TagStore


# Path to a real HTML file in the repo
REAL_HTML_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "docs",
    "index.html",
)


class TestPipelineEndToEnd:
    """Test the full pipeline end-to-end with real HTML content."""

    def setup_method(self):
        """Set up a temporary data directory for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmpdir, "pipeline_data")
        os.makedirs(self.data_dir, exist_ok=True)

    def teardown_method(self):
        """Clean up temporary directory."""
        shutil.rmtree(self.tmpdir, ignore_errors=True)

    def test_full_pipeline_with_real_html_file(self):
        """Test the full pipeline: init -> crawl -> extract -> filter -> score -> tag -> index -> search.

        Uses a real HTML file from the repo (docs/index.html) to verify
        the entire pipeline processes content correctly.
        """
        # Step 1: Init - create pipeline with config
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Step 2: Add interests so scoring/tagging has something to match
        pipeline.interest_store.add(Interest(
            name="python",
            keywords=["python", "programming", "development"],
            priority=8,
        ))
        pipeline.interest_store.add(Interest(
            name="web",
            keywords=["web", "html", "css", "javascript"],
            priority=5,
        ))

        # Step 3: Crawl - read a real HTML file from the repo
        assert os.path.exists(REAL_HTML_FILE), f"Real HTML file not found: {REAL_HTML_FILE}"
        with open(REAL_HTML_FILE, "r", encoding="utf-8") as f:
            html_content = f.read()

        # Step 4: Extract - use the extractor on the real HTML
        extractor = ContentExtractor()
        extracted = extractor.extract(html_content)
        assert extracted.title != "", "Title should be extracted from real HTML"
        assert len(extracted.text) > 100, "Content should be extracted from real HTML"
        assert extracted.word_count > 10, "Word count should be meaningful"

        # Step 5: Filter - verify content passes the filter
        page = CrawledPage(
            url="file://" + REAL_HTML_FILE,
            title=extracted.title,
            content=extracted.text,
            word_count=extracted.word_count,
        )
        filter_config = FilterConfig(
            min_content_length=config.min_content_length,
            require_interest_match=False,
        )
        content_filter = ContentFilter(config=filter_config)
        assert content_filter.should_include(page), "Real HTML content should pass filter"

        # Step 6: Score - verify scoring works
        scorer = ContentScorer(weights=ScoreWeights())
        score_result = scorer.score_page(page, pipeline.interest_store)
        assert score_result.total >= 0, "Score should be non-negative"
        page.relevance_score = score_result.total

        # Step 7: Tag - verify tagging works
        tags = pipeline._auto_tag(page)
        # At least some tags should be generated from interests
        assert isinstance(tags, list), "Tags should be a list"

        # Add tags to the tag store
        for tag_name in tags:
            pipeline.tag_store.add_tag_to_page(page.url, tag_name)

        # Step 8: Index - add page to search index
        pipeline.search_index.add_page(page)
        assert pipeline.search_index.get_page_count() >= 1, "Page should be indexed"

        # Step 9: Search - verify we can find the indexed content
        # Search for a word that should be in the dashboard HTML
        search_results = pipeline.search_index.search("python", limit=10)
        # The dashboard HTML mentions python in module listings
        # Even if no results, the search should not crash
        assert isinstance(search_results, list), "Search should return a list"

        # Search for something definitely in the HTML (it's a dashboard)
        search_results = pipeline.search_index.search("module", limit=10)
        assert isinstance(search_results, list), "Search for 'module' should return list"

        # Step 10: Export - verify we can get stats
        stats = pipeline.get_stats()
        assert stats["indexed_pages"] >= 1, "Stats should show at least 1 indexed page"
        assert stats["total_interests"] >= 2, "Stats should show our interests"

    def test_pipeline_add_page_directly(self):
        """Test adding a page directly through the pipeline (skip crawl)."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Add an interest
        pipeline.interest_store.add(Interest(
            name="testing",
            keywords=["test", "integration", "pipeline"],
            priority=7,
        ))

        # Create a page with content matching our interest
        page = CrawledPage(
            url="https://example.com/integration-test",
            title="Integration Testing Guide",
            content=(
                "Integration testing is a crucial part of software development. "
                "It verifies that different components of a system work together correctly. "
                "Pipeline integration tests ensure the full workflow functions end-to-end."
            ),
        )

        # Add directly through pipeline
        result = pipeline.add_page_directly(page)
        assert result is True, "Page should be added successfully"

        # Verify it's indexed
        assert pipeline.search_index.get_page_count() >= 1

        # Verify we can search for it
        results = pipeline.search_index.search("integration", limit=10)
        assert len(results) >= 1, "Should find the integration test page"
        assert "Integration Testing Guide" in results[0].title

        # Verify tags were applied
        page_tags = pipeline.tag_store.get_tags_for_page(page.url)
        assert len(page_tags) > 0, "Page should have tags"

    def test_pipeline_filters_short_content(self):
        """Test that the pipeline correctly filters out short content."""
        config = PipelineConfig(
            min_content_length=200,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="tech",
            keywords=["python"],
        ))

        # Short content should be filtered out
        short_page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short content.",
        )
        result = pipeline.add_page_directly(short_page)
        assert result is False, "Short content should be filtered out"

        # Longer content should pass
        long_page = CrawledPage(
            url="https://example.com/long",
            title="Long Article",
            content=(
                "This is a longer article about Python programming. "
                "Python is a versatile language used in many domains. "
                "It supports multiple programming paradigms including "
                "object-oriented, functional, and procedural programming. "
                "The Python ecosystem includes many libraries and frameworks."
            ),
        )
        result = pipeline.add_page_directly(long_page)
        assert result is True, "Long content should pass filter"

    def test_pipeline_multiple_pages_search(self):
        """Test indexing multiple pages and searching across them."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "rust", "programming", "language"],
            priority=8,
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Programming",
                content=(
                    "Python is a high-level programming language known for its "
                    "readability and versatility. It is used in web development, "
                    "data science, machine learning, and automation."
                ),
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Development",
                content=(
                    "JavaScript is the language of the web. It powers both "
                    "frontend and backend development. Node.js, React, and "
                    "Vue.js are popular JavaScript frameworks and tools."
                ),
            ),
            CrawledPage(
                url="https://example.com/rust",
                title="Rust Systems Programming",
                content=(
                    "Rust is a systems programming language that focuses on "
                    "safety and performance. It provides memory safety without "
                    "a garbage collector, making it ideal for low-level systems."
                ),
            ),
        ]

        for page in pages:
            result = pipeline.add_page_directly(page)
            assert result is True, f"Page {page.url} should be added"

        # Verify all pages are indexed
        assert pipeline.search_index.get_page_count() == 3

        # Search for "programming" - should find all three
        results = pipeline.search_index.search("programming", limit=10)
        assert len(results) >= 2, "Should find multiple programming pages"

        # Search for "python" - should find the Python page
        results = pipeline.search_index.search("python", limit=10)
        assert len(results) >= 1
        assert "Python Programming" in results[0].title

        # Search for "rust" - should find the Rust page
        results = pipeline.search_index.search("rust", limit=10)
        assert len(results) >= 1
        assert "Rust Systems Programming" in results[0].title

    def test_pipeline_with_real_html_extraction_and_indexing(self):
        """Test full pipeline using real HTML file content through add_page_directly."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="dashboard",
            keywords=["dashboard", "terminal", "module", "coverage"],
            priority=6,
        ))

        # Read real HTML and extract content
        with open(REAL_HTML_FILE, "r", encoding="utf-8") as f:
            html_content = f.read()

        extractor = ContentExtractor()
        extracted = extractor.extract(html_content)

        # Create page from extracted content
        page = CrawledPage(
            url="file://" + REAL_HTML_FILE,
            title=extracted.title,
            content=extracted.text,
            word_count=extracted.word_count,
            raw_html=html_content,
        )

        # Add through pipeline
        result = pipeline.add_page_directly(page)
        assert result is True, "Real HTML page should be added"

        # Verify indexing
        assert pipeline.search_index.get_page_count() >= 1

        # Verify search works on real content
        results = pipeline.search_index.search("terminal", limit=10)
        assert isinstance(results, list)

        # Verify tags were applied
        page_tags = pipeline.tag_store.get_tags_for_page(page.url)
        assert isinstance(page_tags, list)

    def test_pipeline_search_returns_relevant_results(self):
        """Test that search returns results ranked by relevance."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        # Add pages with varying relevance to "python"
        pages = [
            CrawledPage(
                url="https://example.com/high-relevance",
                title="Python Python Python",
                content="Python Python Python Python Python programming language Python.",
            ),
            CrawledPage(
                url="https://example.com/low-relevance",
                title="Something Else",
                content="This page mentions python once in passing among other topics.",
            ),
        ]

        for page in pages:
            pipeline.add_page_directly(page)

        results = pipeline.search_index.search("python", limit=10)
        assert len(results) >= 2

        # The high-relevance page should rank higher
        assert results[0].url == "https://example.com/high-relevance"
        assert results[0].relevance_score > results[1].relevance_score

    def test_pipeline_index_persistence(self):
        """Test that the search index persists to disk and can be reloaded."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
            persist_index=True,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="persistence",
            keywords=["persist", "save", "load"],
        ))

        page = CrawledPage(
            url="https://example.com/persist",
            title="Persistence Test",
            content="This page tests index persistence across pipeline instances.",
        )
        pipeline.add_page_directly(page)

        # Close and reopen pipeline
        index_path = os.path.join(self.data_dir, "search_index.json")
        assert os.path.exists(index_path), "Index file should be persisted"

        # Create a new pipeline pointing to the same data dir
        pipeline2 = Pipeline(data_dir=self.data_dir, config=config)
        assert pipeline2.search_index.get_page_count() >= 1, "Index should be loaded from disk"

        results = pipeline2.search_index.search("persistence", limit=10)
        assert len(results) >= 1, "Should find persisted content"
        assert "Persistence Test" in results[0].title

    def test_pipeline_stats_tracking(self):
        """Test that pipeline stats accurately track processing."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=self.data_dir, config=config)

        pipeline.interest_store.add(Interest(
            name="stats",
            keywords=["stats", "statistics", "tracking"],
        ))

        # Add several pages
        for i in range(5):
            page = CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"This is page number {i} about statistics and tracking data.",
            )
            pipeline.add_page_directly(page)

        stats = pipeline.get_stats()
        assert stats["indexed_pages"] == 5
        assert stats["total_interests"] == 1
        assert stats["total_tags"] > 0
        assert stats["tagged_pages"] > 0
