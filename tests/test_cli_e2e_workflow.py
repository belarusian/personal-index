"""End-to-end workflow tests for personal_index CLI."""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestEndToEndWorkflow:
    """Test complete CLI workflows from init through export."""

    def test_full_workflow_init_import_search_export(self, tmp_path, monkeypatch):
        """Test complete workflow: init -> import -> search -> export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Step 2: Import content
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation."
        )
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # Step 3: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Step 4: Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_workflow_with_multiple_files(self, tmp_path, monkeypatch):
        """Test workflow importing multiple files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        (tmp_path / "file1.txt").write_text("Python programming basics.")
        (tmp_path / "file2.txt").write_text("JavaScript web development.")
        (tmp_path / "file3.txt").write_text("Rust systems programming.")

        result = runner.invoke(main, ["import", str(tmp_path), "--recursive"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "programming"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_workflow_status_after_import(self, tmp_path, monkeypatch):
        """Test status command reflects imported content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial for beginners.")
        runner.invoke(main, ["import", str(test_file)])

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status" in result.output or "status" in result.output.lower()
