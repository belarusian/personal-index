"""End-to-end CLI tests for the pipeline command."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineE2E:
    """Test the pipeline CLI command end-to-end."""

    def test_pipeline_import_file(self, tmp_path, monkeypatch):
        """Test pipeline command with file import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init first
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Create test file
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "# My Article\n\n"
            "This is a test article about programming and software development. "
            "It contains enough content to pass the filter."
        )

        # Run pipeline
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output
        assert "Indexed:" in result.output

    def test_pipeline_import_multiple_files(self, tmp_path, monkeypatch):
        """Test pipeline with multiple file imports."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])

        files = []
        for i in range(3):
            f = tmp_path / f"doc_{i}.txt"
            f.write_text(f"# Doc {i}\n\nContent about topic {i}.")
            files.append(str(f))

        result = cli_runner.invoke(main, [
            "pipeline",
            "--import-file", files[0],
            "--import-file", files[1],
            "--import-file", files[2],
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0
        assert "Crawled:" in result.output

    def test_pipeline_then_search(self, tmp_path, monkeypatch):
        """Test pipeline followed by search."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])

        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "# Python Guide\n\n"
            "Python is a great programming language for beginners."
        )

        cli_runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = cli_runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output

    def test_pipeline_with_interests(self, tmp_path, monkeypatch):
        """Test pipeline with pre-configured interests."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])

        # Add interest
        cli_runner.invoke(main, [
            "interests", "add", "tech",
            "-k", "programming", "-k", "software",
        ])

        test_file = tmp_path / "tech.txt"
        test_file.write_text(
            "# Tech Article\n\n"
            "Software programming is essential in modern development."
        )

        result = cli_runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0
        assert "Tagged:" in result.output

    def test_pipeline_no_urls_or_files(self, tmp_path, monkeypatch):
        """Test pipeline with no input exits with error."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])
        result = cli_runner.invoke(main, ["pipeline"])
        assert result.exit_code == 1
        assert "No URLs or files specified" in result.output

    def test_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """Test pipeline with minimum score threshold."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Article\n\nSome content here.")

        result = cli_runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-score", "0.0",
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0

    def test_pipeline_skip_steps(self, tmp_path, monkeypatch):
        """Test pipeline with specific steps."""
        monkeypatch.chdir(tmp_path)
        cli_runner = CliRunner()

        cli_runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Article\n\nContent about testing.")

        result = cli_runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--steps", "extract,filter,score,tag,index",
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0
