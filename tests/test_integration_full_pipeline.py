"""Full pipeline integration tests: crawl → extract → filter → score → tag → index.

These tests verify the complete end-to-end workflow works correctly.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineWithFiles:
    """Test the complete pipeline using local files."""

    def test_pipeline_from_files_basic(self, tmp_path):
        """Test basic pipeline run with a single text file."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "test_article.txt"
        test_file.write_text(
            "# Python Tutorial\n\n"
            "This is a comprehensive guide to Python programming. "
            "Python is a versatile language used for web development, "
            "data science, and automation."
        )

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        stats = runner.run_from_files([str(test_file)])
        runner.close()

        assert stats.pages_crawled == 1
        assert stats.pages_extracted == 1
        assert stats.pages_filtered_in == 1
        assert stats.pages_indexed == 1
        assert stats.errors == []

    def test_pipeline_from_files_multiple(self, tmp_path):
        """Test pipeline with multiple files."""
        data_dir = str(tmp_path / "data")
        files = []
        for i in range(5):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(f"# Article {i}\n\nContent about topic {i} with details.")
            files.append(str(f))

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        stats = runner.run_from_files(files)
        runner.close()

        assert stats.pages_crawled == 5
        assert stats.pages_indexed == 5

    def test_pipeline_filters_short_content(self, tmp_path):
        """Test that short content is filtered out."""
        data_dir = str(tmp_path / "data")
        short_file = tmp_path / "short.txt"
        short_file.write_text("Hi")
        long_file = tmp_path / "long.txt"
        long_file.write_text("# Title\n\n" + "Word " * 50)

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=100),
        )
        stats = runner.run_from_files([str(short_file), str(long_file)])
        runner.close()

        assert stats.pages_crawled == 2
        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 1

    def test_pipeline_with_interests(self, tmp_path):
        """Test pipeline scoring with configured interests."""
        data_dir = str(tmp_path / "data")
        # Set up interests
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
            priority=8,
        ))

        test_file = tmp_path / "python_guide.txt"
        test_file.write_text(
            "# Python Guide\n\n"
            "Learn Python programming. Python is great for data science."
        )

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        stats = runner.run_from_files([str(test_file)])
        runner.close()

        assert stats.pages_indexed == 1
        assert stats.interests_matched >= 1

    def test_pipeline_persists_index(self, tmp_path):
        """Test that the search index persists to disk."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nThis is test content for indexing.")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        runner.run_from_files([str(test_file)])
        runner.close()

        # Verify persistence by loading a fresh index
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 1

    def test_pipeline_persists_tags(self, tmp_path):
        """Test that tags persist to disk."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nThis is test content.")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        runner.run_from_files([str(test_file)])
        runner.close()

        # Verify tag persistence
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        assert tag_store.get_tag_count() > 0

    def test_pipeline_handles_empty_files(self, tmp_path):
        """Test pipeline handles empty files gracefully."""
        data_dir = str(tmp_path / "data")
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        stats = runner.run_from_files([str(empty_file)])
        runner.close()

        assert stats.pages_indexed == 0
        assert stats.errors == []

    def test_pipeline_handles_missing_files(self, tmp_path):
        """Test pipeline handles missing files gracefully."""
        data_dir = str(tmp_path / "data")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        stats = runner.run_from_files(["/nonexistent/file.txt"])
        runner.close()

        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0


class TestSearchAfterPipeline:
    """Test that search works after pipeline indexing."""

    def test_search_returns_indexed_content(self, tmp_path):
        """Test search finds content indexed by pipeline."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "# Python Programming\n\n"
            "Python is a high-level programming language. "
            "It supports multiple programming paradigms."
        )

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        runner.run_from_files([str(test_file)])
        runner.close()

        # Search for indexed content
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].title

    def test_search_multiple_results(self, tmp_path):
        """Test search returns multiple results."""
        data_dir = str(tmp_path / "data")
        files = []
        for topic in ["python", "javascript", "rust"]:
            f = tmp_path / f"{topic}.txt"
            f.write_text(f"# {topic.title()}\n\nLearn {topic} programming.")
            files.append(str(f))

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        runner.run_from_files(files)
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("programming")
        assert len(results) == 3

    def test_search_no_results(self, tmp_path):
        """Test search returns empty for non-matching query."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "article.txt"
        test_file.write_text("# Article\n\nSome content here.")

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=10),
        )
        runner.run_from_files([str(test_file)])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("xyznonexistent")
        assert len(results) == 0
