"""Tests for personal_index init command."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from personal_index.cli import main


class TestInitCommand:
    """Test the init command creates index directory structure."""

    def test_init_creates_default_directory(self, tmp_path, monkeypatch):
        """Test init creates .personal_index directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert Path(".personal_index").exists()

    def test_init_creates_subdirectories(self, tmp_path, monkeypatch):
        """Test init creates cache, archive, backups subdirectories."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / ".personal_index" / "cache").exists()
        assert (tmp_path / ".personal_index" / "archive").exists()
        assert (tmp_path / ".personal_index" / "backups").exists()

    def test_init_creates_config_file(self, tmp_path, monkeypatch):
        """Test init creates config.yaml."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "config.yaml").exists()

    def test_init_with_custom_dir(self, tmp_path, monkeypatch):
        """Test init with --data-dir option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--data-dir", "my_index"])
        assert result.exit_code == 0
        assert (tmp_path / "my_index").exists()
        assert (tmp_path / "my_index" / "cache").exists()
