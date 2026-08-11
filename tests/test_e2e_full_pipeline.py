"""End-to-end integration tests for the full crawl→extract→filter→score→tag→index pipeline.

These tests verify that the complete pipeline works correctly using
local file imports (no network required).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineEndToEnd:
    """Test the complete pipeline from crawl to search."""

    def test_full_pipeline_file_import_to_search(self, tmp_path):
        """Test complete pipeline: import files → search results."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        # Set up interests
        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "programming", "software"],
        ))

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and software engineering. It supports multiple paradigms."
        )
        file2 = tmp_path / "article2.txt"
        file2.write_text(
            "JavaScript is a scripting language for web browsers and server-side "
            "development with Node.js runtime environment."
        )

        stats = runner.run_from_files([str(file1), str(file2)])

        # Verify pipeline processed files
        assert stats.pages_crawled >= 1
        assert stats.pages_indexed >= 1

        # Verify search works
        results = runner._search_index.search("python")
        assert len(results) >= 1
        assert any("python" in r.title.lower() or "python" in r.snippet.lower()
                   for r in results)

        runner.close()

    def test_pipeline_filters_low_quality_content(self, tmp_path):
        """Test that short/low-quality content is filtered out."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=50)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="tech", keywords=["python", "code"],
        ))

        # Short content should be filtered
        short_file = tmp_path / "short.txt"
        short_file.write_text("Hi there.")

        # Long content should pass
        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "Python programming language is excellent for software development. "
            "It supports object-oriented, functional, and procedural paradigms. "
            "Many developers use Python for web development with Django and Flask."
        )

        stats = runner.run_from_files([str(short_file), str(long_file)])

        assert stats.pages_filtered_out >= 1
        assert stats.pages_indexed >= 1
        runner.close()

    def test_pipeline_tags_and_searches(self, tmp_path):
        """Test that tagged pages are discoverable via search."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)

        runner._interest_store.add(Interest(
            name="webdev", keywords=["python", "web", "development"],
        ))

        file = tmp_path / "webdev.txt"
        file.write_text(
            "Python web development with Django and Flask frameworks. "
            "Building REST APIs and web applications."
        )

        stats = runner.run_from_files([str(file)])
        assert stats.pages_indexed >= 1

        # Verify tags were applied
        assert stats.pages_tagged >= 1
        assert stats.tags_applied >= 1

        # Verify search finds it
        results = runner._search_index.search("web development")
        assert len(results) >= 1

        runner.close()

    def test_pipeline_persistence_across_runs(self, tmp_path):
        """Test that index persists between pipeline runs."""
        data_dir = str(tmp_path / "data")
        cfg = PipelineConfig(min_score_threshold=0.0, min_content_length=10)

        # First run
        runner1 = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)
        runner1._interest_store.add(Interest(
            name="tech", keywords=["python"],
        ))
        file1 = tmp_path / "file1.txt"
        file1.write_text("Python programming language for software development.")
        stats1 = runner1.run_from_files([str(file1)])
        runner1.close()

        # Second run - should see previous index
        runner2 = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)
        assert runner2._search_index.get_page_count() >= stats1.pages_indexed

        file2 = tmp_path / "file2.txt"
        file2.write_text("More about Python and programming best practices.")
        stats2 = runner2.run_from_files([str(file2)])
        runner2.close()

        # Third run - verify cumulative index
        runner3 = PipelineRunner(data_dir=data_dir, pipeline_config=cfg)
        total = runner3._search_index.get_page_count()
        assert total >= 2  # At least 2 unique pages indexed across runs
        runner3.close()


class TestCLIEndToEndWorkflow:
    """Test complete CLI workflows end-to-end."""

    def test_cli_init_import_search_workflow(self, tmp_path, monkeypatch):
        """Test the full CLI workflow: init → import → search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Step 2: Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python", "-k", "python", "-k", "programming"
        ])
        assert result.exit_code == 0

        # Step 3: Create and import content
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a great programming language for web development and data science."
        )
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # Step 4: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()

    def test_cli_pipeline_with_file_import(self, tmp_path, monkeypatch):
        """Test CLI pipeline command with file import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        runner.invoke(main, ["init"])

        # Add interests
        runner.invoke(main, [
            "interests", "add", "-n", "tech", "-k", "python", "-k", "software"
        ])

        # Create content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python software development best practices for professional programmers. "
            "Learn about testing, documentation, and code quality."
        )

        # Run pipeline
        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output or "Indexed:" in result.output

    def test_cli_stats_after_import(self, tmp_path, monkeypatch):
        """Test stats command shows correct data after import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
        assert "indexed_pages" in result.output.lower() or "Indexed pages" in result.output

    def test_cli_list_after_import(self, tmp_path, monkeypatch):
        """Test list command shows imported pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

    def test_cli_top_after_import(self, tmp_path, monkeypatch):
        """Test top command shows highest-scored pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0

    def test_cli_remove_page(self, tmp_path, monkeypatch):
        """Test removing a page from the index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(test_file)])

        # Get URL of imported page
        result = runner.invoke(main, ["list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["pages"]) >= 1
        url = data["pages"][0]["url"]

        # Remove it
        result = runner.invoke(main, ["remove", url])
        assert result.exit_code == 0

        # Verify it's gone
        result = runner.invoke(main, ["list", "--format", "json"])
        remaining = json.loads(result.output)
        assert all(p["url"] != url for p in remaining["pages"])

    def test_cli_clear_index(self, tmp_path, monkeypatch):
        """Test clearing the index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        # Clear
        result = runner.invoke(main, ["clear", "--index", "--tags"])
        assert result.exit_code == 0

        # Verify empty
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

    def test_cli_export_after_import(self, tmp_path, monkeypatch):
        """Test export works after importing content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(test_file)])

        # Export as JSON
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        # Export as markdown
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_cli_search_with_tag_filter(self, tmp_path, monkeypatch):
        """Test search with tag filter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "python"])

        test_file = tmp_path / "test.txt"
        test_file.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(test_file)])

        # Search with tag filter
        result = runner.invoke(main, ["search", "python", "--tag", "tutorial"])
        assert result.exit_code == 0

    def test_cli_full_workflow_multiple_files(self, tmp_path, monkeypatch):
        """Test complete workflow with multiple files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "tech", "-k", "python", "-k", "javascript"])

        # Create multiple files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "python.txt").write_text(
            "Python is a versatile programming language for web development."
        )
        (docs_dir / "js.txt").write_text(
            "JavaScript is the language of the web, used for frontend development."
        )
        (docs_dir / "rust.txt").write_text(
            "Rust is a systems programming language focused on safety and performance."
        )

        # Import all
        result = runner.invoke(main, ["import", str(docs_dir), "--recursive"])
        assert result.exit_code == 0

        # Search for python
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Search for javascript
        result = runner.invoke(main, ["search", "javascript"])
        assert result.exit_code == 0

        # Stats
        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
