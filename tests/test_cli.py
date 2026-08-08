"""Tests for personal_index.cli."""

import pytest
import tempfile
import shutil
from click.testing import CliRunner

from personal_index.cli import cli


@pytest.fixture
def runner():
    """Create a CLI test runner."""
    return CliRunner()


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def data_dir_option(temp_data_dir):
    """Return the data dir option for CLI commands."""
    return f"--data-dir={temp_data_dir}"


class TestInterestCommands:
    def test_add_interest(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python", "-k", "python,code"],
        )
        assert result.exit_code == 0
        assert "Added interest: python" in result.output

    def test_add_interest_with_url_patterns(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [
                data_dir_option,
                "interest", "add",
                "-t", "python",
                "-k", "python",
                "-u", "python.org",
            ],
        )
        assert result.exit_code == 0
        assert "URL patterns: python.org" in result.output

    def test_add_duplicate_interest(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python"],
        )
        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_list_interests_empty(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "list"],
        )
        assert result.exit_code == 0
        assert "No interests" in result.output

    def test_list_interests(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python", "-k", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "list"],
        )
        assert result.exit_code == 0
        assert "python" in result.output

    def test_remove_interest(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "remove", "-t", "python"],
        )
        assert result.exit_code == 0
        assert "Removed interest: python" in result.output

    def test_remove_nonexistent_interest(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "remove", "-t", "nonexistent"],
        )
        assert result.exit_code == 1

    def test_toggle_interest(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "interest", "toggle", "-t", "python"],
        )
        assert result.exit_code == 0
        assert "disabled" in result.output


class TestSearchCommands:
    def test_search_no_results(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "search", "nonexistent"],
        )
        assert result.exit_code == 0
        assert "No results found" in result.output

    def test_results_no_results(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "results", "nonexistent"],
        )
        assert result.exit_code == 0
        assert "No results found" in result.output


class TestScheduleCommands:
    def test_add_schedule(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "schedule", "add", "-t", "python", "-i", "12"],
        )
        assert result.exit_code == 0
        assert "Added schedule" in result.output

    def test_list_schedules_empty(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "schedule", "list"],
        )
        assert result.exit_code == 0
        assert "No schedules" in result.output

    def test_list_schedules(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "schedule", "add", "-t", "python", "-i", "12"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "schedule", "list"],
        )
        assert result.exit_code == 0
        assert "python" in result.output

    def test_remove_schedule(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "schedule", "add", "-t", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "schedule", "remove", "-t", "python"],
        )
        assert result.exit_code == 0
        assert "Removed schedule" in result.output

    def test_list_jobs_empty(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "schedule", "jobs"],
        )
        assert result.exit_code == 0
        assert "No jobs" in result.output


class TestStatusCommand:
    def test_status(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "status"],
        )
        assert result.exit_code == 0
        assert "Personal Index Status" in result.output
        assert "Interests:" in result.output
        assert "Stored pages:" in result.output


class TestCrawlCommand:
    def test_crawl_no_interests(self, runner, data_dir_option):
        result = runner.invoke(
            cli,
            [data_dir_option, "crawl", "-s", "https://example.com"],
        )
        assert result.exit_code == 1
        assert "No enabled interests" in result.output

    def test_crawl_no_urls(self, runner, data_dir_option):
        runner.invoke(
            cli,
            [data_dir_option, "interest", "add", "-t", "python", "-k", "python"],
        )
        result = runner.invoke(
            cli,
            [data_dir_option, "crawl"],
        )
        assert result.exit_code == 1
        assert "No seed URLs" in result.output


class TestVersion:
    def test_version(self, runner, data_dir_option):
        result = runner.invoke(cli, [data_dir_option, "--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output
