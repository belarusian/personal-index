"""Search integration tests.

Tests search functionality across the full stack,
verifying indexing, retrieval, and ranking work correctly.
"""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner


class TestSearchIntegration:
    """Test search functionality with real indexed data."""

    def test_search_finds_relevant_content(self, tmp_path):
        """Test that search returns relevant results."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Create test files
        files = []
        for topic, content in [
            ("python", "Python is a programming language created by Guido van Rossum."),
            ("javascript", "JavaScript is a scripting language for web development."),
            ("rust", "Rust is a systems programming language focused on safety."),
        ]:
            f = tmp_path / f"{topic}.txt"
            f.write_text(content)
            files.append(str(f))

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files(files)
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        # Search for "python"
        results = index.search("python")
        assert len(results) >= 1
        assert any("python" in r.url.lower() for r in results)

    def test_search_ranking_by_relevance(self, tmp_path):
        """Test that search results are ranked by relevance."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Create files with varying relevance to "python"
        files = []
        # High relevance: many mentions of python
        f1 = tmp_path / "high_relevance.txt"
        f1.write_text(
            "Python Python Python. Python is great for Python development. "
            "Python programming with Python frameworks."
        )
        files.append(str(f1))

        # Low relevance: one mention
        f2 = tmp_path / "low_relevance.txt"
        f2.write_text("This article mentions Python once in passing.")
        files.append(str(f2))

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files(files)
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")

        assert len(results) >= 2
        # Higher relevance should rank first
        assert results[0].relevance_score >= results[1].relevance_score

    def test_search_with_no_results(self, tmp_path):
        """Test search returns empty results for non-matching queries."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text("Python programming language.")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("xyznonexistent")
        assert len(results) == 0

    def test_search_with_empty_query(self, tmp_path):
        """Test search handles empty query gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text("Python programming language.")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("")
        assert len(results) == 0

    def test_search_limit_results(self, tmp_path):
        """Test search respects the limit parameter."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Create 5 files all containing "python"
        files = []
        for i in range(5):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(f"Python programming article {i}.")
            files.append(str(f))

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files(files)
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python", limit=2)
        assert len(results) <= 2

    def test_search_snippet_generation(self, tmp_path):
        """Test that search results include relevant snippets."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text(
            "This is a long article about Python programming. "
            "Python is used for web development, data science, "
            "and machine learning. Python has a large ecosystem."
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) >= 1
        assert len(results[0].snippet) > 0
        # Snippet should contain the search term
        assert "python" in results[0].snippet.lower()

    def test_search_multi_word_query(self, tmp_path):
        """Test search with multi-word queries."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text(
            "Python web development with Django and Flask frameworks. "
            "Building web applications with Python is straightforward."
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python web development")
        assert len(results) >= 1

    def test_search_persistence_across_sessions(self, tmp_path):
        """Test that search works after index is saved and reloaded."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text("Python programming language for web development.")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        # Create a new index instance (simulating new session)
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) >= 1

    def test_search_case_insensitive(self, tmp_path):
        """Test that search is case-insensitive."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text("Python programming language.")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        # All these should find the same result
        for query in ["python", "Python", "PYTHON", "PyThOn"]:
            results = index.search(query)
            assert len(results) >= 1, f"Query '{query}' should find results"

    def test_search_with_special_characters(self, tmp_path):
        """Test search handles special characters in queries."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        f = tmp_path / "article.txt"
        f.write_text("Python programming language for web development.")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        try:
            runner.run_from_files([str(f)])
        finally:
            runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))

        # Special characters should not crash
        results = index.search("python & javascript")
        assert isinstance(results, list)

        results = index.search("python's")
        assert isinstance(results, list)
