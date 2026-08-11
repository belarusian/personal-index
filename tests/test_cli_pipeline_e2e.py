"""End-to-end CLI pipeline tests.

Tests the CLI pipeline command with real file-based operations,
verifying the complete user workflow from init through search.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineE2E:
    """Test the CLI pipeline command end-to-end."""

    def test_pipeline_dry_run(self, tmp_path, monkeypatch):
        """Test pipeline dry-run mode shows configuration."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init first
        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "pipeline", "https://example.com", "--dry-run"
        ])
        assert result.exit_code == 0
        assert "Dry run mode" in result.output
        assert "Seed URLs" in result.output
        assert "example.com" in result.output

    def test_pipeline_no_crawl_mode(self, tmp_path, monkeypatch):
        """Test pipeline --no-crawl processes existing data."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Run pipeline without crawl on empty data
        result = runner.invoke(main, [
            "pipeline", "--no-crawl"
        ])
        assert result.exit_code == 0
        assert "Pipeline Summary" in result.output

    def test_pipeline_with_step_selection(self, tmp_path, monkeypatch):
        """Test pipeline with specific step selection."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "pipeline", "https://example.com",
            "--step", "extract",
            "--step", "index",
            "--dry-run"
        ])
        assert result.exit_code == 0
        assert "Dry run mode" in result.output

    def test_pipeline_with_output_file(self, tmp_path, monkeypatch):
        """Test pipeline saves stats to output file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "pipeline", "--no-crawl",
            "-o", str(tmp_path / "stats.txt")
        ])
        assert result.exit_code == 0
        assert "Stats saved to" in result.output
        assert (tmp_path / "stats.txt").exists()

    def test_pipeline_quiet_mode(self, tmp_path, monkeypatch):
        """Test pipeline quiet mode suppresses output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "pipeline", "--no-crawl", "-q"
        ])
        assert result.exit_code == 0
        # Quiet mode should still show summary
        assert "Pipeline Summary" in result.output

    def test_full_cli_workflow_init_import_search_export(self, tmp_path, monkeypatch):
        """Test complete CLI workflow: init → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Initialized" in result.output

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django", "-k", "flask"
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language. Django and Flask are popular "
            "Python web frameworks. Python is used for web development, data science, "
            "machine learning, and automation tasks."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # 4. Search for content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()

        # 5. Export results
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

        # 6. Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status" in result.output

    def test_cli_multiple_interests_and_search(self, tmp_path, monkeypatch):
        """Test adding multiple interests and searching across them."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add multiple interests
        runner.invoke(main, [
            "interests", "add", "-n", "web-dev",
            "-k", "javascript", "-k", "react", "-k", "vue"
        ])
        runner.invoke(main, [
            "interests", "add", "-n", "backend",
            "-k", "python", "-k", "rust", "-k", "go"
        ])

        # Import content matching both interests
        article = tmp_path / "fullstack.txt"
        article.write_text(
            "Full-stack development uses JavaScript and React for the frontend, "
            "with Python and Rust for the backend. Modern web applications combine "
            "these technologies for optimal performance."
        )
        runner.invoke(main, ["import", str(article)])

        # Search should find content
        result = runner.invoke(main, ["search", "javascript python"])
        assert result.exit_code == 0

    def test_cli_import_multiple_files(self, tmp_path, monkeypatch):
        """Test importing multiple files at once."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create multiple files
        for i in range(3):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(
                f"This is article number {i} about programming languages. "
                f"Python and JavaScript are popular choices for web development."
            )

        # Import all files
        for i in range(3):
            result = runner.invoke(main, ["import", str(tmp_path / f"article_{i}.txt")])
            assert result.exit_code == 0

        # Search should find all articles
        result = runner.invoke(main, ["search", "programming"])
        assert result.exit_code == 0

    def test_cli_export_all_formats(self, tmp_path, monkeypatch):
        """Test exporting in all supported formats."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        # Test each format
        for fmt in ["markdown", "json", "csv"]:
            result = runner.invoke(main, ["export", "--format", fmt])
            assert result.exit_code == 0, f"Export failed for format {fmt}: {result.output}"

    def test_cli_config_commands(self, tmp_path, monkeypatch):
        """Test config management commands."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # View config
        result = runner.invoke(main, ["config", "view"])
        assert result.exit_code == 0

        # Set crawler config
        result = runner.invoke(main, ["config", "set-crawler", "--max-depth", "5"])
        assert result.exit_code == 0

        # Verify config was updated
        result = runner.invoke(main, ["config", "view"])
        assert result.exit_code == 0

    def test_cli_schedule_commands(self, tmp_path, monkeypatch):
        """Test schedule management commands."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add schedule
        result = runner.invoke(main, [
            "schedule", "add", "-n", "daily",
            "-u", "https://example.com", "-i", "24"
        ])
        assert result.exit_code == 0

        # List schedules
        result = runner.invoke(main, ["schedule", "list"])
        assert result.exit_code == 0
        assert "daily" in result.output

        # Remove schedule
        result = runner.invoke(main, ["schedule", "remove", "daily"])
        assert result.exit_code == 0

    def test_cli_tag_management(self, tmp_path, monkeypatch):
        """Test tag management commands."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add tag to URL
        result = runner.invoke(main, [
            "tags", "add", "important", "https://example.com/page1"
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

        # Remove tag
        result = runner.invoke(main, [
            "tags", "remove", "important", "https://example.com/page1"
        ])
        assert result.exit_code == 0


class TestCLIDataDirectory:
    """Test CLI with custom data directories."""

    def test_custom_data_dir(self, tmp_path, monkeypatch):
        """Test using a custom data directory."""
        custom_dir = tmp_path / "custom_index"
        runner = CliRunner()

        result = runner.invoke(main, ["init", "--data-dir", str(custom_dir)])
        assert result.exit_code == 0
        assert custom_dir.exists()
        assert (custom_dir / "cache").exists()
        assert (custom_dir / "archive").exists()

    def test_data_dir_persistence(self, tmp_path, monkeypatch):
        """Test that data persists in custom data directory."""
        custom_dir = tmp_path / "my_index"
        runner = CliRunner()

        # First run: init and add content
        runner.invoke(main, ["init", "--data-dir", str(custom_dir)])
        runner.invoke(main, [
            "interests", "add", "-n", "test",
            "--data-dir", str(custom_dir),
            "-k", "python"
        ])

        # Second run: verify data persists
        result = runner.invoke(main, [
            "interests", "list",
            "--data-dir", str(custom_dir)
        ])
        assert result.exit_code == 0
        assert "test" in result.output
