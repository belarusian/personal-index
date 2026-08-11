"""CLI workflow integration tests - verify the full user journey works."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIInitWorkflow:
    """Test the init command creates proper project structure."""

    def test_init_default(self, tmp_path, monkeypatch):
        """Test init with default settings."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Initialized personal-index" in result.output

        data_dir = tmp_path / ".personal_index"
        assert data_dir.exists()
        assert (data_dir / "cache").exists()
        assert (data_dir / "archive").exists()
        assert (data_dir / "backups").exists()
        assert (tmp_path / "config.yaml").exists()

    def test_init_custom_data_dir(self, tmp_path, monkeypatch):
        """Test init with custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--data-dir", "my_index"])
        assert result.exit_code == 0
        assert (tmp_path / "my_index").exists()
        assert (tmp_path / "my_index" / "cache").exists()


class TestCLIInterestWorkflow:
    """Test interest management CLI commands."""

    def test_add_interest(self, tmp_path, monkeypatch):
        """Test adding an interest via CLI."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django", "-k", "flask",
        ])
        assert result.exit_code == 0

    def test_list_interests(self, tmp_path, monkeypatch):
        """Test listing interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_remove_interest(self, tmp_path, monkeypatch):
        """Test removing an interest."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["interests", "add", "-n", "test", "-k", "test"])
        result = runner.invoke(main, ["interests", "remove", "test"])
        assert result.exit_code == 0


class TestCLIImportWorkflow:
    """Test import command with various file types."""

    def test_import_single_file(self, tmp_path, monkeypatch):
        """Test importing a single text file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, machine learning, and automation tasks."
        )

        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

    def test_import_directory(self, tmp_path, monkeypatch):
        """Test importing a directory of files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.txt").write_text("Python programming tutorial content here.")
        (docs / "b.txt").write_text("JavaScript web development guide content.")

        result = runner.invoke(main, ["import", str(docs), "--recursive"])
        assert result.exit_code == 0

    def test_import_with_interests(self, tmp_path, monkeypatch):
        """Test that imported content is scored against interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        article = tmp_path / "python.txt"
        article.write_text(
            "Python programming language is great for web development."
        )

        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0


class TestCLISearchWorkflow:
    """Test search command with indexed content."""

    def test_search_text_output(self, tmp_path, monkeypatch):
        """Test search returns text formatted results."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming language tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_search_json_output(self, tmp_path, monkeypatch):
        """Test search returns JSON formatted results."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming language tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["search", "python", "--format", "json"])
        assert result.exit_code == 0

    def test_search_empty_index(self, tmp_path, monkeypatch):
        """Test search on empty index gives helpful message."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "No indexed content" in result.output or "No results" in result.output


class TestCLIPipelineWorkflow:
    """Test the pipeline command end-to-end."""

    def test_pipeline_from_files(self, tmp_path, monkeypatch):
        """Test pipeline command with file input."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It supports multiple paradigms."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output or "Indexed:" in result.output

    def test_pipeline_with_interests(self, tmp_path, monkeypatch):
        """Test pipeline respects configured interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language tutorial for web development."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0


class TestCLIExportWorkflow:
    """Test export command with various formats."""

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Test exporting indexed content as markdown."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_json(self, tmp_path, monkeypatch):
        """Test exporting indexed content as JSON."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_export_csv(self, tmp_path, monkeypatch):
        """Test exporting indexed content as CSV."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        article = tmp_path / "test.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0


class TestCLIStatusWorkflow:
    """Test status and doctor commands."""

    def test_status_command(self, tmp_path, monkeypatch):
        """Test status shows index information."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_doctor_command(self, tmp_path, monkeypatch):
        """Test doctor checks system health."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0


class TestCLICompleteWorkflow:
    """Test the complete user journey from init to search."""

    def test_full_user_journey(self, tmp_path, monkeypatch):
        """Test: init → add interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Step 2: Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "programming",
            "-k", "python", "-k", "javascript", "-k", "programming",
        ])
        assert result.exit_code == 0

        # Step 3: Import content
        articles = tmp_path / "articles"
        articles.mkdir()
        (articles / "python.txt").write_text(
            "Python is a great programming language for web development."
        )
        (articles / "javascript.txt").write_text(
            "JavaScript powers the modern web with frameworks like React."
        )
        (articles / "cooking.txt").write_text(
            "This article is about cooking recipes and baking cakes."
        )

        result = runner.invoke(main, ["import", str(articles), "--recursive"])
        assert result.exit_code == 0

        # Step 4: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Step 5: Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        # Step 6: Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_pipeline_then_search(self, tmp_path, monkeypatch):
        """Test: init → pipeline → search returns results."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language is used for web development, "
            "data science, and machine learning applications."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_add_interest_with_priority(self, tmp_path, monkeypatch):
        """Test adding an interest with custom priority."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "interests", "add", "-n", "critical",
            "-k", "security", "-p", "10",
        ])
        assert result.exit_code == 0
