"""End-to-end pipeline integration tests.

Tests the complete pipeline flow: crawl → extract → filter → score → tag → index.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineRunnerE2E:
    """Test the full pipeline runner end-to-end."""

    def setup_method(self):
        """Set up test fixtures."""
        self.tmp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.tmp_dir, "test_data")
        os.makedirs(self.data_dir, exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_pipeline_run_from_files_basic(self):
        """Test pipeline processes files through all stages."""
        # Create test files
        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write(
                "Python is a versatile programming language used for web development, "
                "data science, and machine learning. Python supports multiple programming "
                "paradigms including procedural, object-oriented, and functional programming."
            )

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        assert stats.pages_crawled == 1
        assert stats.pages_extracted == 1
        assert stats.pages_filtered_in == 1
        assert stats.pages_indexed == 1

    def test_pipeline_filters_short_content(self):
        """Test pipeline filters out content below minimum length."""
        test_file = os.path.join(self.tmp_dir, "short.txt")
        with open(test_file, "w") as f:
            f.write("Too short")

        config = PipelineConfig(
            min_content_length=100,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        assert stats.pages_crawled == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 0

    def test_pipeline_scores_with_interests(self):
        """Test pipeline scores content based on interests."""
        # Add an interest
        interest_store = InterestStore(
            store_path=os.path.join(self.data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
            priority=8,
        ))

        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write(
                "Python programming is great for web development. "
                "Python supports many libraries and frameworks."
            )

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        assert stats.pages_scored == 1
        assert stats.interests_matched == 1

    def test_pipeline_tags_matched_interests(self):
        """Test pipeline tags pages with matched interest names."""
        # Add an interest
        interest_store = InterestStore(
            store_path=os.path.join(self.data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="webdev",
            keywords=["web", "development", "javascript"],
            priority=5,
        ))

        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write(
                "Web development with JavaScript and Python. "
                "Modern web frameworks make development easier."
            )

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        assert stats.pages_tagged >= 1
        assert stats.tags_applied >= 1

        # Verify tag was actually stored
        tag_store = TagStore(
            store_path=os.path.join(self.data_dir, "tags.json")
        )
        tags = tag_store.get_tags_for_page(test_file)
        tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
        assert "webdev" in tag_names

    def test_pipeline_indexes_content(self):
        """Test pipeline adds content to search index."""
        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write(
                "Machine learning is a subset of artificial intelligence. "
                "It enables systems to learn and improve from experience."
            )

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        # Verify content is in the index
        search_index = SearchIndex(
            db_path=os.path.join(self.data_dir, "search_index.json")
        )
        assert search_index.get_page_count() == 1

        # Verify search works
        results = search_index.search("machine learning")
        assert len(results) == 1
        assert "machine learning" in results[0].title.lower() or \
               "machine learning" in (results[0].snippet or "").lower()

    def test_pipeline_multiple_files(self):
        """Test pipeline processes multiple files."""
        files = []
        for i in range(3):
            test_file = os.path.join(self.tmp_dir, f"article_{i}.txt")
            with open(test_file, "w") as f:
                f.write(
                    f"This is article number {i} about programming. "
                    f"It discusses Python, JavaScript, and web development."
                )
            files.append(test_file)

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files(files)
        runner.close()

        assert stats.pages_crawled == 3
        assert stats.pages_indexed == 3

    def test_pipeline_score_threshold_filters(self):
        """Test pipeline filters pages below score threshold."""
        # Add interest that won't match
        interest_store = InterestStore(
            store_path=os.path.join(self.data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="cooking",
            keywords=["recipe", "cooking", "baking"],
            priority=5,
        ))

        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write(
                "This article is about programming and software development. "
                "It has nothing to do with cooking or recipes."
            )

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=5.0,  # High threshold
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files([test_file])
        runner.close()

        # Page should be filtered out due to low score
        assert stats.pages_indexed == 0

    def test_pipeline_stats_summary(self):
        """Test pipeline stats summary is formatted correctly."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            tags_applied=12,
            pages_indexed=6,
            elapsed_seconds=3.5,
        )

        summary = stats.summary()
        assert "Pipeline Summary" in summary
        assert "Crawled:      10" in summary
        assert "Indexed:      6" in summary
        assert "Time:         3.5s" in summary

    def test_pipeline_get_stats(self):
        """Test pipeline get_stats returns correct data."""
        test_file = os.path.join(self.tmp_dir, "article.txt")
        with open(test_file, "w") as f:
            f.write("Python programming tutorial for web development.")

        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        runner.run_from_files([test_file])

        stats = runner.get_stats()
        assert "indexed_pages" in stats
        assert "total_interests" in stats
        assert "total_tags" in stats
        assert "tagged_pages" in stats
        assert stats["indexed_pages"] == 1

        runner.close()

    def test_pipeline_handles_missing_files(self):
        """Test pipeline handles missing files gracefully."""
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(
            data_dir=self.data_dir,
            pipeline_config=config,
        )

        stats = runner.run_from_files(["/nonexistent/file.txt"])
        runner.close()

        assert stats.pages_indexed == 0
        assert len(stats.errors) == 1
