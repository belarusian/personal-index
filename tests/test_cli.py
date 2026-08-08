"""Tests for the CLI interface."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from personal_index.cli import (
    main,
    interests,
    crawl,
    search,
    index,
    schedule,
    config,
)
from personal_index.interests import InterestStore
from personal_index.index import SearchIndex
from personal_index.scheduler import Scheduler
from personal_index.models import Interest


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
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'add') as mock_add:
                result = runner.invoke(
                    interests,
                    ['add', '-n', 'test', '-k', 'python', '-k', 'coding', '-p', '3'],
                )
                assert result.exit_code == 0
                assert "Added interest" in result.output

    def test_add_interest_with_url_pattern(self, runner, tmp_path):
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'add') as mock_add:
                result = runner.invoke(
                    interests,
                    ['add', '-n', 'news', '-u', r'https://news\.example\.com/.*'],
                )
                assert result.exit_code == 0

    def test_list_interests_empty(self, runner, tmp_path):
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'list_all', return_value=[]):
                result = runner.invoke(interests, ['list'])
                assert result.exit_code == 0
                assert "No interests" in result.output

    def test_list_interests_with_data(self, runner, tmp_path):
        test_interest = Interest(name="test", keywords=["python"], enabled=True)
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'list_all', return_value=[test_interest]):
                result = runner.invoke(interests, ['list'])
                assert result.exit_code == 0
                assert "test" in result.output

    def test_remove_interest(self, runner, tmp_path):
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'remove', return_value=True):
                result = runner.invoke(interests, ['remove', 'test'])
                assert result.exit_code == 0
                assert "Removed" in result.output

    def test_remove_interest_not_found(self, runner, tmp_path):
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'remove', return_value=False):
                result = runner.invoke(interests, ['remove', 'nonexistent'])
                assert result.exit_code == 1

    def test_toggle_interest(self, runner, tmp_path):
        toggled_interest = Interest(name="test", enabled=False)
        with patch.object(InterestStore, '__init__', lambda self, store_path=None: None):
            with patch.object(InterestStore, 'toggle', return_value=toggled_interest):
                result = runner.invoke(interests, ['toggle', 'test'])
                assert result.exit_code == 0
                assert "disabled" in result.output


class TestSearchCommand:
    def test_search_no_results(self, runner, tmp_path):
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'search', return_value=[]):
                result = runner.invoke(search, ['python'])
                assert result.exit_code == 0
                assert "No results" in result.output

    def test_search_with_results(self, runner, tmp_path):
        from personal_index.index import SearchResult
        test_result = SearchResult(
            url="https://example.com",
            title="Python Guide",
            snippet="Learn Python",
            relevance_score=1.5,
        )
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'search', return_value=[test_result]):
                result = runner.invoke(search, ['python'])
                assert result.exit_code == 0
                assert "Python Guide" in result.output

    def test_search_with_limit(self, runner, tmp_path):
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'search') as mock_search:
                mock_search.return_value = []
                result = runner.invoke(search, ['python', '--limit', '5'])
                assert result.exit_code == 0
                mock_search.assert_called_once()


class TestCrawlCommand:
    def test_crawl_basic(self, runner, tmp_path):
        with patch('personal_index.cli.get_config_manager') as mock_mgr:
            mock_config = MagicMock()
            mock_mgr.return_value.config = mock_config
            with patch('personal_index.crawler.main.WebCrawler') as mock_crawler_cls:
                mock_crawler = MagicMock()
                mock_crawler_cls.return_value = mock_crawler
                mock_crawler.crawl.return_value = []
                result = runner.invoke(crawl, ['https://example.com'])
                assert result.exit_code == 0

    def test_crawl_with_depth(self, runner, tmp_path):
        with patch('personal_index.cli.get_config_manager') as mock_mgr:
            mock_config = MagicMock()
            mock_mgr.return_value.config = mock_config
            with patch('personal_index.crawler.main.WebCrawler') as mock_crawler_cls:
                mock_crawler = MagicMock()
                mock_crawler_cls.return_value = mock_crawler
                mock_crawler.crawl.return_value = []
                result = runner.invoke(crawl, ['https://example.com', '--depth', '2'])
                assert result.exit_code == 0


class TestIndexCommands:
    def test_index_count(self, runner, tmp_path):
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'get_page_count', return_value=42):
                result = runner.invoke(index, ['count'])
                assert result.exit_code == 0
                assert "42" in result.output

    def test_index_list_empty(self, runner, tmp_path):
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'list_pages', return_value=[]):
                result = runner.invoke(index, ['list'])
                assert result.exit_code == 0
                assert "No pages" in result.output

    def test_index_clear(self, runner, tmp_path):
        with patch.object(SearchIndex, '__init__', lambda self, db_path=None: None):
            with patch.object(SearchIndex, 'clear'):
                result = runner.invoke(index, ['clear'], input='y\n')
                assert result.exit_code == 0
                assert "cleared" in result.output


class TestScheduleCommands:
    def test_schedule_add(self, runner, tmp_path):
        with patch.object(Scheduler, '__init__', lambda self, config=None, crawler=None, jobs_file=None: None):
            with patch.object(Scheduler, 'add_job'):
                result = runner.invoke(
                    schedule,
                    ['add', '-n', 'daily', '-u', 'https://example.com', '-i', '24'],
                )
                assert result.exit_code == 0
                assert "Added scheduled job" in result.output

    def test_schedule_list_empty(self, runner, tmp_path):
        with patch.object(Scheduler, '__init__', lambda self, config=None, crawler=None, jobs_file=None: None):
            with patch.object(Scheduler, 'list_jobs', return_value=[]):
                result = runner.invoke(schedule, ['list'])
                assert result.exit_code == 0
                assert "No scheduled jobs" in result.output

    def test_schedule_remove(self, runner, tmp_path):
        with patch.object(Scheduler, '__init__', lambda self, config=None, crawler=None, jobs_file=None: None):
            with patch.object(Scheduler, 'remove_job', return_value=True):
                result = runner.invoke(schedule, ['remove', 'daily'])
                assert result.exit_code == 0
                assert "Removed" in result.output

    def test_schedule_remove_not_found(self, runner, tmp_path):
        with patch.object(Scheduler, '__init__', lambda self, config=None, crawler=None, jobs_file=None: None):
            with patch.object(Scheduler, 'remove_job', return_value=False):
                result = runner.invoke(schedule, ['remove', 'nonexistent'])
                assert result.exit_code == 1


class TestConfigCommands:
    def test_config_show(self, runner, tmp_path):
        with patch('personal_index.cli.get_config_manager') as mock_mgr:
            mock_config = MagicMock()
            mock_config.config_dir = str(tmp_path / "config")
            mock_config.data_dir = str(tmp_path / "data")
            mock_config.crawler.max_depth = 3
            mock_config.crawler.politeness_delay = 1.0
            mock_config.crawler.max_concurrent_requests = 5
            mock_config.crawler.request_timeout = 30
            mock_config.crawler.respect_robots_txt = True
            mock_config.schedule.enabled = False
            mock_config.schedule.interval_hours = 24
            mock_mgr.return_value.config = mock_config

            result = runner.invoke(config, ['show'])
            assert result.exit_code == 0
            assert "Max depth: 3" in result.output

    def test_config_set_crawler(self, runner, tmp_path):
        with patch('personal_index.cli.get_config_manager') as mock_mgr:
            mock_config = MagicMock()
            mock_mgr.return_value.config = mock_config
            result = runner.invoke(config, ['set-crawler', '--max-depth', '5'])
            assert result.exit_code == 0
            assert mock_config.crawler.max_depth == 5

    def test_config_set_schedule(self, runner, tmp_path):
        with patch('personal_index.cli.get_config_manager') as mock_mgr:
            mock_config = MagicMock()
            mock_mgr.return_value.config = mock_config
            result = runner.invoke(config, ['set-schedule', '--interval', '12'])
            assert result.exit_code == 0
            assert mock_config.schedule.interval_hours == 12


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
        assert "crawl" in result.output
