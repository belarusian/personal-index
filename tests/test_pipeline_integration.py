"""Integration tests for the full crawl→extract→filter→score→tag→index→search pipeline.

These tests verify that all pipeline stages work together correctly,
from content ingestion through search retrieval.
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


class TestPipelineRunnerBasic:
    """Test PipelineRunner with file-based input."""

    def test_run_from_files_basic(self, tmp_path):
        """Pipeline should process files through all stages."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        # Create test files
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "python_intro.txt").write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and machine learning. Python has a clean syntax."
        )
        (docs / "javascript_intro.txt").write_text(
            "JavaScript is a programming language for web development. "
            "It runs in the browser and on the server with Node.js."
        )

        runner = PipelineRunner(data_dir=data_dir)

        # Add an interest so scoring works
        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"]
        ))

        stats = runner.run_from_files([
            str(docs / "python_intro.txt"),
            str(docs / "javascript_intro.txt"),
        ])

        runner.close()

        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in == 2
        assert stats.pages_scored == 2
        assert stats.pages_tagged == 2
        assert stats.pages_indexed == 2
        assert stats.errors == []
        assert stats.elapsed_seconds > 0

    def test_run_from_files_empty_content(self, tmp_path):
        """Files with empty content should be skipped."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "empty.txt").write_text("")
        (docs / "good.txt").write_text(
            "This is a proper article with enough content to be indexed "
            "and scored properly by the pipeline system."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "empty.txt"),
            str(docs / "good.txt"),
        ])
        runner.close()

        # Empty file should not be indexed
        assert stats.pages_crawled == 1  # Only good.txt
        assert stats.pages_indexed == 1

    def test_run_from_files_nonexistent(self, tmp_path):
        """Non-existent files should produce errors, not crash."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files(["/nonexistent/file.txt"])
        runner.close()

        assert len(stats.errors) > 0
        assert stats.pages_indexed == 0


class TestPipelineSearchIntegration:
    """Test that pipeline-indexed content is searchable."""

    def test_search_after_pipeline(self, tmp_path):
        """Content indexed by pipeline should be findable via search."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Machine learning is a subset of artificial intelligence. "
            "Deep learning uses neural networks for pattern recognition."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "article.txt")])

        # Verify search works
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("machine learning")

        runner.close()

        assert len(results) == 1
        assert "machine" in results[0].snippet.lower() or "learning" in results[0].snippet.lower()

    def test_search_multiple_results(self, tmp_path):
        """Search should return multiple results ranked by relevance."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.txt").write_text("Python programming for beginners.")
        (docs / "b.txt").write_text("Python advanced programming techniques.")
        (docs / "c.txt").write_text("JavaScript web development guide.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([
            str(docs / "a.txt"),
            str(docs / "b.txt"),
            str(docs / "c.txt"),
        ])

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")

        runner.close()

        assert len(results) == 2  # Only python articles match
        # Results should be sorted by relevance
        assert results[0].relevance_score >= results[1].relevance_score


