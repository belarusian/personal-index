"""Tests for CLI interface."""

import pytest
from click.testing import CliRunner
from pathlib import Path
from personal_index.cli import main
from personal_index.config import AppConfig


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_config_dir(tmp_path):
    return str(tmp_path / "config")


class TestMainGroup:
    def test_version(self, runner):
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "personal-index" in result.output
        assert "crawl" in result.output
        assert "search" in result.output


class TestInterestCommands:
    def test_add_interest(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            [
                "--config-dir", temp_config_dir,
                "interest", "add",
                "--topic", "AI",
                "--keywords", "neural,deep learning",
                "--priority", "8",
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: AI" in result.output

    def test_add_interest_with_url_pattern(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            [
                "--config-dir", temp_config_dir,
                "interest", "add",
                "--topic", "Tech",
                "--url-pattern", "http://techblog.example.com/*",
            ],
        )
        assert result.exit_code == 0
        assert "Added interest: Tech" in result.output

    def test_add_duplicate_interest(self, runner, temp_config_dir):
        runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI"],
        )
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI"],
        )
        assert result.exit_code == 0
        assert "already exists" in result.output

    def test_list_interests_empty(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "list"],
        )
        assert result.exit_code == 0
        assert "No interests" in result.output

    def test_list_interests(self, runner, temp_config_dir):
        runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI", "--keywords", "neural"],
        )
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "list"],
        )
        assert result.exit_code == 0
        assert "AI" in result.output

    def test_remove_interest(self, runner, temp_config_dir):
        runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI"],
        )
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "remove", "--topic", "AI"],
        )
        assert result.exit_code == 0
        assert "Removed interest: AI" in result.output

    def test_remove_nonexistent_interest(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "remove", "--topic", "Nonexistent"],
        )
        assert result.exit_code == 0
        assert "not found" in result.output

    def test_enable_interest(self, runner, temp_config_dir):
        runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI"],
        )
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "disable", "--topic", "AI"],
        )
        assert "Disabled" in result.output

        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "enable", "--topic", "AI"],
        )
        assert result.exit_code == 0
        assert "Enabled" in result.output

    def test_disable_interest(self, runner, temp_config_dir):
        runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "add", "--topic", "AI"],
        )
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "interest", "disable", "--topic", "AI"],
        )
        assert result.exit_code == 0
        assert "Disabled interest: AI" in result.output


class TestSearchCommand:
    def test_search_empty_index(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "search", "test"],
        )
        assert result.exit_code == 0
        assert "empty" in result.output.lower()

    def test_search_no_results(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "search", "nonexistent"],
        )
        assert result.exit_code == 0


class TestResultsCommand:
    def test_results_empty(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "results"],
        )
        assert result.exit_code == 0
        assert "No indexed" in result.output

    def test_results_json(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "results", "--format", "json"],
        )
        assert result.exit_code == 0
        assert result.output.strip() == "[]"


class TestStatsCommand:
    def test_stats(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "stats"],
        )
        assert result.exit_code == 0
        assert "Statistics" in result.output
        assert "Interests" in result.output
        assert "Index" in result.output


class TestClearCommand:
    def test_clear(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "clear"],
            input="y\n",
        )
        assert result.exit_code == 0
        assert "cleared" in result.output.lower()


class TestScheduleCommands:
    def test_add_schedule(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            [
                "--config-dir", temp_config_dir,
                "schedule", "add",
                "--name", "daily",
                "--interval", "24",
                "--seed", "http://example.com",
                "--topic", "AI",
            ],
        )
        assert result.exit_code == 0
        assert "Added schedule: daily" in result.output

    def test_list_schedules_empty(self, runner, temp_config_dir):
        result = runner.invoke(
            main,
            ["--config-dir", temp_config_dir, "schedule", "list"],
        )
        assert result.exit_code == 0
        assert "No scheduled" in result.output
