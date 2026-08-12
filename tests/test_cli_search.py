"""Tests for personal_index search command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestSearchCommand:
    """Test the search command."""

    def test_search_empty_index(self, tmp_path, monkeypatch):
        """Test search on empty index exits 0."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 0

    def test_search_after_import(self, tmp_path, monkeypatch):
        """Test search finds content after import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python is a great programming language for web development.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_search_with_limit(self, tmp_path, monkeypatch):
        """Test search with limit option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "-l", "5"])
        assert result.exit_code == 0

    def test_search_json_format(self, tmp_path, monkeypatch):
        """Test search with JSON output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "json"])
        assert result.exit_code == 0

    def test_search_csv_format(self, tmp_path, monkeypatch):
        """Test search with CSV output format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["search", "python", "--format", "csv"])
        assert result.exit_code == 0
