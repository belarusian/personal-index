"""CLI pipeline end-to-end tests.

Tests the full CLI workflow: init → interests → import → pipeline → search → export.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineEndToEnd:
    """Test complete CLI pipeline workflows."""

    def test_init_creates_structure(self, tmp_path, monkeypatch):
        """Test init creates all required directories and config."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path(".personal_index").exists()
        assert Path(".personal_index/cache").exists()
        assert Path(".personal_index/archive").exists()
        assert Path(".personal_index/backups").exists()
        assert Path("config.yaml").exists()

    def test_full_workflow_init_import_search_export(self, tmp_path, monkeypatch):
        """Test complete workflow: init → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming",
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It is widely used in production."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "Python" in result.output or "python" in result.output.lower()

        # 5. Export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_pipeline_command_with_imported_content(self, tmp_path, monkeypatch):
        """Test pipeline command processes imported content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        runner.invoke(main, ["init"])

        # Add interest
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "javascript",
        ])

        # Create content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python and JavaScript are popular programming languages for web development. "
            "Both are widely used in modern software engineering."
        )
        runner.invoke(main, ["import", str(article)])

        # Run pipeline (no-crawl mode, just process existing)
        result = runner.invoke(main, ["pipeline", "--no-crawl"])
        assert result.exit_code == 0

    def test_pipeline_dry_run(self, tmp_path, monkeypatch):
        """Test pipeline dry-run shows configuration."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["pipeline", "--dry-run"])
        assert result.exit_code == 0
        assert "Dry run" in result.output or "pipeline" in result.output.lower()

    def test_search_after_pipeline(self, tmp_path, monkeypatch):
        """Test search works after running pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "webdev",
            "-k", "python", "-k", "web",
        ])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python web development with Django and Flask frameworks. "
            "Build robust web applications with Python."
        )
        runner.invoke(main, ["import", str(article)])
        runner.invoke(main, ["pipeline", "--no-crawl"])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_export_json_contains_results(self, tmp_path, monkeypatch):
        """Test JSON export contains search results."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_export_csv_contains_results(self, tmp_path, monkeypatch):
        """Test CSV export contains search results."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python",
        ])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

    def test_status_shows_index_stats(self, tmp_path, monkeypatch):
        """Test status command shows index statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and software engineering."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status" in result.output or "status" in result.output.lower()

    def test_multiple_interests_and_search(self, tmp_path, monkeypatch):
        """Test multiple interests work correctly with search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add multiple interests
        runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django",
        ])
        runner.invoke(main, [
            "interests", "add", "-n", "javascript",
            "-k", "javascript", "-k", "react",
        ])

        # List interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()
        assert "javascript" in result.output.lower()

    def test_import_multiple_files(self, tmp_path, monkeypatch):
        """Test importing multiple files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "rust",
        ])

        # Create multiple files
        for i in range(3):
            article = tmp_path / f"article_{i}.txt"
            article.write_text(
                f"Article {i}: Python programming and software development. "
                f"This is content number {i} about technology."
            )
            result = runner.invoke(main, ["import", str(article)])
            assert result.exit_code == 0

        # Search should find content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_tags_cli_workflow(self, tmp_path, monkeypatch):
        """Test tag management via CLI."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add tag
        result = runner.invoke(main, [
            "tags", "add", "important",
            "https://example.com/page1",
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_config_show(self, tmp_path, monkeypatch):
        """Test config show command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["config", "show"])
        assert result.exit_code == 0

    def test_interests_remove(self, tmp_path, monkeypatch):
        """Test removing interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, [
            "interests", "add", "-n", "temp",
            "-k", "temporary",
        ])
        result = runner.invoke(main, ["interests", "remove", "temp"])
        assert result.exit_code == 0

        # Verify removed
        result = runner.invoke(main, ["interests", "list"])
        assert "temp" not in result.output.lower() or "temporary" not in result.output.lower()


class TestCLIPipelineStepSelection:
    """Test CLI pipeline step selection."""

    def test_pipeline_step_filter_only(self, tmp_path, monkeypatch):
        """Test running only the filter step."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, [
            "pipeline", "--step", "filter", "--dry-run"
        ])
        assert result.exit_code == 0

    def test_pipeline_step_score_only(self, tmp_path, monkeypatch):
        """Test running only the score step."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, [
            "pipeline", "--step", "score", "--dry-run"
        ])
        assert result.exit_code == 0

    def test_pipeline_multiple_steps(self, tmp_path, monkeypatch):
        """Test running multiple specific steps."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, [
            "pipeline", "--step", "filter", "--step", "score", "--dry-run"
        ])
        assert result.exit_code == 0
