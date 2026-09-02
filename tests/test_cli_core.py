"""Core CLI tests for personal_index/cli.py.

Tests the CLI structure, config validation, command routing,
and subcommand --help accessibility.

These tests verify the CLI framework itself works correctly,
not the underlying business logic (which is tested elsewhere).
"""

from __future__ import annotations

import os

import pytest
from click.testing import CliRunner

from personal_index.cli import main


@pytest.fixture
def runner():
    """CliRunner for invoking CLI commands."""
    return CliRunner()


# ── CLI Config Validation ─────────────────────────────────────────────

class TestCLIConfigValidation:
    """Test CLI-level options: --data-dir, --verbose, --version."""

    def test_version_flag(self, runner):
        """Test --version shows version number."""
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_flag(self, runner):
        """Test --help shows usage information."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "Personal Index" in result.output
        assert "--data-dir" in result.output
        assert "--verbose" in result.output

    def test_data_dir_flag(self, runner, tmp_path):
        """Test --data-dir sets custom data directory."""
        data_dir = str(tmp_path / "custom_data")
        result = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result.exit_code == 0
        assert os.path.isdir(data_dir)

    def test_data_dir_default(self, runner, tmp_path, monkeypatch):
        """Test default data-dir is .personal_index."""
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert os.path.isdir(".personal_index")

    def test_verbose_flag(self, runner, tmp_path):
        """Test --verbose flag is accepted without error."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ["--verbose", "--data-dir", data_dir, "init"])
        assert result.exit_code == 0

    def test_verbose_flag_short(self, runner, tmp_path):
        """Test -v (short verbose) flag is accepted."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ["-v", "--data-dir", data_dir, "init"])
        assert result.exit_code == 0

    def test_data_dir_with_init(self, runner, tmp_path):
        """Test --data-dir with init creates directory at specified path."""
        data_dir = str(tmp_path / "my_index")
        result = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result.exit_code == 0
        assert os.path.isdir(data_dir)
        assert "Initialized" in result.output


# ── Command Routing ───────────────────────────────────────────────────

class TestCommandRouting:
    """Test that all subcommands are registered and accessible."""

    EXPECTED_COMMANDS = (
        "init", "interests", "tags", "import", "search",
        "export", "status", "crawl", "pipeline", "stats",
        "list", "top", "remove", "clear", "doctor",
        "schedule", "config", "verify", "watch",
        "dedup", "health", "recommend",
    )

    def test_all_commands_registered(self, runner):
        """Test all expected commands appear in --help output."""
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        for cmd in self.EXPECTED_COMMANDS:
            assert cmd in result.output, f"Command '{cmd}' not found in help output"

    def test_all_commands_accessible_via_help(self, runner):
        """Test each subcommand is accessible via --help."""
        for cmd in self.EXPECTED_COMMANDS:
            result = runner.invoke(main, [cmd, "--help"])
            assert result.exit_code == 0, (
                f"Command '{cmd} --help' failed with exit code {result.exit_code}: "
                f"{result.output}"
            )

    def test_group_subcommands_accessible(self, runner):
        """Test group subcommands (interests, tags, schedule, config) have subcommands."""
        # interests subcommands
        result = runner.invoke(main, ["interests", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

        # tags subcommands
        result = runner.invoke(main, ["tags", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

        # schedule subcommands
        result = runner.invoke(main, ["schedule", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

        # config subcommands
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set-crawler" in result.output
        assert "set-schedule" in result.output


# ── CLI Init Command ──────────────────────────────────────────────────

class TestCLIInitCommand:
    """Test the init command creates proper directory structure."""

    def test_init_creates_data_directory(self, runner, tmp_path):
        """Test init creates the data directory."""
        data_dir = str(tmp_path / "my_index")
        result = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result.exit_code == 0
        assert os.path.isdir(data_dir)

    def test_init_creates_config_yaml(self, runner, tmp_path):
        """Test init creates config.yaml."""
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=str(tmp_path)):
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert os.path.exists("config.yaml")

    def test_init_creates_subdirectories(self, runner, tmp_path):
        """Test init creates cache, archive, backups subdirectories."""
        data_dir = str(tmp_path / "my_index")
        result = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result.exit_code == 0
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_init_config_yaml_content(self, runner, tmp_path):
        """Test init creates config.yaml with expected structure."""
        import yaml
        runner = CliRunner()
        with runner.isolated_filesystem(temp_dir=str(tmp_path)):
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            with open("config.yaml", "r") as f:
                config = yaml.safe_load(f)
            assert "crawler" in config
            assert "filter" in config
            assert "pipeline" in config

    def test_init_idempotent(self, runner, tmp_path):
        """Test init can be run multiple times without error."""
        data_dir = str(tmp_path / "my_index")
        result1 = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result1.exit_code == 0
        result2 = runner.invoke(main, ["--data-dir", data_dir, "init"])
        assert result2.exit_code == 0

    def test_init_with_custom_config_path(self, runner, tmp_path):
        """Test init with --config option."""
        data_dir = str(tmp_path / "my_index")
        config_path = str(tmp_path / "custom_config.yaml")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "init", "--config", config_path
        ])
        assert result.exit_code == 0
        assert os.path.exists(config_path)


# ── CLI Interests Commands ────────────────────────────────────────────

class TestCLIInterestsCommands:
    """Test interests subcommands."""

    def test_interests_help(self, runner):
        """Test interests --help works."""
        result = runner.invoke(main, ["interests", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_interests_add_help(self, runner):
        """Test interests add --help works."""
        result = runner.invoke(main, ["interests", "add", "--help"])
        assert result.exit_code == 0
        assert "--name" in result.output
        assert "--keyword" in result.output
        assert "--priority" in result.output

    def test_interests_add(self, runner, tmp_path):
        """Test interests add creates an interest."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "add", "-n", "python", "-k", "python", "-k", "django"
        ])
        assert result.exit_code == 0
        assert "Added interest" in result.output

    def test_interests_add_required_name(self, runner, tmp_path):
        """Test interests add requires --name."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "add", "-k", "python"
        ])
        assert result.exit_code != 0

    def test_interests_list_empty(self, runner, tmp_path):
        """Test interests list with no interests."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ["--data-dir", data_dir, "interests", "list"])
        assert result.exit_code == 0

    def test_interests_list_with_data(self, runner, tmp_path):
        """Test interests list shows added interests."""
        data_dir = str(tmp_path / "data")
        runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "add", "-n", "python", "-k", "python"
        ])
        result = runner.invoke(main, ["--data-dir", data_dir, "interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output

    def test_interests_remove(self, runner, tmp_path):
        """Test interests remove deletes an interest."""
        data_dir = str(tmp_path / "data")
        runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "add", "-n", "python", "-k", "python"
        ])
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "remove", "python"
        ])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_interests_remove_not_found(self, runner, tmp_path):
        """Test interests remove fails for non-existent interest."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "interests", "remove", "nonexistent"
        ])
        assert result.exit_code == 1


# ── CLI Tags Commands ─────────────────────────────────────────────────

class TestCLITagsCommands:
    """Test tags subcommands."""

    def test_tags_help(self, runner):
        """Test tags --help works."""
        result = runner.invoke(main, ["tags", "--help"])
        assert result.exit_code == 0
        assert "add" in result.output
        assert "list" in result.output
        assert "remove" in result.output

    def test_tags_add_help(self, runner):
        """Test tags add --help works."""
        result = runner.invoke(main, ["tags", "add", "--help"])
        assert result.exit_code == 0

    def test_tags_add(self, runner, tmp_path):
        """Test tags add creates a tag."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "tags", "add", "important", "https://example.com/page1"
        ])
        assert result.exit_code == 0
        assert "Added tag" in result.output

    def test_tags_list_empty(self, runner, tmp_path):
        """Test tags list with no tags."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ["--data-dir", data_dir, "tags", "list"])
        assert result.exit_code == 0

    def test_tags_list_with_data(self, runner, tmp_path):
        """Test tags list shows added tags."""
        data_dir = str(tmp_path / "data")
        runner.invoke(main, [
            "--data-dir", data_dir,
            "tags", "add", "important", "https://example.com/page1"
        ])
        result = runner.invoke(main, ["--data-dir", data_dir, "tags", "list"])
        assert result.exit_code == 0
        assert "important" in result.output

    def test_tags_remove(self, runner, tmp_path):
        """Test tags remove deletes a tag."""
        data_dir = str(tmp_path / "data")
        runner.invoke(main, [
            "--data-dir", data_dir,
            "tags", "add", "important", "https://example.com/page1"
        ])
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "tags", "remove", "important", "https://example.com/page1"
        ])
        assert result.exit_code == 0
        assert "Removed tag" in result.output


# ── CLI Search Command ────────────────────────────────────────────────

class TestCLISearchCommand:
    """Test search command."""

    def test_search_help(self, runner):
        """Test search --help works."""
        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "--limit" in result.output
        assert "--tag" in result.output
        assert "--format" in result.output

    def test_search_empty_index(self, runner, tmp_path):
        """Test search with empty index returns no results."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "search", "python"
        ])
        assert result.exit_code == 0
        assert "No results" in result.output or "No indexed" in result.output

    def test_search_with_limit(self, runner, tmp_path):
        """Test search with --limit flag."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "search", "python", "--limit", "5"
        ])
        assert result.exit_code == 0

    def test_search_with_format_json(self, runner, tmp_path):
        """Test search with --format json."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "search", "python", "--format", "json"
        ])
        assert result.exit_code == 0


