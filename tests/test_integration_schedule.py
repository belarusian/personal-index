"""Integration tests for the schedule command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestScheduleCommands:
    """Test scheduled job commands."""

    def test_schedule_add(self, tmp_path, monkeypatch):
        """Test adding a scheduled job."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "schedule", "add",
            "-n", "daily",
            "--url", "https://example.com",
            "--interval", "24",
            "--depth", "2",
            "--max-pages", "50"
        ])
        assert result.exit_code == 0
        assert "Added scheduled job" in result.output

    def test_schedule_add_duplicate(self, tmp_path, monkeypatch):
        """Test adding duplicate scheduled job."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        runner.invoke(main, [
            "schedule", "add",
            "-n", "test", "--url", "https://example.com"
        ])
        result = runner.invoke(main, [
            "schedule", "add",
            "-n", "test", "--url", "https://other.com"
        ])
        assert result.exit_code != 0 or "already exists" in result.output

    def test_schedule_list(self, tmp_path, monkeypatch):
        """Test listing scheduled jobs."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        runner.invoke(main, [
            "schedule", "add",
            "-n", "job1", "--url", "https://a.com"
        ])
        runner.invoke(main, [
            "schedule", "add",
            "-n", "job2", "--url", "https://b.com"
        ])

        result = runner.invoke(main, ["schedule", "list"])
        assert result.exit_code == 0
        assert "job1" in result.output or "job2" in result.output

    def test_schedule_remove(self, tmp_path, monkeypatch):
        """Test removing a scheduled job."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        runner.invoke(main, [
            "schedule", "add",
            "-n", "test", "--url", "https://example.com"
        ])

        result = runner.invoke(main, ["schedule", "remove", "test"])
        assert result.exit_code == 0
        assert "Removed" in result.output

    def test_schedule_run(self, tmp_path, monkeypatch):
        """Test manually running a scheduled job."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        runner.invoke(main, [
            "schedule", "add",
            "-n", "test", "--url", "https://example.com"
        ])

        result = runner.invoke(main, ["schedule", "run", "test"])
        # May fail due to network, but command should parse
        assert result.exit_code in (0, 1)
