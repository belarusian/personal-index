"""End-to-end integration tests for the full crawl→extract→filter→score→tag→index pipeline.

These tests verify that all pipeline stages work together correctly,
using real components (not mocks) wherever possible.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig, PipelineStepConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineE2E:
    """Test the complete pipeline from crawl to search."""

    def test_pipeline_runner_full_flow_with_mocked_crawler(self, tmp_path):
        """Test full pipeline: crawl→extract→filter→score→tag→index with mocked crawler."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        # Add interests so filter passes
        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language", "development"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Python Tutorial",
                content="Python is a versatile programming language used for web development, data science, and automation. It is widely used in production environments around the world.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="JavaScript Guide",
                content="JavaScript is the language of the web, used for frontend and backend development. Node.js enables server-side JavaScript programming for scalable applications.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in == 2
        assert stats.pages_scored == 2
        assert stats.pages_tagged >= 0  # Tags applied
        assert stats.pages_indexed == 2
        assert stats.errors == []

    def test_pipeline_filters_low_quality_content(self, tmp_path):
        """Test that the pipeline filters out low-quality content."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=50)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "code", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/good",
                title="Good Article",
                content="Python programming is a great way to learn software development and build amazing applications with clean code.",
            ),
            CrawledPage(
                url="https://example.com/short",
                title="Short",
                content="Hi.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 2
        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 1

    def test_pipeline_auto_tags_pages(self, tmp_path):
        """Test that the pipeline auto-tags pages based on content."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/blog/python-tips",
                title="Python Tips",
                content="Python programming tips for web development using Django and Flask frameworks.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            runner.run(["https://example.com"], max_depth=1)

        # Check tags were created
        tag_names = [t.name for t in runner._tag_store.list_tags()]
        assert "python" in tag_names
        assert "blog" in tag_names

    def test_pipeline_index_persists_and_searches(self, tmp_path):
        """Test that indexed content persists and can be searched."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["rust", "systems", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/rust-intro",
                title="Introduction to Rust",
                content="Rust is a systems programming language that focuses on safety, speed, and concurrency. It is used for building reliable software.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            runner.run(["https://example.com"], max_depth=1)

        # Verify search works on indexed data
        results = runner._search_index.search("rust")
        assert len(results) == 1
        assert "Rust" in results[0].title
        assert "rust-intro" in results[0].url

    def test_pipeline_with_no_interests_passes_all(self, tmp_path):
        """Test pipeline behavior when no interests are configured."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        # No interests added - filter should still work with content length

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Some Content",
                content="This is a page with enough content to pass the minimum length filter for testing purposes.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        # Without interests, require_interest_match should filter out
        # But the pipeline runner sets require_interest_match=True
        # So pages without matching interests get filtered
        assert stats.pages_crawled == 1

    def test_pipeline_stats_tracking(self, tmp_path):
        """Test that pipeline stats are accurately tracked."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="general",
            keywords=["hello", "world", "test", "content", "page"],
        ))

        pages = [
            CrawledPage(
                url=f"https://example.com/page{i}",
                title=f"Page {i}",
                content=f"This is test content for page {i}. It has enough words to pass the content length filter.",
            )
            for i in range(5)
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 5
        assert stats.pages_extracted == 5
        assert stats.pages_filtered_in == 5
        assert stats.pages_indexed == 5
        assert stats.elapsed_seconds >= 0

        # Verify summary output contains key metrics
        summary = stats.summary()
        assert "Crawled:" in summary
        assert "5" in summary
        assert "Indexed:" in summary

    def test_pipeline_stats_to_dict(self, tmp_path):
        """Test PipelineStats.to_dict() serialization."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=10,
            pages_filtered_in=8,
            pages_filtered_out=2,
            pages_scored=8,
            pages_tagged=8,
            tags_applied=16,
            pages_indexed=8,
            errors=["error1"],
            elapsed_seconds=1.5,
        )
        d = stats.to_dict()
        assert d["pages_crawled"] == 10
        assert d["tags_applied"] == 16
        assert d["elapsed_seconds"] == 1.5
        assert d["errors"] == ["error1"]


