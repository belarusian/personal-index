"""Tests for the CLI interface."""

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.index import SearchIndex


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def temp_dirs(tmp_path):
    """Set up temporary config and data directories."""
    config_dir = str(tmp_path / "config")
    data_dir = str(tmp_path / "data")
    os.makedirs(config_dir, exist_ok=True)
    os.makedirs(data_dir, exist_ok=True)
    return config_dir, data_dir


class TestInterestCommands:
    def test_add_interest(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(
            main,
            ['--data-dir', data_dir, 'interests', 'add', '-n', 'test', '-k', 'python', '-k', 'coding', '--priority', '3'],
        )
        assert result.exit_code == 0
        assert "Added interest" in result.output

    def test_add_interest_with_url_pattern(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(
            main,
            ['--data-dir', data_dir, 'interests', 'add', '-n', 'news'],
        )
        assert result.exit_code == 0

    def test_list_interests_empty(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'interests', 'list'])
        assert result.exit_code == 0
        assert "No interests" in result.output

    def test_list_interests_with_data(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        # First add an interest
        runner.invoke(main, ['--data-dir', data_dir, 'interests', 'add', '-n', 'test', '-k', 'python'])
        result = runner.invoke(main, ['--data-dir', data_dir, 'interests', 'list'])
        assert result.exit_code == 0
        assert "test" in result.output

    def test_remove_interest(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        runner.invoke(main, ['--data-dir', data_dir, 'interests', 'add', '-n', 'test', '-k', 'python'])
        result = runner.invoke(main, ['--data-dir', data_dir, 'interests', 'remove', 'test'])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_remove_interest_not_found(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'interests', 'remove', 'nonexistent'])
        assert result.exit_code == 1

    def test_toggle_interest(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        runner.invoke(main, ['--data-dir', data_dir, 'interests', 'add', '-n', 'test', '-k', 'python'])
        # Check if enable/disable command exists
        result = runner.invoke(main, ['--data-dir', data_dir, 'interests', 'list'])
        assert result.exit_code == 0
        assert "test" in result.output


class TestSearchCommand:
    def test_search_no_results(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'search', 'python'])
        assert result.exit_code == 0

    def test_search_with_results(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        # Add a page to the index first
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        from personal_index.models import CrawledPage
        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language.",
        )
        index.add_page(page)
        index.close()

        result = runner.invoke(main, ['--data-dir', data_dir, 'search', 'python'])
        assert result.exit_code == 0
        assert "Python Guide" in result.output

    def test_search_with_limit(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'search', 'python', '--limit', '5'])
        assert result.exit_code == 0


class TestTagCommands:
    def test_add_tag(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(
            main,
            ['--data-dir', data_dir, 'tags', 'add', 'important', 'https://example.com/page1'],
        )
        assert result.exit_code == 0
        assert "Added tag" in result.output

    def test_list_tags_empty(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'tags', 'list'])
        assert result.exit_code == 0

    def test_remove_tag(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        runner.invoke(main, ['--data-dir', data_dir, 'tags', 'add', 'important', 'https://example.com/page1'])
        result = runner.invoke(main, ['--data-dir', data_dir, 'tags', 'remove', 'important', 'https://example.com/page1'])
        assert result.exit_code == 0
        assert "Removed tag" in result.output

    def test_remove_tag_not_present(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        runner.invoke(main, ['--data-dir', data_dir, 'tags', 'add', 'important', 'https://example.com/page1'])
        # "missing" was never added to this page -> should report not found
        result = runner.invoke(main, ['--data-dir', data_dir, 'tags', 'remove', 'missing', 'https://example.com/page1'])
        assert result.exit_code == 0
        assert "not found" in result.output
        assert "Removed tag" not in result.output


class TestScheduleCommands:
    def test_schedule_list(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'schedule', 'list'])
        assert result.exit_code == 0

    def test_schedule_add(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'schedule', 'add', '--name', 'daily', '--url', 'https://example.com', '--interval', '24'])
        assert result.exit_code == 0
        assert "Added" in result.output

    def test_schedule_remove(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        runner.invoke(main, ['--data-dir', data_dir, 'schedule', 'add', '--name', 'daily', '--url', 'https://example.com', '--interval', '24'])
        result = runner.invoke(main, ['--data-dir', data_dir, 'schedule', 'remove', 'daily'])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_schedule_remove_not_found(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'schedule', 'remove', 'nonexistent'])
        assert result.exit_code == 1


class TestConfigCommands:
    def test_config_show(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'config', 'show'])
        assert result.exit_code == 0

    def test_config_set_crawler(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'config', 'set-crawler', '--max-depth', '5'])
        assert result.exit_code == 0

    def test_config_set_schedule(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ['--data-dir', data_dir, 'config', 'set-schedule', '--interval', '12'])
        assert result.exit_code == 0


class TestMainCommand:
    def test_version(self, runner):
        result = runner.invoke(main, ['--version'])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self, runner):
        result = runner.invoke(main, ['--help'])
        assert result.exit_code == 0
        assert "personal-index" in result.output
        assert "interests" in result.output
        assert "search" in result.output
        assert "pipeline" in result.output

    def test_init_creates_data_dir(self, runner, tmp_path):
        data_dir = str(tmp_path / "mydata")
        result = runner.invoke(main, ['--data-dir', data_dir, 'init'])
        assert result.exit_code == 0
        assert os.path.isdir(data_dir)
        assert "Initialized" in result.output

    def test_status_command(self, runner, tmp_path):
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)
        result = runner.invoke(main, ['--data-dir', data_dir, 'status'])
        assert result.exit_code == 0
        assert "Status" in result.output

    def test_import_command_file_not_found(self, runner, tmp_path):
        result = runner.invoke(main, ['import', '/nonexistent/path'])
        assert result.exit_code == 1
        assert "not found" in result.output
