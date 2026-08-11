"""Comprehensive CLI workflow integration tests.

Tests the complete user journey from initialization through
crawling, indexing, searching, and exporting content.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCompleteWorkflow:
    """Test the complete user workflow end-to-end."""

    def test_init_to_search_workflow(self, tmp_path, monkeypatch):
        """Test the full workflow: init → add interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert ".personal_index" in result.output

        # Step 2: Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "programming",
            "-k", "python", "-k", "javascript", "-k", "rust",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "interests", "add", "-n", "webdev",
            "-k", "html", "-k", "css", "-k", "react",
        ])
        assert result.exit_code == 0

        # Step 3: Verify interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "programming" in result.output
        assert "webdev" in result.output

        # Step 4: Create and import content
        article = tmp_path / "python_web_dev.txt"
        article.write_text(
            "Python web development frameworks include Django and Flask. "
            "Python is a versatile programming language for building web applications. "
            "Many developers use Python for backend development and data processing."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0
        assert "Indexed:" in result.output

        # Step 5: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        # Step 6: Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

        # Step 7: Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Pages indexed:" in result.output

    def test_add_remove_interest_workflow(self, tmp_path, monkeypatch):
        """Test adding and removing interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add interest
        result = runner.invoke(main, [
            "interests", "add", "-n", "test-interest",
            "-k", "test",
        ])
        assert result.exit_code == 0

        # Verify it exists
        result = runner.invoke(main, ["interests", "list"])
        assert "test-interest" in result.output

        # Remove interest
        result = runner.invoke(main, ["interests", "remove", "test-interest"])
        assert result.exit_code == 0

        # Verify it's gone
        result = runner.invoke(main, ["interests", "list"])
        assert "test-interest" not in result.output

    def test_tag_workflow(self, tmp_path, monkeypatch):
        """Test adding and listing tags."""
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
        assert "important" in result.output

    def test_import_search_export_workflow(self, tmp_path, monkeypatch):
        """Test import → search → export workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Import multiple files
        files = []
        for i in range(3):
            f = tmp_path / f"article_{i}.txt"
            f.write_text(
                f"Article {i}: Python programming for web development. "
                f"This article covers Python best practices and patterns."
            )
            files.append(str(f))

        result = runner.invoke(main, ["pipeline"] + [
            item for f in files for item in ["--import-file", f]
        ])
        assert result.exit_code == 0

        # Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Export as JSON
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "pages" in data or "results" in data

        # Export as CSV
        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

        # Export as markdown
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_pipeline_with_custom_options(self, tmp_path, monkeypatch):
        """Test pipeline with various custom options."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development and data science."
        )

        # Test with custom min content length
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "5",
        ])
        assert result.exit_code == 0

        # Test with custom min score
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-score", "0.0",
        ])
        assert result.exit_code == 0

    def test_list_command(self, tmp_path, monkeypatch):
        """Test the list command shows indexed pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

    def test_stats_command(self, tmp_path, monkeypatch):
        """Test the stats command shows statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

    def test_doctor_command(self, tmp_path, monkeypatch):
        """Test the doctor command checks health."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Health Check" in result.output or "Personal Index" in result.output

    def test_clear_command(self, tmp_path, monkeypatch):
        """Test the clear command removes all indexed content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming language for web development."
        )
        runner.invoke(main, ["pipeline", "--import-file", str(test_file)])

        # Verify content exists
        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

        # Clear
        result = runner.invoke(main, ["clear"])
        assert result.exit_code == 0

    def test_version_command(self, tmp_path, monkeypatch):
        """Test the version command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output


class TestCLIEdgeCases:
    """Test CLI edge cases and error handling."""

    def test_pipeline_no_args(self, tmp_path, monkeypatch):
        """Test pipeline command with no arguments."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["pipeline"])
        assert result.exit_code == 1  # Should fail without URLs or files

    def test_search_before_init(self, tmp_path, monkeypatch):
        """Test searching before initialization."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["search", "test"])
        # Should handle gracefully
        assert result.exit_code == 0

    def test_import_binary_file(self, tmp_path, monkeypatch):
        """Test importing a binary file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        binary_file = tmp_path / "binary.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04\x05" * 100)

        result = runner.invoke(main, ["pipeline", "--import-file", str(binary_file)])
        # Should not crash
        assert result.exit_code == 0

    def test_import_unicode_file(self, tmp_path, monkeypatch):
        """Test importing a file with unicode content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        unicode_file = tmp_path / "unicode.txt"
        unicode_file.write_text(
            "Python プログラミング 言語 for web development. "
            "日本語のコンテンツをインデックスします。"
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(unicode_file),
            "--min-content-length", "5",
        ])
        assert result.exit_code == 0

    def test_large_file_import(self, tmp_path, monkeypatch):
        """Test importing a large file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        large_file = tmp_path / "large.txt"
        large_file.write_text(
            "Python programming. " * 10000  # ~200KB
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(large_file)])
        assert result.exit_code == 0

    def test_concurrent_pipeline_runs(self, tmp_path, monkeypatch):
        """Test running pipeline multiple times."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        for i in range(3):
            test_file = tmp_path / f"article_{i}.txt"
            test_file.write_text(
                f"Article {i}: Python programming for web development."
            )
            result = runner.invoke(main, ["pipeline", "--import-file", str(test_file)])
            assert result.exit_code == 0

        # All articles should be indexed
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
