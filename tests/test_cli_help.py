"""Tests for personal_index --help command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestHelpCommand:
    """Test the --help command shows available commands."""

    def test_help_shows_available_commands(self):
        """Test that --help displays all available commands."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "init" in result.output
        assert "crawl" in result.output
        assert "search" in result.output
        assert "export" in result.output

    def test_help_shows_description(self):
        """Test that --help shows a description of the tool."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Personal Index" in result.output
