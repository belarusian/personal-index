"""Tests for personal_index CLI subcommands."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestCLISubcommands:
    """Test CLI subcommands like interests, tags, status."""

    def test_interests_add(self, tmp_path, monkeypatch):
        """Test adding an interest."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, [
            "interests", "add", "-n", "python", "-k", "python", "-k", "django"
        ])
        assert result.exit_code == 0

    def test_interests_list(self, tmp_path, monkeypatch):
        """Test listing interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0

    def test_tags_add(self, tmp_path, monkeypatch):
        """Test adding a tag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["tags", "add", "important", "https://example.com"])
        assert result.exit_code == 0

    def test_tags_list(self, tmp_path, monkeypatch):
        """Test listing tags."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["tags", "add", "important", "https://example.com"])
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_status_after_init(self, tmp_path, monkeypatch):
        """Test status command after init."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Indexed pages" in result.output or "indexed" in result.output.lower()
