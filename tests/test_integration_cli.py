"""Integration tests for CLI commands."""

from __future__ import annotations

import os
import tempfile

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIInit:
    """Test CLI init command."""

    def test_init_creates_data_dir(self, tmp_path):
        runner = CliRunner()
        data_dir = str(tmp_path / "my_data")
        result = runner.invoke(main, ["init", "--data-dir", data_dir])
        assert result.exit_code == 0
        assert os.path.isdir(data_dir)

    def test_init_creates_config(self, tmp_path):
        runner = CliRunner()
        data_dir = str(tmp_path / "my_data")
        config_file = str(tmp_path / "config.yaml")
        result = runner.invoke(main, ["init", "--data-dir", data_dir, "--config", config_file])
        assert result.exit_code == 0
        assert os.path.isfile(config_file)


class TestCLIInterests:
    """Test CLI interests commands."""

    def test_add_interest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["interests", "add", "-n", "Python", "-k", "python", "-k", "programming"])
        assert result.exit_code == 0
        assert "Added interest: Python" in result.output

    def test_list_interests_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "No interests" in result.output

    def test_add_and_list_interest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["interests", "add", "-n", "AI", "-k", "artificial", "-k", "intelligence"])
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "AI" in result.output

    def test_remove_interest(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["interests", "add", "-n", "Test", "-k", "test"])
        result = runner.invoke(main, ["interests", "remove", "Test"])
        assert result.exit_code == 0
        assert "Removed interest: Test" in result.output


class TestCLISearch:
    """Test CLI search command."""

    def test_search_no_results(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["search", "nonexistent"])
        assert result.exit_code == 0


class TestCLIStatus:
    """Test CLI status command."""

    def test_status_runs(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Personal Index Status" in result.output


class TestCLIPipeline:
    """Test CLI pipeline command."""

    def test_pipeline_dry_run(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["pipeline", "--dry-run", "https://example.com"])
        assert result.exit_code == 0
        assert "Dry run mode" in result.output


class TestCLIImport:
    """Test CLI import command."""

    def test_import_file(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        # Create a test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("This is test content for importing.")
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0
        assert "Imported" in result.output

    def test_import_directory_recursive(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        # Create test files
        subdir = tmp_path / "docs"
        subdir.mkdir()
        (subdir / "file1.txt").write_text("File one content.")
        (subdir / "file2.txt").write_text("File two content.")
        result = runner.invoke(main, ["import", str(subdir), "--recursive"])
        assert result.exit_code == 0
        assert "Imported" in result.output


class TestCLIExport:
    """Test CLI export command."""

    def test_export_markdown_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0


class TestCLITag:
    """Test CLI tag commands."""

    def test_tag_list_empty(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["tag", "list"])
        assert result.exit_code == 0

    def test_tag_add(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["tag", "add", "important", "--color", "#ff0000"])
        assert result.exit_code == 0
        assert "Added tag: important" in result.output
