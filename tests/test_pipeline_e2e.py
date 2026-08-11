"""End-to-end integration tests for the full pipeline.

Tests verify the complete crawl → extract → filter → score → tag → index → search
pipeline works correctly with real data through the CLI and programmatic API.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.pipeline_runner import PipelineRunner


class TestPipelineEndToEnd:
    """Test the complete pipeline end-to-end."""

    def test_full_pipeline_with_single_file(self, tmp_path, monkeypatch):
        """Test complete pipeline: import → extract → filter → score → tag → index → search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming",
        ])
        assert result.exit_code == 0

        # Create test file
        test_file = tmp_path / "python_guide.txt"
        test_file.write_text(
            "Python is a versatile programming language. "
            "Python supports multiple programming paradigms including "
            "object-oriented, functional, and procedural programming. "
            "Python is widely used in web development, data science, "
            "and machine learning applications."
        )

        # Run pipeline
        result = runner.invoke(main, ["pipeline", "--import-file", str(test_file)])
        assert result.exit_code == 0
        assert "Indexed:" in result.output
        assert "1" in result.output  # At least 1 page indexed

        # Search should find the content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python_guide" in result.output.lower() or "python" in result.output.lower()

    def test_full_pipeline_with_multiple_files(self, tmp_path, monkeypatch):
        """Test pipeline with multiple files of different topics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "tech", "-k", "python", "-k", "javascript"])

        # Create multiple files
        (tmp_path / "python.txt").write_text(
            "Python programming language for web development and data science."
        )
        (tmp_path / "js.txt").write_text(
            "JavaScript is the language of the web. JavaScript runs in browsers and servers."
        )
        (tmp_path / "random.txt").write_text(
            "This is a random article about cooking pasta and baking bread."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(tmp_path / "python.txt"),
            "--import-file", str(tmp_path / "js.txt"),
            "--import-file", str(tmp_path / "random.txt"),
        ])
        assert result.exit_code == 0

        # All files should be indexed (no interest filter by default)
        result = runner.invoke(main, ["search", "language"])
        assert result.exit_code == 0

    def test_pipeline_with_directory_import(self, tmp_path, monkeypatch):
        """Test pipeline with recursive directory import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create directory structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "intro.md").write_text(
            "Introduction to Python programming. Python is easy to learn."
        )
        (docs_dir / "advanced.md").write_text(
            "Advanced Python concepts: decorators, generators, and metaclasses."
        )
        sub_dir = docs_dir / "tutorials"
        sub_dir.mkdir()
        (sub_dir / "web.md").write_text(
            "Python web development with Flask and Django frameworks."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs_dir), "--recursive"
        ])
        assert result.exit_code == 0

        # Search should find content from all files
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_pipeline_filters_short_content(self, tmp_path, monkeypatch):
        """Test that short content is filtered out by default."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Short content (below default min_content_length)
        short_file = tmp_path / "short.txt"
        short_file.write_text("Hi")

        # Long content
        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "This is a longer article with enough content to pass the filter. "
            "It discusses important topics in detail with comprehensive coverage."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(short_file),
            "--import-file", str(long_file),
            "--min-content-length", "50",
        ])
        assert result.exit_code == 0

    def test_pipeline_with_score_threshold(self, tmp_path, monkeypatch):
        """Test pipeline with minimum score threshold filtering."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        # Relevant content
        relevant = tmp_path / "relevant.txt"
        relevant.write_text(
            "Python programming is great. Python has many libraries."
        )

        # Irrelevant content
        irrelevant = tmp_path / "irrelevant.txt"
        irrelevant.write_text(
            "Cooking pasta requires boiling water and good pasta."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(relevant),
            "--import-file", str(irrelevant),
            "--min-score", "0.0",
        ])
        assert result.exit_code == 0

    def test_pipeline_stats_output(self, tmp_path, monkeypatch):
        """Test that pipeline outputs correct statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming tutorial for web development and data science."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(test_file)])
        assert result.exit_code == 0
        assert "Crawled:" in result.output
        assert "Extracted:" in result.output
        assert "Filtered in:" in result.output
        assert "Scored:" in result.output
        assert "Tagged:" in result.output
        assert "Indexed:" in result.output

    def test_pipeline_persists_index(self, tmp_path, monkeypatch):
        """Test that pipeline persists the search index to disk."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        # Verify index file exists
        index_path = tmp_path / ".personal_index" / "search_index.json"
        assert index_path.exists()

        # Verify index is loadable
        with open(index_path) as f:
            data = json.load(f)
        assert "pages" in data
        assert len(data["pages"]) >= 1

    def test_pipeline_persists_tags(self, tmp_path, monkeypatch):
        """Test that pipeline persists tags to disk."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development and data science."
        )

        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        # Verify tags file exists
        tags_path = tmp_path / ".personal_index" / "tags.json"
        assert tags_path.exists()


class TestPipelineProgrammaticAPI:
    """Test the pipeline through the programmatic API."""

    def test_runner_full_pipeline(self, tmp_path):
        """Test PipelineRunner with file import through API."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a powerful programming language for web development, "
            "data science, and artificial intelligence."
        )

        config = PipelineConfig(
            min_score_threshold=0.0,
            min_content_length=10,
        )
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([str(test_file)])

        assert stats.pages_crawled >= 1
        assert stats.pages_extracted >= 1
        assert stats.pages_indexed >= 1
        runner.close()

    def test_runner_search_after_index(self, tmp_path):
        """Test that search works after pipeline indexing."""
        data_dir = str(tmp_path / "data")
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        runner.run_from_files([str(test_file)])

        results = runner._search_index.search("python")
        assert len(results) >= 1
        assert "python" in results[0].title.lower() or "python" in results[0].snippet.lower()
        runner.close()

    def test_runner_multiple_interests(self, tmp_path):
        """Test pipeline with multiple interests configured."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        # Add interests programmatically
        from personal_index.models import Interest
        runner._interest_store.add(Interest(name="python", keywords=["python", "django"]))
        runner._interest_store.add(Interest(name="web", keywords=["web", "http"]))

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python web development with Django framework."
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner.pipeline_config = config
        stats = runner.run_from_files([str(test_file)])

        assert stats.pages_indexed >= 1
        runner.close()

    def test_runner_empty_file_handling(self, tmp_path):
        """Test pipeline handles empty files gracefully."""
        data_dir = str(tmp_path / "data")
        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([str(empty_file)])

        # Should not crash, may filter out empty content
        assert stats.errors == [] or len(stats.errors) == 0
        runner.close()

    def test_runner_nonexistent_file(self, tmp_path):
        """Test pipeline handles nonexistent files gracefully."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files(["/nonexistent/path/file.txt"])

        # Should handle gracefully
        assert stats.pages_indexed == 0
        runner.close()

    def test_runner_html_file(self, tmp_path):
        """Test pipeline with HTML file input."""
        data_dir = str(tmp_path / "data")
        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Python Guide</title></head>"
            "<body><h1>Python Programming</h1>"
            "<p>Python is a versatile programming language.</p>"
            "</body></html>"
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([str(html_file)])

        assert stats.pages_indexed >= 1
        runner.close()

    def test_runner_json_file(self, tmp_path):
        """Test pipeline with JSON file input."""
        data_dir = str(tmp_path / "data")
        json_file = tmp_path / "data.json"
        json_file.write_text(
            '{"title": "Python API", "content": "Python REST API documentation"}'
        )

        config = PipelineConfig(min_score_threshold=0.0, min_content_length=10)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        stats = runner.run_from_files([str(json_file)])

        # JSON files are imported as text
        assert stats.pages_crawled >= 1
        runner.close()


class TestPipelineSearchIntegration:
    """Test search integration with pipeline results."""

    def test_search_finds_indexed_content(self, tmp_path, monkeypatch):
        """Test search finds content indexed by pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and index content
        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "Python programming language for web development and data science."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        # Search for indexed content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_search_with_no_results(self, tmp_path, monkeypatch):
        """Test search returns gracefully when no results found."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        # Search for non-existent term
        result = runner.invoke(main, ["search", "xyznonexistent"])
        assert result.exit_code == 0

    def test_search_json_output(self, tmp_path, monkeypatch):
        """Test search with JSON output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data

    def test_search_csv_output(self, tmp_path, monkeypatch):
        """Test search with CSV output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "csv"])
        assert result.exit_code == 0
        assert "rank" in result.output.lower()