# ── CLI Export Command ────────────────────────────────────────────────

class TestCLIExportCommand:
    """Test export command."""

    def test_export_help(self, runner):
        """Test export --help works."""
        result = runner.invoke(main, ["export", "--help"])
        assert result.exit_code == 0
        assert "--format" in result.output
        assert "--output" in result.output

    def test_export_empty_index(self, runner, tmp_path):
        """Test export with empty index shows message."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "export", "--format", "json"
        ])
        assert result.exit_code == 0
        assert "No indexed content" in result.output

    def test_export_markdown_empty(self, runner, tmp_path):
        """Test export markdown with empty index."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "export", "--format", "markdown"
        ])
        assert result.exit_code == 0
        assert "No indexed content" in result.output

    def test_export_csv_empty(self, runner, tmp_path):
        """Test export csv with empty index."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir, "export", "--format", "csv"
        ])
        assert result.exit_code == 0
        assert "No indexed content" in result.output


# ── CLI Config Commands ───────────────────────────────────────────────

class TestCLIConfigCommands:
    """Test config subcommands."""

    def test_config_help(self, runner):
        """Test config --help works."""
        result = runner.invoke(main, ["config", "--help"])
        assert result.exit_code == 0
        assert "show" in result.output
        assert "set-crawler" in result.output
        assert "set-schedule" in result.output

    def test_config_show_help(self, runner):
        """Test config show --help works."""
        result = runner.invoke(main, ["config", "show", "--help"])
        assert result.exit_code == 0

    def test_config_show(self, runner, tmp_path):
        """Test config show displays configuration."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, ["--data-dir", data_dir, "config", "show"])
        assert result.exit_code == 0

    def test_config_set_crawler_help(self, runner):
        """Test config set-crawler --help works."""
        result = runner.invoke(main, ["config", "set-crawler", "--help"])
        assert result.exit_code == 0
        assert "--max-depth" in result.output

    def test_config_set_crawler(self, runner, tmp_path):
        """Test config set-crawler updates crawler settings."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "config", "set-crawler", "--max-depth", "5"
        ])
        assert result.exit_code == 0

    def test_config_set_schedule_help(self, runner):
        """Test config set-schedule --help works."""
        result = runner.invoke(main, ["config", "set-schedule", "--help"])
        assert result.exit_code == 0
        assert "--interval" in result.output

    def test_config_set_schedule(self, runner, tmp_path):
        """Test config set-schedule updates schedule settings."""
        data_dir = str(tmp_path / "data")
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "config", "set-schedule", "--interval", "12"
        ])
        assert result.exit_code == 0


# ── CLI Other Commands ────────────────────────────────────────────────

class TestCLIOtherCommands:
    """Test remaining CLI commands are accessible."""

    def test_status_help(self, runner):
        """Test status --help works."""
        result = runner.invoke(main, ["status", "--help"])
        assert result.exit_code == 0

    def test_crawl_help(self, runner):
        """Test crawl --help works."""
        result = runner.invoke(main, ["crawl", "--help"])
        assert result.exit_code == 0

    def test_pipeline_help(self, runner):
        """Test pipeline --help works."""
        result = runner.invoke(main, ["pipeline", "--help"])
        assert result.exit_code == 0

    def test_stats_help(self, runner):
        """Test stats --help works."""
        result = runner.invoke(main, ["stats", "--help"])
        assert result.exit_code == 0

    def test_list_help(self, runner):
        """Test list --help works."""
        result = runner.invoke(main, ["list", "--help"])
        assert result.exit_code == 0

    def test_top_help(self, runner):
        """Test top --help works."""
        result = runner.invoke(main, ["top", "--help"])
        assert result.exit_code == 0

    def test_remove_help(self, runner):
        """Test remove --help works."""
        result = runner.invoke(main, ["remove", "--help"])
        assert result.exit_code == 0

    def test_clear_help(self, runner):
        """Test clear --help works."""
        result = runner.invoke(main, ["clear", "--help"])
        assert result.exit_code == 0

    def test_doctor_help(self, runner):
        """Test doctor --help works."""
        result = runner.invoke(main, ["doctor", "--help"])
        assert result.exit_code == 0

    def test_verify_help(self, runner):
        """Test verify --help works."""
        result = runner.invoke(main, ["verify", "--help"])
        assert result.exit_code == 0

    def test_watch_help(self, runner):
        """Test watch --help works."""
        result = runner.invoke(main, ["watch", "--help"])
        assert result.exit_code == 0

    def test_import_help(self, runner):
        """Test import --help works."""
        result = runner.invoke(main, ["import", "--help"])
        assert result.exit_code == 0

    def test_schedule_help(self, runner):
        """Test schedule --help works."""
        result = runner.invoke(main, ["schedule", "--help"])
        assert result.exit_code == 0

    def test_dedup_help(self, runner):
        """Test dedup --help works."""
        result = runner.invoke(main, ["dedup", "--help"])
        assert result.exit_code == 0

    def test_health_help(self, runner):
        """Test health --help works."""
        result = runner.invoke(main, ["health", "--help"])
        assert result.exit_code == 0

    def test_recommend_help(self, runner):
        """Test recommend --help works."""
        result = runner.invoke(main, ["recommend", "--help"])
        assert result.exit_code == 0


# ── CLI Remove Command (tag cleanup parity) ───────────────────────────
class TestCLIRemoveCommand:
    """Test `remove` drops the page's tags alongside the index entry."""

    def test_remove_cleans_orphan_tags(self, runner, tmp_path):
        """Removing a page must also drop its TagStore associations."""
        from personal_index.index import SearchIndex
        from personal_index.models import IndexedPage
        from personal_index.tags import TagStore

        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Seed the search index with a page and tag it.
        idx = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        idx.add_page(IndexedPage(url="https://example.com/page1", title="T"))
        tag_store = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        tag_store.add_tag_to_page("https://example.com/page1", "important")

        # Remove the page via the CLI (it uses its own store instances).
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "remove", "https://example.com/page1",
        ])
        assert result.exit_code == 0

        # Reload fresh instances from disk to observe the persisted state.
        idx2 = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        tag_store2 = TagStore(store_path=os.path.join(data_dir, "tags.json"))
        # The page is gone from the index...
        assert idx2.get_page("https://example.com/page1") is None
        # ...and its tag association is cleaned up (no orphan).
        assert tag_store2.get_pages_for_tag("important") == []
        assert tag_store2.get_tags_for_page("https://example.com/page1") == []

    def test_remove_not_found(self, runner, tmp_path):
        """Removing an unknown URL exits non-zero."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)
        result = runner.invoke(main, [
            "--data-dir", data_dir,
            "remove", "https://example.com/missing",
        ])
        assert result.exit_code == 1
        assert "not found" in result.output