class TestPipelineTaggingIntegration:
    """Test that tagging works correctly through the pipeline."""

    def test_tags_applied_after_pipeline(self, tmp_path):
        """Tags should be applied based on interests and keywords."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Docker containerization for microservices architecture. "
            "Kubernetes orchestration for cloud deployment."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner._interest_store.add(Interest(
            name="devops",
            keywords=["docker", "kubernetes", "devops"]
        ))

        runner.run_from_files([str(docs / "article.txt")])

        # Check tags were applied
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        all_tags = tag_store.list_tags()

        runner.close()

        assert len(all_tags) > 0
        tag_names = [t.name for t in all_tags]
        assert "devops" in tag_names

    def test_interest_matching_in_pipeline(self, tmp_path):
        """Interest matching should boost scores during pipeline."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "match.txt").write_text(
            "This article discusses python programming and data science."
        )
        (docs / "nomatch.txt").write_text(
            "This article is about cooking recipes and baking."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner._interest_store.add(Interest(
            name="tech",
            keywords=["python", "programming", "data science"]
        ))

        runner.run_from_files([
            str(docs / "match.txt"),
            str(docs / "nomatch.txt"),
        ])

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        pages = index.list_pages()

        runner.close()

        # Both should be indexed (filter doesn't require interest match by default)
        assert len(pages) == 2
        # The matching page should have a higher score
        assert pages[0].score > pages[1].score


class TestPipelineFilteringIntegration:
    """Test that filtering works correctly through the pipeline."""

    def test_min_content_length_filter(self, tmp_path):
        """Content below min length should be filtered out."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "short.txt").write_text("too short")
        (docs / "long.txt").write_text(
            "This is a longer article with sufficient content for indexing "
            "and proper scoring by the pipeline system."
        )

        config = PipelineConfig(min_content_length=50)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([
            str(docs / "short.txt"),
            str(docs / "long.txt"),
        ])
        runner.close()

        assert stats.pages_filtered_out >= 1
        assert stats.pages_filtered_in >= 1

    def test_min_score_threshold(self, tmp_path):
        """Pages below score threshold should not be indexed."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Generic content without any interesting keywords."
        )

        config = PipelineConfig(min_score_threshold=999.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([str(docs / "article.txt")])
        runner.close()

        # Page should pass filter but fail score threshold
        assert stats.pages_indexed == 0


class TestPipelinePersistence:
    """Test that pipeline data persists correctly."""

    def test_index_persists_after_close(self, tmp_path):
        """Indexed data should persist after runner is closed."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Persistent data test for pipeline integration."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "article.txt")])
        runner.close()

        # Re-open index and verify data persists
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert index.get_page_count() == 1
        page = index.get_page(str(docs / "article.txt"))
        assert page is not None
        assert "Persistent" in page.content

    def test_interests_persist_after_close(self, tmp_path):
        """Interests should persist after runner is closed."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        runner = PipelineRunner(data_dir=data_dir)
        runner._interest_store.add(Interest(
            name="test_interest",
            keywords=["test", "integration"]
        ))
        runner.close()

        # Re-open and verify
        store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interests = store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "test_interest"


class TestPipelineStats:
    """Test PipelineStats dataclass."""

    def test_stats_summary(self):
        """Stats summary should be human-readable."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=6,
            pages_indexed=6,
            tags_applied=12,
            errors=[],
            elapsed_seconds=2.5,
        )
        summary = stats.summary()
        assert "Crawled:" in summary
        assert "10" in summary
        assert "2.5s" in summary

    def test_stats_default_values(self):
        """Stats should default to zero."""
        stats = PipelineStats()
        assert stats.pages_crawled == 0
        assert stats.pages_extracted == 0
        assert stats.errors == []
        assert stats.elapsed_seconds == 0.0


class TestPipelineHTMLFiles:
    """Test pipeline with HTML files."""

    def test_html_file_processing(self, tmp_path):
        """HTML files should be properly extracted and indexed."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "page.html").write_text(
            "<html><head><title>Python Tutorial</title></head>"
            "<body><h1>Python Tutorial</h1>"
            "<p>Learn Python programming from scratch.</p>"
            "</body></html>"
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "page.html")])
        runner.close()

        assert stats.pages_crawled == 1
        assert stats.pages_indexed == 1

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) == 1
        assert "Python" in results[0].title


class TestPipelineEndToEnd:
    """Full end-to-end pipeline tests."""

    def test_full_workflow(self, tmp_path):
        """Complete workflow: add interests, import files, search, verify."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "python.txt").write_text(
            "Python is a versatile programming language for web development, "
            "data science, and machine learning."
        )
        (docs / "rust.txt").write_text(
            "Rust is a systems programming language focused on safety and performance."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"]
        ))
        runner._interest_store.add(Interest(
            name="rust",
            keywords=["rust", "systems"]
        ))

        stats = runner.run_from_files([
            str(docs / "python.txt"),
            str(docs / "rust.txt"),
        ])

        # Verify all stages completed
        assert stats.pages_crawled == 2
        assert stats.pages_indexed == 2
        assert stats.tags_applied > 0

        # Verify search works
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        python_results = index.search("python")
        rust_results = index.search("rust")

        assert len(python_results) == 1
        assert len(rust_results) == 1

        # Verify tags
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        python_tags = tag_store.get_tags_for_page(str(docs / "python.txt"))
        assert "python" in python_tags

        runner.close()
