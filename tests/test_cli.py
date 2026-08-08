"""Tests for CLI interface."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from personal_index.cli.main import cli
from personal_index.config import AppConfig, Interest


class TestInterestCommands:
    def setup_method(self) -> None:
        self.runner = CliRunner()
        self.config_dir = None

    def test_add_interest(self, tmp_path: Path) -> None:
        self.config_dir = str(tmp_path)
        result = self.runner.invoke(
            cli,
            [
                "interest", "add",
                "--topic", "Machine Learning",
                "--keywords", "ml",
                "--keywords", "deep learning",
                "--priority", "8",
                "--config-dir", self.config_dir,
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: Machine Learning" in result.output

    def test_add_interest_with_url_pattern(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            [
                "interest", "add",
                "--topic", "Tech News",
                "--url-pattern", "https://techcrunch.com/*",
                "--config-dir", str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: Tech News" in result.output

    def test_list_interests_empty(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            ["interest", "list", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "No interests configured" in result.output

    def test_list_interests(self, tmp_path: Path) -> None:
        # Add an interest first
        self.runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", str(tmp_path)],
        )
        result = self.runner.invoke(
            cli,
            ["interest", "list", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "AI" in result.output

    def test_remove_interest(self, tmp_path: Path) -> None:
        self.runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", str(tmp_path)],
        )
        result = self.runner.invoke(
            cli,
            ["interest", "remove", "--topic", "AI", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Removed interest: AI" in result.output

    def test_remove_nonexistent_interest(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            ["interest", "remove", "--topic", "Nonexistent", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_duplicate_interest(self, tmp_path: Path) -> None:
        self.runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", str(tmp_path)],
        )
        result = self.runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "already exists" in result.output


class TestSearchCommand:
    def test_search_empty_index(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            ["search", "test", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "No results" in result.output


class TestStatusCommand:
    def test_status(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            ["status", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Personal Index Status" in result.output


class TestStatsCommand:
    def test_stats(self, tmp_path: Path) -> None:
        result = self.runner.invoke(
            cli,
            ["stats", "--config-dir", str(tmp_path)],
        )
        assert result.exit_code == 0
        assert "Index Statistics" in result.output


class TestVersion:
    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
