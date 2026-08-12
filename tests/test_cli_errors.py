"""Error handling tests for personal_index CLI."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIErrorHandling:
    """Test CLI error handling and edge cases."""

    def test_crawl_no_url_fails(self, tmp_path, monkeypatch):
        """Test crawl without URL exits non-zero."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["crawl"])
        assert result.exit_code != 0

    def test_search_no_query_fails(self, tmp_path, monkeypatch):
        """Test search without query argument."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search"])
        assert result.exit_code != 0

    def test_export_invalid_format_fails(self, tmp_path, monkeypatch):
        """Test export with invalid format exits non-zero."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["export", "--format", "xml"])
        assert result.exit_code != 0

    def test_init_idempotent(self, tmp_path, monkeypatch):
        """Test running init twice does not fail."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result1 = runner.invoke(main, ["init"])
        assert result1.exit_code == 0
        result2 = runner.invoke(main, ["init"])
        assert result2.exit_code == 0

    def test_search_nonexistent_term(self, tmp_path, monkeypatch):
        """Test search for term that doesn't exist exits 0."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search", "xyznonexistent"])
        assert result.exit_code == 0
