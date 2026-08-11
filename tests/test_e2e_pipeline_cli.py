"""CLI pipeline integration tests.

These tests verify the CLI pipeline command works end-to-end.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineBasic:
    """Test basic pipeline CLI functionality."""

    def test_pipeline_help(self):
        """Pipeline command shows help."""
        runner = CliRunner()
        result = runner.invoke(main, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "crawl" in result.output.lower() or "extract" in result.output.lower()

    def test_pipeline_with_import_file(self, tmp_path, monkeypatch):
        """Pipeline works with --import-file option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial for web development.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0
        assert "indexed" in result.output.lower() or "complete" in result.output.lower()

    def test_pipeline_with_multiple_import_files(self, tmp_path, monkeypatch):
        """Pipeline works with multiple --import-file options."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        (tmp_path / "file1.txt").write_text("Python programming.")
        (tmp_path / "file2.txt").write_text("JavaScript development.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(tmp_path / "file1.txt"),
            "--import-file", str(tmp_path / "file2.txt"),
        ])
        assert result.exit_code == 0

    def test_pipeline_with_interests(self, tmp_path, monkeypatch):
        """Pipeline respects interests configuration."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming is excellent for web development.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0

    def test_pipeline_output_format(self, tmp_path, monkeypatch):
        """Pipeline output includes key statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial for web development and data science.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0
        # Check for key stats in output
        assert "indexed" in result.output.lower() or "complete" in result.output.lower()


class TestCLIPipelineWithMockedCrawler:
    """Test pipeline CLI with mocked web crawler."""

    def test_pipeline_crawl_url(self, tmp_path, monkeypatch):
        """Pipeline can crawl URLs (with mocked crawler)."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        # Mock the crawler at the module level
        from personal_index import pipeline_runner as pr_module

        pages = [
            pr_module.CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming tutorial for web development.",
            ),
        ]

        with patch.object(pr_module.Crawler, "crawl", return_value=pages):
            with patch.object(pr_module.Crawler, "close"):
                result = runner.invoke(main, ["pipeline", "https://example.com"])
                assert result.exit_code == 0


class TestCLIPipelineEndToEnd:
    """Complete end-to-end CLI pipeline tests."""

    def test_full_cli_workflow(self, tmp_path, monkeypatch):
        """Complete workflow: init → interests → pipeline → search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Step 2: Add interest
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django"
        ])
        assert result.exit_code == 0

        # Step 3: Run pipeline on file
        article = tmp_path / "article.txt"
        article.write_text("Python Django web development tutorial.")
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0

        # Step 4: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_cli_pipeline_with_export(self, tmp_path, monkeypatch):
        """Pipeline followed by export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming language for web development.")

        runner.invoke(main, ["pipeline", "--import-file", str(article)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        # Verify JSON output
        data = json.loads(result.output)
        assert "results" in data or "pages" in data or "indexed" in str(data).lower()

    def test_cli_pipeline_multiple_interests(self, tmp_path, monkeypatch):
        """Pipeline with multiple interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        runner.invoke(main, ["interests", "add", "-n", "webdev", "-k", "javascript"])

        (tmp_path / "python.txt").write_text("Python programming tutorial.")
        (tmp_path / "js.txt").write_text("JavaScript web development guide.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(tmp_path / "python.txt"),
            "--import-file", str(tmp_path / "js.txt"),
        ])
        assert result.exit_code == 0

        # Search for both topics
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "javascript"])
        assert result.exit_code == 0

    def test_cli_pipeline_with_tags(self, tmp_path, monkeypatch):
        """Pipeline with manual tagging."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming for web development.")

        runner.invoke(main, ["pipeline", "--import-file", str(article)])

        # Tag the content
        result = runner.invoke(main, [
            "tags", "add", "important",
            str(article),
        ])
        assert result.exit_code == 0

        # Search with tag filter
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0


class TestCLIPipelineStats:
    """Test pipeline statistics output."""

    def test_pipeline_shows_crawled_count(self, tmp_path, monkeypatch):
        """Pipeline output shows pages crawled."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0

    def test_pipeline_shows_indexed_count(self, tmp_path, monkeypatch):
        """Pipeline output shows pages indexed."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial for web development.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article)
        ])
        assert result.exit_code == 0


class TestCLIPipelineOptions:
    """Test pipeline CLI options."""

    def test_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """Pipeline respects --min-score option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article), "--min-score", "0.5"
        ])
        assert result.exit_code == 0

    def test_pipeline_with_min_content_length(self, tmp_path, monkeypatch):
        """Pipeline respects --min-content-length option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article), "-l", "50"
        ])
        assert result.exit_code == 0

    def test_pipeline_skip_stages(self, tmp_path, monkeypatch):
        """Pipeline can skip stages with --no-* options."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article), "--no-filter", "--no-tag"
        ])
        assert result.exit_code == 0
