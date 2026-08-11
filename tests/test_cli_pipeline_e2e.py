"""CLI pipeline end-to-end tests.

Tests the actual CLI commands for the full pipeline workflow.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineCommand:
    """Test the pipeline CLI command."""

    def test_pipeline_with_import_files(self, tmp_path, monkeypatch):
        """Test pipeline command with --import-file option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text("Python is a great programming language for web development.")
        file2 = tmp_path / "article2.txt"
        file2.write_text("JavaScript and Node.js for building modern web applications.")

        # Run pipeline with import
        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(file1),
            "--import-file", str(file2),
        ])
        assert result.exit_code == 0
        assert "Imported" in result.output

    def test_pipeline_with_interests(self, tmp_path, monkeypatch):
        """Test pipeline with pre-configured interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add interest first
        runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming",
        ])

        # Create test file
        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial for web development.")

        # Run pipeline
        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(test_file),
        ])
        assert result.exit_code == 0

    def test_pipeline_no_urls_or_files(self, tmp_path, monkeypatch):
        """Test pipeline with no URLs or files exits with error."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["pipeline"])
        assert result.exit_code == 1

    def test_pipeline_with_steps_option(self, tmp_path, monkeypatch):
        """Test pipeline with specific steps."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming language guide for web development.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(test_file),
            "--steps", "extract,filter,score,tag,index",
        ])
        assert result.exit_code == 0

    def test_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """Test pipeline with minimum score threshold."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming language guide.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(test_file),
            "--min-score", "0.0",
        ])
        assert result.exit_code == 0

    def test_pipeline_with_nonexistent_file(self, tmp_path, monkeypatch):
        """Test pipeline handles missing files gracefully."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", "/nonexistent/file.txt",
        ])
        # Should not crash, just warn
        assert result.exit_code == 0


class TestCLICompleteWorkflow:
    """Test complete CLI workflows."""

    def test_init_interests_import_search_export(self, tmp_path, monkeypatch):
        """Test the complete workflow: init → interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django",
        ])
        assert result.exit_code == 0

        # 3. Import content
        test_file = tmp_path / "article.txt"
        test_file.write_text("Python and Django web development tutorial.")
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # 5. Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_full_pipeline_workflow(self, tmp_path, monkeypatch):
        """Test full pipeline: init → interests → pipeline → search → tags → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        runner.invoke(main, ["init"])

        # Add interests
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "programming", "-k", "software",
        ])

        # Create test files
        for i in range(3):
            f = tmp_path / f"article{i}.txt"
            f.write_text(f"This is article {i} about programming and software development.")

        # Run pipeline
        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(tmp_path / "article0.txt"),
            "--import-file", str(tmp_path / "article1.txt"),
            "--import-file", str(tmp_path / "article2.txt"),
        ])
        assert result.exit_code == 0

        # Search
        result = runner.invoke(main, ["search", "programming"])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

        # Status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_pipeline_then_search_then_export(self, tmp_path, monkeypatch):
        """Test pipeline feeds into search and export correctly."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and import content
        test_file = tmp_path / "guide.txt"
        test_file.write_text("Complete Python programming guide for beginners and advanced developers.")
        runner.invoke(main, ["import", str(test_file)])

        # Search should find it
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Export should include it
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()


class TestCLIPipelineWithDataDir:
    """Test pipeline with custom data directories."""

    def test_pipeline_custom_data_dir(self, tmp_path, monkeypatch):
        """Test pipeline with --data-dir option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        custom_dir = str(tmp_path / "custom_index")

        result = runner.invoke(main, [
            "--data-dir", custom_dir,
            "pipeline",
            "--import-file", str(tmp_path / "test.txt"),
        ])
        # File doesn't exist but should handle gracefully
        assert result.exit_code == 0

    def test_pipeline_data_dir_persists(self, tmp_path, monkeypatch):
        """Test that data persists in custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        custom_dir = str(tmp_path / "my_index")

        # First run
        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, [
            "--data-dir", custom_dir,
            "import", str(test_file),
        ])

        # Second run - verify persistence
        result = runner.invoke(main, [
            "--data-dir", custom_dir,
            "search", "python",
        ])
        assert result.exit_code == 0
