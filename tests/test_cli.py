"""Tests for CLI interface."""

import pytest
from pathlib import Path
from click.testing import CliRunner
from personal_index.cli.main import cli
from personal_index.config import AppConfig, Interest


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def config_dir(tmp_path: Path) -> str:
    return str(tmp_path)


class TestInterestCommands:
    def test_add_interest(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            [
                "interest", "add",
                "--topic", "Machine Learning",
                "--keywords", "ml",
                "--keywords", "deep learning",
                "--priority", "8",
                "--config-dir", config_dir,
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: Machine Learning" in result.output

    def test_add_interest_with_url_pattern(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            [
                "interest", "add",
                "--topic", "Tech News",
                "--url-pattern", "https://techcrunch.com/*",
                "--config-dir", config_dir,
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: Tech News" in result.output

    def test_list_interests_empty(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            ["interest", "list", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "No interests configured" in result.output

    def test_list_interests(self, runner: CliRunner, config_dir: str) -> None:
        runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", config_dir],
        )
        result = runner.invoke(
            cli,
            ["interest", "list", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "AI" in result.output

    def test_remove_interest(self, runner: CliRunner, config_dir: str) -> None:
        runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", config_dir],
        )
        result = runner.invoke(
            cli,
            ["interest", "remove", "--topic", "AI", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "Removed interest: AI" in result.output

    def test_remove_nonexistent_interest(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            ["interest", "remove", "--topic", "Nonexistent", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_duplicate_interest(self, runner: CliRunner, config_dir: str) -> None:
        runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", config_dir],
        )
        result = runner.invoke(
            cli,
            ["interest", "add", "--topic", "AI", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "already exists" in result.output


class TestSearchCommand:
    def test_search_empty_index(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            ["search", "test", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "empty" in result.output.lower() or "No results" in result.output


class TestStatusCommand:
    def test_status(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            ["status", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "Personal Index Status" in result.output


class TestStatsCommand:
    def test_stats(self, runner: CliRunner, config_dir: str) -> None:
        result = runner.invoke(
            cli,
            ["stats", "--config-dir", config_dir],
        )
        assert result.exit_code == 0
        assert "Index Statistics" in result.output


class TestVersion:
    def test_version(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
