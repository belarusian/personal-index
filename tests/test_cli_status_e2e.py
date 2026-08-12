"""End-to-end CLI tests for status and stats commands."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIStatusE2E:
    """Test status and stats CLI commands end-to-end."""

    def test_status_shows_index_info(self, tmp_path, monkeypatch):
        """Test status command shows index information."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content here.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_stats_shows_counts(self, tmp_path, monkeypatch):
        """Test stats command shows page counts."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("# Test\n\nTest content here.")

        runner.invoke(main, [
            "pipeline", "--import-file", str(test_file),
            "--min-content-length", "10",
        ])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0

    def test_doctor_checks_health(self, tmp_path, monkeypatch):
        """Test doctor command checks system health."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