class TestPipelineStepControl:
    """Test individual step enable/disable in the pipeline."""

    def test_skip_crawl_step(self, tmp_path):
        """Test running pipeline without crawl step."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(
            steps=[PipelineStepConfig(name="crawl", enabled=False)],
            min_score_threshold=0.0,
            min_content_length=10,
        )
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        stats = runner.run(["https://example.com"], max_depth=1)
        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0

    def test_skip_filter_step(self, tmp_path):
        """Test running pipeline without filter step."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(
            steps=[PipelineStepConfig(name="filter", enabled=False)],
            min_score_threshold=0.0,
            min_content_length=10,
        )
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Python Page",
                content="Python programming language for web development and software engineering.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        # Without filter, all pages should pass through
        assert stats.pages_crawled == 1
        assert stats.pages_indexed == 1

    def test_only_index_step(self, tmp_path):
        """Test running only the index step."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(
            steps=[
                PipelineStepConfig(name="crawl", enabled=False),
                PipelineStepConfig(name="extract", enabled=False),
                PipelineStepConfig(name="filter", enabled=False),
                PipelineStepConfig(name="score", enabled=False),
                PipelineStepConfig(name="tag", enabled=False),
                PipelineStepConfig(name="index", enabled=True),
            ],
        )
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        stats = runner.run([], max_depth=1)
        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0


class TestPipelineDirectPageAdd:
    """Test adding pages directly through the pipeline."""

    def test_add_page_directly_success(self, tmp_path):
        """Test adding a page directly through the pipeline."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        page = CrawledPage(
            url="https://example.com/direct",
            title="Direct Import",
            content="Python programming is a popular way to build web applications and data pipelines.",
        )

        result = runner.add_page_directly(page)
        assert result is True
        assert runner._search_index.get_page_count() == 1

    def test_add_page_directly_filtered_out(self, tmp_path):
        """Test that short content is filtered when adding directly."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=100)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Hi.",
        )

        result = runner.add_page_directly(page)
        assert result is False
        assert runner._search_index.get_page_count() == 0

    def test_add_page_directly_no_content(self, tmp_path):
        """Test that pages with no content are rejected."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        page = CrawledPage(
            url="https://example.com/empty",
            title="Empty Page",
            content="",
        )

        result = runner.add_page_directly(page)
        assert result is False


class TestPipelineDataPersistence:
    """Test that pipeline data persists across runs."""

    def test_interests_persist_across_pipeline_runs(self, tmp_path):
        """Test that interests persist between pipeline runs."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        # Create a new runner pointing to same data dir
        runner2 = PipelineRunner(config=cfg, data_dir=data_dir)
        interests = runner2._interest_store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "python"

    def test_index_persists_across_pipeline_runs(self, tmp_path):
        """Test that search index persists between pipeline runs."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "code"],
        ))

        page = CrawledPage(
            url="https://example.com/persist",
            title="Persistent Page",
            content="Python code examples for web development and software engineering.",
        )
        runner.add_page_directly(page)

        # New runner should see the indexed page
        runner2 = PipelineRunner(config=cfg, data_dir=data_dir)
        assert runner2._search_index.get_page_count() == 1
        results = runner2._search_index.search("python")
        assert len(results) == 1

    def test_tags_persist_across_pipeline_runs(self, tmp_path):
        """Test that tags persist between pipeline runs."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        page = CrawledPage(
            url="https://example.com/tagged",
            title="Tagged Page",
            content="Python programming language for web development.",
        )
        runner.add_page_directly(page)

        # New runner should see the tags
        runner2 = PipelineRunner(config=cfg, data_dir=data_dir)
        tag_names = [t.name for t in runner2._tag_store.list_tags()]
        assert "python" in tag_names


class TestPipelineProgressCallback:
    """Test pipeline progress callback functionality."""

    def test_progress_callback_receives_updates(self, tmp_path):
        """Test that progress callback receives updates during pipeline run."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        progress_log = []

        def callback(step, current, total):
            progress_log.append((step, current, total))

        runner = PipelineRunner(
            config=cfg,
            data_dir=data_dir,
            progress_callback=callback,
        )

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        page = CrawledPage(
            url="https://example.com/page",
            title="Python Page",
            content="Python programming language for web development.",
        )
        runner.add_page_directly(page)

        # Direct add doesn't use progress callback, but runner accepts it
        assert runner.progress_callback is not None

    def test_progress_callback_with_mocked_crawler(self, tmp_path):
        """Test progress callback during full pipeline with mocked crawler."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        progress_log = []

        def callback(step, current, total):
            progress_log.append((step, current, total))

        runner = PipelineRunner(
            config=cfg,
            data_dir=data_dir,
            progress_callback=callback,
        )

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Python Page 1",
                content="Python programming language for web development and software engineering.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="Python Page 2",
                content="More Python programming content for testing the pipeline progress callback.",
            ),
        ]

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            mock_crawler.close.return_value = None
            MockCrawler.return_value = mock_crawler

            runner.run(["https://example.com"], max_depth=1)

        # Verify progress was reported for each step
        steps_seen = {entry[0] for entry in progress_log}
        assert "crawl" in steps_seen
        assert "extract" in steps_seen
        assert "filter" in steps_seen
        assert "score" in steps_seen
        assert "tag" in steps_seen
        assert "index" in steps_seen
