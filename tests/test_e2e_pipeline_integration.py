"""End-to-end pipeline integration tests.

These tests verify the complete crawl → extract → filter → score → tag → index
pipeline works correctly from CLI and programmatic interfaces.
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
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineRunnerBasic:
    """Test PipelineRunner with mocked crawler."""

    def test_pipeline_runner_initialization(self, tmp_path):
        """PipelineRunner initializes all components correctly."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        assert runner.data_dir == data_dir
        assert runner._interest_store is not None
        assert runner._tag_store is not None
        assert runner._search_index is not None
        assert runner._filter is not None
        assert runner._scorer is not None
        runner.close()

    def test_pipeline_runner_creates_data_dirs(self, tmp_path):
        """PipelineRunner creates required subdirectories."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))
        runner.close()

    def test_pipeline_runner_with_custom_config(self, tmp_path):
        """PipelineRunner respects custom PipelineConfig."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_score_threshold=0.5,
            min_content_length=50,
            max_depth=2,
            max_pages=50,
        )
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        assert runner.pipeline_config.min_score_threshold == 0.5
        assert runner.pipeline_config.min_content_length == 50
        assert runner.pipeline_config.max_depth == 2
        runner.close()

    def test_pipeline_runner_run_from_files(self, tmp_path):
        """PipelineRunner processes local files through full pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        # Add an interest
        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"],
        ))

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It is widely used in production systems."
        )
        file2 = tmp_path / "article2.txt"
        file2.write_text(
            "JavaScript is the language of the web, used for frontend and backend "
            "development. Node.js enables server-side JavaScript programming."
        )

        stats = runner.run_from_files([str(file1), str(file2)])

        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in == 2
        assert stats.pages_scored == 2
        assert stats.pages_tagged == 2
        assert stats.pages_indexed == 2
        assert stats.errors == []
        runner.close()

    def test_pipeline_runner_filters_short_content(self, tmp_path):
        """PipelineRunner filters out content below min_content_length."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=100)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="test",
            keywords=["hello"],
        ))

        short_file = tmp_path / "short.txt"
        short_file.write_text("Short content.")

        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "This is a longer piece of content that discusses programming "
            "languages and software development in great detail. It covers "
            "many topics including python, javascript, and rust programming."
        )

        stats = runner.run_from_files([str(short_file), str(long_file)])

        assert stats.pages_crawled == 2
        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 1
        runner.close()

    def test_pipeline_runner_stats_summary(self):
        """PipelineStats.summary returns readable output."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            pages_indexed=5,
            errors=["timeout"],
            elapsed_seconds=3.5,
            tags_applied=10,
        )
        summary = stats.summary()
        assert "Pipeline Summary" in summary
        assert "Crawled:      10" in summary
        assert "Indexed:      5" in summary
        assert "Errors:       1" in summary
        assert "Time:         3.5s" in summary


class TestPipelineRunnerWithMockedCrawler:
    """Test PipelineRunner with mocked web crawler."""

    def test_full_pipeline_with_mocked_crawler(self, tmp_path):
        """Full pipeline: crawl → extract → filter → score → tag → index."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "language"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-tutorial",
                title="Python Programming Tutorial",
                content="Python is a versatile programming language used for web development, "
                        "data science, and automation. It is widely used in production systems "
                        "around the world.",
            ),
            CrawledPage(
                url="https://example.com/js-guide",
                title="JavaScript Development Guide",
                content="JavaScript is the language of the web, used for frontend and backend "
                        "development. Node.js enables server-side JavaScript programming.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in == 2
        assert stats.pages_scored == 2
        assert stats.pages_indexed == 2
        assert stats.errors == []
        runner.close()

    def test_pipeline_with_no_interests(self, tmp_path):
        """Pipeline works without interests (require_interest_match=False)."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        # Don't add any interests - filter should still pass with require_interest_match=False

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Some Page",
                content="This is some content about various topics and general information.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 1
        assert stats.pages_indexed == 1
        runner.close()

    def test_pipeline_empty_crawl_results(self, tmp_path):
        """Pipeline handles empty crawl results gracefully."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        with patch.object(runner._crawler, "crawl", return_value=[]):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0
        assert stats.errors == []
        runner.close()


class TestPipelineRunnerTagging:
    """Test tagging within the pipeline."""

    def test_pipeline_auto_tags_by_interest(self, tmp_path):
        """Pipeline auto-tags pages based on matched interests."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))
        runner._interest_store.add(Interest(
            name="webdev",
            keywords=["javascript", "react", "html"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python-page",
                title="Python Web Development",
                content="Python with Django and Flask for web development.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_tagged == 1
        assert stats.tags_applied >= 1
        # Verify tag was actually stored
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tags = tag_store.get_tags_for_page("https://example.com/python-page")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        runner.close()

    def test_pipeline_tags_persist_to_disk(self, tmp_path):
        """Tags applied by pipeline persist to disk."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/tech",
                title="Tech Article",
                content="Python programming is fun and useful.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                runner.run(["https://example.com"], max_depth=1)
        runner.close()

        # Reload tag store and verify
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tags = tag_store.get_tags_for_page("https://example.com/tech")
        tag_names = [t.name for t in tags]
        assert "tech" in tag_names


class TestPipelineRunnerScoring:
    """Test scoring within the pipeline."""

    def test_pipeline_scores_pages(self, tmp_path):
        """Pipeline assigns scores to pages."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/high-score",
                title="Python Programming",
                content="Python programming Python programming Python programming.",
            ),
            CrawledPage(
                url="https://example.com/low-score",
                title="Unrelated Content",
                content="This content has nothing to do with programming.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_scored == 2
        runner.close()

    def test_pipeline_filters_by_score_threshold(self, tmp_path):
        """Pipeline filters pages below score threshold."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.5, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/relevant",
                title="Python Guide",
                content="Python Python Python Python Python Python Python Python.",
            ),
            CrawledPage(
                url="https://example.com/irrelevant",
                title="Random Stuff",
                content="This is random content with no keywords.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                stats = runner.run(["https://example.com"], max_depth=1)

        # At least the relevant page should be indexed
        assert stats.pages_indexed >= 1
        runner.close()


class TestPipelineRunnerIndexing:
    """Test indexing within the pipeline."""

    def test_pipeline_index_is_searchable(self, tmp_path):
        """Pages indexed by pipeline are searchable."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Learn Python programming from scratch.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                runner.run(["https://example.com"], max_depth=1)
        runner.close()

        # Search the index
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 1
        assert results[0].title == "Python Tutorial"
        index.close()

    def test_pipeline_index_persists_across_runs(self, tmp_path):
        """Index persists between pipeline runs."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        # First run
        runner1 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        runner1._interest_store.add(Interest(
            name="python",
            keywords=["python"],
        ))
        pages1 = [
            CrawledPage(
                url="https://example.com/page1",
                title="Page One",
                content="Python is great for programming.",
            ),
        ]
        with patch.object(runner1._crawler, "crawl", return_value=pages1):
            with patch.object(runner1._crawler, "close"):
                runner1.run(["https://example.com"], max_depth=1)
        runner1.close()

        # Second run
        runner2 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        pages2 = [
            CrawledPage(
                url="https://example.com/page2",
                title="Page Two",
                content="JavaScript is also popular.",
            ),
        ]
        with patch.object(runner2._crawler, "crawl", return_value=pages2):
            with patch.object(runner2._crawler, "close"):
                runner2.run(["https://example.com"], max_depth=1)
        runner2.close()

        # Both pages should be in index
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 2
        index.close()


class TestPipelineRunnerProgress:
    """Test progress callback in PipelineRunner."""

    def test_progress_callback_receives_updates(self, tmp_path):
        """Progress callback receives stage updates."""
        data_dir = str(tmp_path / "data")
        updates = []

        def callback(stage, count):
            updates.append((stage, count))

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=config,
            progress_callback=callback,
        )

        runner._interest_store.add(Interest(
            name="test",
            keywords=["test"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/p1",
                title="Test Page",
                content="This is a test page with test content.",
            ),
        ]

        with patch.object(runner._crawler, "crawl", return_value=pages):
            with patch.object(runner._crawler, "close"):
                runner.run(["https://example.com"], max_depth=1)
        runner.close()

        # Should have received updates for multiple stages
        assert len(updates) > 0
        stages = [u[0] for u in updates]
        assert "crawl" in stages or "extract" in stages or "filter" in stages
