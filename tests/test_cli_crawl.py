"""Tests for personal_index crawl command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestCrawlCommand:
    """Test the crawl command."""

    def test_crawl_without_url_exits_nonzero(self, tmp_path, monkeypatch):
        """Test crawl without URL argument exits with error."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["crawl"])
        assert result.exit_code != 0

    def test_crawl_with_url_exits_zero(self, tmp_path, monkeypatch):
        """Test crawl with a valid URL exits 0."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        # Initialize first
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["crawl", "https://example.com"])
        assert result.exit_code == 0

    def test_crawl_shows_crawl_output(self, tmp_path, monkeypatch):
        """Test crawl shows crawled pages in output."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["crawl", "https://example.com"])
        assert result.exit_code == 0
        assert "Crawled" in result.output or "crawled" in result.output.lower()

    def test_crawl_with_depth_option(self, tmp_path, monkeypatch):
        """Test crawl with custom depth."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["crawl", "https://example.com", "-d", "1"])
        assert result.exit_code == 0

    def test_crawl_with_max_pages_option(self, tmp_path, monkeypatch):
        """Test crawl with custom max pages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["crawl", "https://example.com", "-m", "5"])
        assert result.exit_code == 0
