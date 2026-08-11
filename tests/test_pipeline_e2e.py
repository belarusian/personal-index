"""End-to-end integration tests for the full crawl→extract→filter→score→tag→index pipeline.

These tests verify that all pipeline stages work together correctly,
using local files to avoid network dependencies.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineRunnerFileBased:
    """Test the full pipeline using local files (no network)."""

    def test_run_from_files_basic(self, tmp_path):
        """Test pipeline processes local files through all 6 stages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. Python supports multiple programming paradigms "
            "including procedural, object-oriented, and functional programming."
        )
        file2 = tmp_path / "article2.txt"
        file2.write_text(
            "JavaScript is the language of the web. It powers interactive websites "
            "and modern web applications. Node.js brings JavaScript to the server side."
        )

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([str(file1), str(file2)])

            # Verify all stages ran
            assert stats.pages_crawled == 2
            assert stats.pages_extracted == 2
            assert stats.pages_filtered_in == 2
            assert stats.pages_filtered_out == 0
            assert stats.pages_scored == 2
            assert stats.pages_tagged == 2
            assert stats.pages_indexed == 2
            assert stats.tags_applied > 0  # keyword tags should be added
            assert stats.elapsed_seconds >= 0
            assert len(stats.errors) == 0
        finally:
            runner.close()

    def test_run_from_files_with_interests(self, tmp_path):
        """Test pipeline respects configured interests."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Pre-configure interests
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
            priority=8,
        ))
        interest_store.add(Interest(
            name="webdev",
            keywords=["javascript", "react", "web"],
            priority=7,
        ))

        # Create test files
        file1 = tmp_path / "python_article.txt"
        file1.write_text(
            "Python and Django are great for web development. Flask is another "
            "popular Python framework for building web applications."
        )
        file2 = tmp_path / "js_article.txt"
        file2.write_text(
            "JavaScript and React are essential for modern web development. "
            "The web ecosystem continues to grow with new frameworks."
        )
        file3 = tmp_path / "unrelated.txt"
        file3.write_text(
            "This article is about cooking recipes and baking cakes. "
            "It has nothing to do with programming or technology."
        )

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([str(file1), str(file2), str(file3)])

            assert stats.pages_crawled == 3
            assert stats.pages_filtered_in == 3  # All pass (require_interest_match=False)
            assert stats.pages_indexed == 3
            assert stats.interests_matched >= 2  # At least python and js articles match
        finally:
            runner.close()

    def test_run_from_files_empty_content(self, tmp_path):
        """Test pipeline handles empty files gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "empty.txt"
        file1.write_text("")
        file2 = tmp_path / "short.txt"
        file2.write_text("Hi")

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([str(file1), str(file2)])

            assert stats.pages_crawled == 2
            # Empty and short content should be filtered out
            assert stats.pages_filtered_out >= 1
            assert stats.pages_indexed == 0
        finally:
            runner.close()

    def test_run_from_files_with_errors(self, tmp_path):
        """Test pipeline handles file read errors gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "good.txt"
        file1.write_text("This is a good article about programming and software development.")

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([str(file1), "/nonexistent/file.txt"])

            assert stats.pages_crawled == 1  # Only the good file
            assert stats.pages_indexed == 1
            assert len(stats.errors) == 1  # One error for missing file
            assert "File read error" in stats.errors[0]
        finally:
            runner.close()

    def test_pipeline_persists_data(self, tmp_path):
        """Test that pipeline data persists to disk and can be reloaded."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "article.txt"
        file1.write_text(
            "Python programming language tutorial for beginners and advanced developers."
        )

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(file1)])
        finally:
            runner.close()

        # Verify files were created
        assert os.path.exists(os.path.join(data_dir, "search_index.json"))
        assert os.path.exists(os.path.join(data_dir, "tags.json"))

        # Reload and verify
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 1
        results = index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].snippet

        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        assert tag_store.get_tagged_page_count() >= 1

    def test_pipeline_stats_summary(self, tmp_path):
        """Test PipelineStats summary method."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=6,
            tags_applied=15,
            pages_indexed=6,
            errors=["error1"],
            elapsed_seconds=2.5,
        )
        summary = stats.summary()
        assert "Crawled:      10" in summary
        assert "Extracted:    8" in summary
        assert "Filtered in:  6" in summary
        assert "Errors:       1" in summary
        assert "Time:         2.5s" in summary

    def test_pipeline_get_stats(self, tmp_path):
        """Test PipelineRunner.get_stats returns correct data."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "article.txt"
        file1.write_text("Python programming tutorial for web development.")

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(file1)])
            stats = runner.get_stats()

            assert stats["indexed_pages"] == 1
            assert stats["total_tags"] >= 1
            assert stats["tagged_pages"] >= 1
        finally:
            runner.close()

    def test_pipeline_progress_callback(self, tmp_path):
        """Test that progress callback is invoked at each stage."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "article.txt"
        file1.write_text("Python programming tutorial for web development.")

        stages = []
        def callback(stage, count):
            stages.append((stage, count))

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=config,
            progress_callback=callback,
        )

        try:
            runner.run_from_files([str(file1)])
        finally:
            runner.close()

        stage_names = [s[0] for s in stages]
        assert "crawl" in stage_names
        assert "extract" in stage_names
        assert "filter" in stage_names
        assert "score" in stage_names
        assert "tag" in stage_names
        assert "index" in stage_names


class TestPipelineRunnerWithMockedCrawler:
    """Test the full crawl pipeline with mocked network requests."""

    def test_full_crawl_pipeline(self, tmp_path):
        """Test crawl→extract→filter→score→tag→index with mocked crawler."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Pre-configure interests
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"],
        ))

        mock_pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Python is a great programming language for web development.",
                meta_description="Learn Python programming",
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Guide",
                content="JavaScript powers the modern web with frameworks like React.",
                meta_description="JavaScript web development",
            ),
        ]

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            with patch.object(runner._crawler, "crawl", return_value=mock_pages):
                stats = runner.run(["https://example.com"])

            assert stats.pages_crawled == 2
            assert stats.pages_extracted == 2
            assert stats.pages_filtered_in == 2
            assert stats.pages_scored == 2
            assert stats.pages_tagged == 2
            assert stats.pages_indexed == 2
            assert stats.interests_matched >= 1
        finally:
            runner.close()

    def test_crawl_pipeline_with_filtering(self, tmp_path):
        """Test that filter stage correctly removes low-quality pages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        mock_pages = [
            CrawledPage(
                url="https://example.com/good",
                title="Good Article",
                content="This is a comprehensive article about programming and software development best practices.",
            ),
            CrawledPage(
                url="https://example.com/short",
                title="X",
                content="Hi.",
            ),
        ]

        config = PipelineConfig(min_content_length=50, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            with patch.object(runner._crawler, "crawl", return_value=mock_pages):
                stats = runner.run(["https://example.com"])

            assert stats.pages_crawled == 2
            assert stats.pages_filtered_in == 1
            assert stats.pages_filtered_out == 1
            assert stats.pages_indexed == 1
        finally:
            runner.close()


class TestPipelineRunnerEdgeCases:
    """Test edge cases and error handling in the pipeline."""

    def test_run_with_no_seed_urls(self, tmp_path):
        """Test pipeline handles empty URL list."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run([])
            assert stats.pages_crawled == 0
            assert stats.pages_indexed == 0
        finally:
            runner.close()

    def test_run_from_files_with_no_files(self, tmp_path):
        """Test pipeline handles empty file list."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([])
            assert stats.pages_crawled == 0
            assert stats.pages_indexed == 0
        finally:
            runner.close()

    def test_pipeline_handles_unicode_content(self, tmp_path):
        """Test pipeline handles Unicode content correctly."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "unicode.txt"
        file1.write_text(
            "Python プログラミング言語は素晴らしいです。"
            "JavaScript и веб-разработка тоже интересны."
            "Émojis 🐍🚀 are fun too!"
        )

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            stats = runner.run_from_files([str(file1)])
            assert stats.pages_crawled == 1
            assert stats.pages_indexed == 1
            assert len(stats.errors) == 0
        finally:
            runner.close()

    def test_pipeline_multiple_runs_accumulate(self, tmp_path):
        """Test that multiple pipeline runs accumulate indexed pages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "article1.txt"
        file1.write_text("Python programming language tutorial for web development.")
        file2 = tmp_path / "article2.txt"
        file2.write_text("JavaScript framework React for building user interfaces.")

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(file1)])
            stats1 = runner.get_stats()
            assert stats1["indexed_pages"] == 1

            runner.run_from_files([str(file2)])
            stats2 = runner.get_stats()
            assert stats2["indexed_pages"] == 2
        finally:
            runner.close()

    def test_pipeline_close_saves_data(self, tmp_path):
        """Test that close() properly saves all data."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        file1 = tmp_path / "article.txt"
        file1.write_text("Python programming tutorial for web development.")

        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner.run_from_files([str(file1)])
        runner.close()

        # Verify data persisted
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 1
