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


class TestScheduleRunPersists:
    """TICKET-253: `schedule run` must persist run state to the store."""

    def test_schedule_run_updates_store(self, tmp_path, monkeypatch):
        """A manual run records run_count, last_run and an advanced next_run."""
        import json
        from datetime import datetime, timezone

        from personal_index import cli
        from personal_index.pipeline_runner import PipelineStats

        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "schedule", "add",
            "-n", "test",
            "--url", "https://example.com",
            "--interval", "24",
        ])

        store_path = tmp_path / ".personal_index" / "schedules.json"
        before = json.loads(store_path.read_text())["test"]
        assert before["run_count"] == 0
        assert before["last_run"] is None

        class _FakeRunner:
            def run(self, seed_urls):
                return PipelineStats(pages_crawled=3)

            def close(self):
                return None

        monkeypatch.setattr(
            cli, "_create_pipeline_runner", lambda *a, **k: _FakeRunner()
        )

        # Use cli.main (same module object we patched) so the fake runner is
        # applied even if another test re-imported personal_index.cli.
        result = runner.invoke(cli.main, ["schedule", "run", "test"])
        assert result.exit_code == 0, result.output
        assert "3 pages crawled" in result.output

        after = json.loads(store_path.read_text())["test"]
        assert after["run_count"] == 1
        assert after["total_pages_indexed"] == 3
        assert after["last_run"] is not None
        # last_run parses back as an aware UTC datetime
        last = datetime.fromisoformat(after["last_run"])
        assert last.tzinfo is not None
        assert last.tzinfo == timezone.utc
        # next_run advanced by the 24h interval from last_run
        nxt = datetime.fromisoformat(after["next_run"])
        from datetime import timedelta
        assert nxt - last == timedelta(hours=24)
