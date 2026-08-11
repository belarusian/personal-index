"""End-to-end CLI pipeline integration tests.

Tests the complete CLI workflow: init → interests → pipeline → search → export.
These tests use the Click test runner to verify the CLI works end-to-end.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIEndToEndPipeline:
    """Test the complete CLI pipeline workflow."""

    def test_full_cli_workflow_init_import_search_export(self, tmp_path, monkeypatch):
        """Test: init → import → search → export (complete workflow)."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert ".personal_index" in result.output

        # Step 2: Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming", "-k", "development",
        ])
        assert result.exit_code == 0

        # Step 3: Create test content
        article = tmp_path / "python_guide.txt"
        article.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. Python supports multiple programming paradigms "
            "including procedural, object-oriented, and functional programming."
        )

        # Step 4: Import
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # Step 5: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()

        # Step 6: Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data or "pages" in data

    def test_cli_pipeline_with_import_file(self, tmp_path, monkeypatch):
        """Test pipeline command with --import-file option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        runner.invoke(main, ["init"])

        # Add interest
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "javascript", "-k", "web",
        ])

        # Create test files
        file1 = tmp_path / "article1.txt"
        file1.write_text(
            "Python web development with Django and Flask frameworks. "
            "These are popular Python web frameworks for building APIs."
        )
        file2 = tmp_path / "article2.txt"
        file2.write_text(
            "JavaScript is the language of the web. React and Vue are "
            "popular JavaScript frameworks for frontend development."
        )

        # Run pipeline with import files
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(file1), "--import-file", str(file2),
            "--min-content-length", "10",
        ])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output or "Indexed:" in result.output

    def test_cli_search_with_tag_filter(self, tmp_path, monkeypatch):
        """Test search with tag filtering."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and import content
        article = tmp_path / "test.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )
        runner.invoke(main, ["import", str(article)])

        # Add a tag
        runner.invoke(main, ["tags", "add", "important", "file://" + str(article)])

        # Search with tag filter
        result = runner.invoke(main, ["search", "python", "--tag", "important"])
        assert result.exit_code == 0

    def test_cli_export_multiple_formats(self, tmp_path, monkeypatch):
        """Test exporting in all supported formats."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text(
            "Python programming for web development."
        )
        runner.invoke(main, ["import", str(article)])

        # Export as JSON
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        # Export as markdown
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        # Export as CSV
        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

    def test_cli_doctor_command(self, tmp_path, monkeypatch):
        """Test the doctor diagnostic command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Health Check" in result.output or "Index:" in result.output

    def test_cli_interests_full_lifecycle(self, tmp_path, monkeypatch):
        """Test full interest lifecycle: add, list, remove."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add multiple interests
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        runner.invoke(main, ["interests", "add", "-n", "rust", "-k", "rust"])

        # List
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()
        assert "rust" in result.output.lower()

        # Remove one
        result = runner.invoke(main, ["interests", "remove", "rust"])
        assert result.exit_code == 0

        # Verify removal
        result = runner.invoke(main, ["interests", "list"])
        assert "python" in result.output.lower()
        assert "rust" not in result.output.lower()

    def test_cli_search_json_format(self, tmp_path, monkeypatch):
        """Test search output in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data
        assert len(data["results"]) >= 1

    def test_cli_search_csv_format(self, tmp_path, monkeypatch):
        """Test search output in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "--format", "csv"])
        assert result.exit_code == 0
        assert "rank" in result.output.lower() or "title" in result.output.lower()

    def test_cli_pipeline_no_urls_shows_help(self, tmp_path, monkeypatch):
        """Test that pipeline without URLs shows usage info."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["pipeline"])
        # Should exit with error or show usage
        assert result.exit_code != 0 or "Usage" in result.output or "No URLs" in result.output

    def test_cli_version_flag(self, tmp_path, monkeypatch):
        """Test version flag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
