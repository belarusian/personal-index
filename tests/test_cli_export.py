"""Tests for personal_index export command."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestExportCommand:
    """Test the export command."""

    def test_export_empty_index(self, tmp_path, monkeypatch):
        """Test export on empty index exits 0."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Test export in markdown format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

    def test_export_json(self, tmp_path, monkeypatch):
        """Test export in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        assert "pages" in result.output

    def test_export_csv(self, tmp_path, monkeypatch):
        """Test export in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "rank" in result.output

    def test_export_to_file(self, tmp_path, monkeypatch):
        """Test export to a file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial.")
        runner.invoke(main, ["import", str(test_file)])

        output_file = tmp_path / "export.json"
        result = runner.invoke(main, ["export", "--format", "json", "-o", str(output_file)])
        assert result.exit_code == 0
        assert output_file.exists()
