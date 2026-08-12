"""Tests for personal_index CLI with custom data directories."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIDataDir:
    """Test CLI commands with --data-dir option."""

    def test_init_custom_data_dir(self, tmp_path, monkeypatch):
        """Test init with custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--data-dir", "custom_index"])
        assert result.exit_code == 0
        assert (tmp_path / "custom_index").exists()

    def test_import_with_data_dir(self, tmp_path, monkeypatch):
        """Test import with custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init", "--data-dir", "custom_index"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        result = runner.invoke(main, ["import", str(test_file), "--data-dir", "custom_index"])
        assert result.exit_code == 0

    def test_search_with_data_dir(self, tmp_path, monkeypatch):
        """Test search with custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init", "--data-dir", "custom_index"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file), "--data-dir", "custom_index"])

        result = runner.invoke(main, ["search", "python", "--data-dir", "custom_index"])
        assert result.exit_code == 0

    def test_export_with_data_dir(self, tmp_path, monkeypatch):
        """Test export with custom data directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init", "--data-dir", "custom_index"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file), "--data-dir", "custom_index"])

        result = runner.invoke(main, ["export", "--format", "json", "--data-dir", "custom_index"])
        assert result.exit_code == 0
