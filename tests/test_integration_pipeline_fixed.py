"""Fixed integration pipeline tests - previously skipped due to test isolation issues.

These tests verify the full pipeline: crawl → extract → filter → score → tag → index.
"""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineRunnerDirect:
    """Test pipeline runner with direct page addition (no network needed)."""

    def test_add_page_directly_indexes_and_searches(self, tmp_path):
        """Test that add_page_directly indexes content and makes it searchable."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language"],
        ))

        page = CrawledPage(
            url="https://example.com/python-tutorial",
            title="Python Programming Tutorial",
            content=(
                "Python is a versatile programming language used for web development, "
                "data science, and automation. It is widely used in production environments "
                "around the world for building robust applications."
            ),
        )

        result = runner.add_page_directly(page)
        assert result is True

        results = runner._search_index.search("python")
        assert len(results) == 1
        assert "Python Programming Tutorial" in results[0].title

        page_tags = runner._tag_store.get_tags_for_page(page.url)
        assert len(page_tags) > 0
        runner.close()

    def test_add_page_directly_filters_low_score(self, tmp_path):
        """Test that pages below score threshold are rejected."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.8, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="cooking",
            keywords=["recipe", "cooking", "baking"],
        ))

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content=(
                "Python is a programming language used for software development. "
                "It is great for building web applications and data analysis tools."
            ),
        )

        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_add_page_directly_filters_short_content(self, tmp_path):
        """Test that pages with too little content are rejected."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=50)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(name="tech", keywords=["python"]))

        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short.",
        )

        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_add_multiple_pages_directly(self, tmp_path):
        """Test adding multiple pages and searching across them."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="webdev",
            keywords=["python", "javascript", "web", "development", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-web",
                title="Python Web Development",
                content=(
                    "Python is excellent for web development with frameworks like Django "
                    "and Flask. Many developers choose Python for backend web services."
                ),
            ),
            CrawledPage(
                url="https://example.com/js-frontend",
                title="JavaScript Frontend Development",
                content=(
                    "JavaScript is the primary language for frontend web development. "
                    "React, Vue, and Angular are popular JavaScript frameworks."
                ),
            ),
            CrawledPage(
                url="https://example.com/irrelevant",
                title="Gardening Tips",
                content=(
                    "How to grow tomatoes in your backyard garden. Tips for soil preparation "
                    "and watering schedules for optimal tomato growth."
                ),
            ),
        ]

        indexed = 0
        for page in pages:
            if runner.add_page_directly(page):
                indexed += 1

        assert indexed >= 2  # At least the two web dev pages

        results = runner._search_index.search("web development")
        assert len(results) >= 1

        runner.close()


class TestFullPipelineWithMockedCrawler:
    """Test the full pipeline with a mocked crawler."""

    def test_full_pipeline_all_six_steps(self, tmp_path):
        """Test crawl → extract → filter → score → tag → index with mocked crawler."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language", "development"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Python Tutorial",
                content="Python is a versatile programming language used for web development, data science, and automation. It is widely used in production.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="JavaScript Guide",
                content="JavaScript is the language of the web, used for frontend and backend development. Node.js enables server-side JavaScript.",
            ),
        ]

        with patch.object(runner, '_crawler') as mock_crawler:
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in == 2
        assert stats.pages_indexed == 2
        runner.close()

    def test_pipeline_filters_by_score_threshold(self, tmp_path):
        """Test that pipeline respects score threshold."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.5, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/relevant",
                title="Python Django Tutorial",
                content="Python and Django are great for web development. Python is a versatile programming language.",
            ),
            CrawledPage(
                url="https://example.com/irrelevant",
                title="Cooking Recipes",
                content="How to make pasta with tomato sauce and fresh basil.",
            ),
        ]

        with patch.object(runner, '_crawler') as mock_crawler:
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            stats = runner.run(["https://example.com"], max_depth=1)

        # At least the relevant page should be indexed
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_stats_tracking(self, tmp_path):
        """Test that pipeline stats are accurately tracked."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "code", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Page One",
                content="Python programming language for software development.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="Page Two",
                content="More about Python and programming best practices.",
            ),
            CrawledPage(
                url="https://example.com/page3",
                title="Page Three",
                content="Advanced Python techniques for professional developers.",
            ),
        ]

        with patch.object(runner, '_crawler') as mock_crawler:
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 3
        assert stats.pages_extracted == 3
        assert stats.pages_filtered_in == 3
        assert stats.pages_scored == 3
        assert stats.pages_indexed == 3
        assert stats.elapsed_seconds >= 0
        runner.close()


class TestPipelineFromFiles:
    """Test pipeline with file imports (no network)."""

    def test_run_from_files_basic(self, tmp_path):
        """Test importing and processing local files."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming", "development"],
        ))

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text("Python is a great programming language for web development.")
        file2 = tmp_path / "article2.txt"
        file2.write_text("JavaScript is used for frontend development and Node.js backend.")

        stats = runner.run_from_files([str(file1), str(file2)])

        assert stats.pages_indexed >= 1
        assert stats.errors == []
        runner.close()

    def test_run_from_files_with_html(self, tmp_path):
        """Test importing HTML files."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="webdev",
            keywords=["python", "web", "development"],
        ))

        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Python Web Dev</title></head>"
            "<body><p>Python is excellent for web development with Django and Flask.</p></body></html>"
        )

        stats = runner.run_from_files([str(html_file)])

        assert stats.pages_indexed >= 1
        runner.close()

    def test_run_from_files_empty_file(self, tmp_path):
        """Test that empty files are handled gracefully."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(name="tech", keywords=["python"]))

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        stats = runner.run_from_files([str(empty_file)])

        assert stats.pages_indexed == 0
        runner.close()

    def test_run_from_files_nonexistent(self, tmp_path):
        """Test that nonexistent files produce errors."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(name="tech", keywords=["python"]))

        stats = runner.run_from_files([str(tmp_path / "nonexistent.txt")])

        assert len(stats.errors) > 0
        runner.close()
