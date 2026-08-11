"""End-to-end CLI tests for export command."""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIExportE2E:
    """Test export CLI commands end-to-end."""

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Test exporting index as markdown."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create and index a file
        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_json(self, tmp_path, monkeypatch):
        """Test exporting index as JSON."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_export_csv(self, tmp_path, monkeypatch):
        """Test exporting index as CSV."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content for export.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0

    def test_export_empty_index(self, tmp_path, monkeypatch):
        """Test exporting an empty index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
