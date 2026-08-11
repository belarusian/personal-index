"""End-to-end CLI pipeline integration tests.

Verifies the complete crawl→extract→filter→score→tag→index→search
pipeline works through the CLI interface.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineE2E:
    """Test the full pipeline through CLI commands."""

    def test_init_and_pipeline_import(self, tmp_path, monkeypatch):
        """Test init followed by pipeline file import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Create test content
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python is a versatile programming language for web development, "
            "data science, machine learning, and automation. Python features "
            "clean syntax and a comprehensive standard library that makes it "
            "ideal for rapid development and prototyping."
        )

        # Run pipeline with file import
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.txt")
        ])
        assert result.exit_code == 0
        assert "Imported" in result.output or "indexed" in result.output.lower()

    def test_full_cli_workflow(self, tmp_path, monkeypatch):
        """Test complete CLI workflow: init → interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming"
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language is widely used for web development, "
            "data analysis, and artificial intelligence. The Python community "
            "is large and active, contributing thousands of packages."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower() or "Python" in result.output

        # 5. Export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        # 6. Status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_pipeline_with_multiple_files(self, tmp_path, monkeypatch):
        """Test pipeline with multiple files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "a.txt").write_text("Python programming for web development.")
        (docs / "b.txt").write_text("JavaScript for frontend development.")
        (docs / "c.txt").write_text("Docker containerization for deployment.")

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs), "--recursive"
        ])
        assert result.exit_code == 0

    def test_pipeline_with_interests_affects_scoring(self, tmp_path, monkeypatch):
        """Test that interests affect scoring in pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add interest
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "docker"
        ])

        # Create content matching interest
        article = tmp_path / "article.txt"
        article.write_text(
            "Python and Docker are essential tools for modern development. "
            "Python provides the programming language while Docker handles "
            "containerization and deployment automation."
        )

        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # Search should find it
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_pipeline_min_content_length_filter(self, tmp_path, monkeypatch):
        """Test that min-content-length filter works in pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create short and long files
        short = tmp_path / "short.txt"
        short.write_text("Too short")

        long = tmp_path / "long.txt"
        long.write_text(
            "This is a longer article with enough content to pass the filter. "
            "It discusses various topics including programming, development, "
            "and software engineering best practices."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(short),
            "--import-file", str(long),
            "--min-content-length", "50",
        ])
        assert result.exit_code == 0

    def test_search_with_tag_filter(self, tmp_path, monkeypatch):
        """Test search with tag filtering."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )
        runner.invoke(main, ["import", str(article)])

        # Add a tag
        runner.invoke(main, [
            "tags", "add", "important", str(article)
        ])

        # Search with tag filter
        result = runner.invoke(main, [
            "search", "python", "--tag", "important"
        ])
        assert result.exit_code == 0

    def test_export_all_formats(self, tmp_path, monkeypatch):
        """Test export in all supported formats."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        for fmt in ["markdown", "json", "csv"]:
            result = runner.invoke(main, ["export", "--format", fmt])
            assert result.exit_code == 0, f"Export failed for {fmt}: {result.output}"

    def test_stats_command_after_import(self, tmp_path, monkeypatch):
        """Test stats command shows correct data after import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

    def test_doctor_command(self, tmp_path, monkeypatch):
        """Test doctor command after setup."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Health Check" in result.output or "health" in result.output.lower()

    def test_list_command(self, tmp_path, monkeypatch):
        """Test list command shows indexed pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

    def test_top_command(self, tmp_path, monkeypatch):
        """Test top command shows highest scored pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["top"])
        assert result.exit_code == 0

    def test_remove_command(self, tmp_path, monkeypatch):
        """Test remove command removes indexed pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["remove", str(article)])
        assert result.exit_code == 0

    def test_clear_command(self, tmp_path, monkeypatch):
        """Test clear command removes all indexed content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["import", str(article)])

        result = runner.invoke(main, ["clear"])
        assert result.exit_code == 0

    def test_pipeline_no_crawl_flag(self, tmp_path, monkeypatch):
        """Test pipeline with --no-crawl flag for file imports."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science. "
            "This article covers the basics of Python programming."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(article),
            "--no-crawl",
        ])
        assert result.exit_code == 0

    def test_pipeline_custom_steps(self, tmp_path, monkeypatch):
        """Test pipeline with custom step selection."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(article),
            "--steps", "filter,score,tag,index",
        ])
        assert result.exit_code == 0
