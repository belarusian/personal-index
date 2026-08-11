"""Integration tests for the CLI interface."""

from __future__ import annotations

import os
import tempfile

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIIntegration:
    """Test CLI commands end-to-end."""

    def setup_method(self):
        """Set up a temporary directory for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.runner = CliRunner()
        self.original_dir = os.getcwd()

    def teardown_method(self):
        os.chdir(self.original_dir)

    def test_init_command(self):
        """Init command should create config and data directory."""
        with self.runner.isolated_filesystem() as tmpdir:
            result = self.runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert os.path.exists("config.yaml")
            assert os.path.isdir(".personal_index")

    def test_init_with_custom_dirs(self):
        """Init should respect custom data-dir and config options."""
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(main, [
                "init", "--data-dir", "my_data", "--config", "my_config.yaml"
            ])
            assert result.exit_code == 0
            assert os.path.exists("my_config.yaml")
            assert os.path.isdir("my_data")

    def test_interests_add(self):
        """Adding an interest should succeed."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, [
                "interests", "add", "-n", "Python", "-k", "python", "-k", "programming"
            ])
            assert result.exit_code == 0
            assert "Added interest" in result.output

    def test_interests_list(self):
        """Listing interests should show added interests."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            self.runner.invoke(main, ["interests", "add", "-n", "AI", "-k", "ai"])
            result = self.runner.invoke(main, ["interests", "list"])
            assert result.exit_code == 0
            assert "AI" in result.output

    def test_interests_remove(self):
        """Removing an interest should succeed."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            self.runner.invoke(main, ["interests", "add", "-n", "Test", "-k", "test"])
            result = self.runner.invoke(main, ["interests", "remove", "Test"])
            assert result.exit_code == 0
            assert "Removed interest" in result.output

    def test_interests_remove_nonexistent(self):
        """Removing a nonexistent interest should fail."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["interests", "remove", "NonExistent"])
            assert result.exit_code == 1

    def test_search_empty(self):
        """Searching with no indexed content should return no results."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["search", "nonexistent"])
            assert result.exit_code == 0
            assert "No results" in result.output

    def test_process_and_search(self):
        """Processing content should make it searchable."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            self.runner.invoke(main, [
                "process",
                "--url", "https://example.com/test",
                "--title", "Test Page",
                "--content", "This is a test page about Python programming",
            ])
            result = self.runner.invoke(main, ["search", "Python"])
            assert result.exit_code == 0
            assert "Test Page" in result.output

    def test_stats_command(self):
        """Stats command should show statistics."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["stats"])
            assert result.exit_code == 0
            assert "Indexed items" in result.output

    def test_stats_json(self):
        """Stats command with --json should output valid JSON."""
        import json
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["stats", "--json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "indexed_items" in data

    def test_health_command(self):
        """Health command should pass after init."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["health"])
            assert result.exit_code == 0
            assert "OK" in result.output

    def test_config_show(self):
        """Config show should display current configuration."""
        with self.runner.isolated_filesystem():
            self.runner.invoke(main, ["init"])
            result = self.runner.invoke(main, ["config", "show"])
            assert result.exit_code == 0
            assert "Data dir" in result.output

    def test_version_option(self):
        """Version option should display version."""
        result = self.runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help(self):
        """Help should show available commands."""
        result = self.runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "personal-index" in result.output
        assert "init" in result.output
        assert "search" in result.output
        assert "interests" in result.output
