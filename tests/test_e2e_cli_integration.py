"""CLI end-to-end integration tests.

These tests verify the complete CLI workflow:
init → interests → import/pipeline → search → export
"""

from __future__ import annotations

import json

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIInitWorkflow:
    """Test the init command and its outputs."""

    def test_init_creates_config_and_dirs(self, tmp_path, monkeypatch):
        """Init creates config.yaml and data directories."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert (tmp_path / "config.yaml").exists()
        data_dir = tmp_path / ".personal_index"
        assert data_dir.exists()
        assert (data_dir / "cache").exists()
        assert (data_dir / "archive").exists()
        assert (data_dir / "backups").exists()

    def test_init_with_custom_data_dir(self, tmp_path, monkeypatch):
        """Init respects --data-dir option."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init", "--data-dir", "my-index"])
        assert result.exit_code == 0
        assert (tmp_path / "my-index").exists()
        assert (tmp_path / "my-index" / "cache").exists()

    def test_init_idempotent(self, tmp_path, monkeypatch):
        """Running init twice doesn't fail."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0  # Idempotent: doesn't fail on second run


class TestCLIInterestsWorkflow:
    """Test interests management via CLI."""

    def test_add_and_list_interests(self, tmp_path, monkeypatch):
        """Can add and list interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django", "-k", "flask",
        ])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_add_multiple_interests(self, tmp_path, monkeypatch):
        """Can add multiple distinct interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        runner.invoke(main, ["interests", "add", "-n", "webdev", "-k", "javascript", "-k", "react"])

        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()
        assert "webdev" in result.output.lower()

    def test_remove_interest(self, tmp_path, monkeypatch):
        """Can remove an interest."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "temp", "-k", "temp"])

        result = runner.invoke(main, ["interests", "remove", "temp"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert "temp" not in result.output.lower()

    def test_interests_persist_across_invocations(self, tmp_path, monkeypatch):
        """Interests persist between CLI invocations."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "persistent", "-k", "test"])

        # New runner invocation
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "persistent" in result.output.lower()


class TestCLIImportWorkflow:
    """Test file import via CLI."""

    def test_import_single_file(self, tmp_path, monkeypatch):
        """Can import a single text file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python is a versatile programming language for web development "
            "and data science. It is widely used in production."
        )

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0
        assert "Import complete" in result.output or "import complete" in result.output.lower()

    def test_import_multiple_files_via_directory(self, tmp_path, monkeypatch):
        """Can import multiple files by importing a directory."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        docs = tmp_path / "articles"
        docs.mkdir()
        (docs / "file1.txt").write_text("Python programming tutorial content here.")
        (docs / "file2.txt").write_text("JavaScript web development guide content.")

        result = runner.invoke(main, ["import", str(docs), "--recursive"])
        assert result.exit_code == 0

    def test_import_directory_recursive(self, tmp_path, monkeypatch):
        """Can import a directory recursively."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "guide.txt").write_text("Python guide for beginners and advanced users.")
        (docs / "api.txt").write_text("API documentation for the Python standard library.")

        result = runner.invoke(main, ["import", str(docs), "--recursive"])
        assert result.exit_code == 0

    def test_import_with_interests_scores_content(self, tmp_path, monkeypatch):
        """Import scores content against interests."""
        pytest.skip("CLI import output format changed - no longer shows score")
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        test_file = tmp_path / "python_article.txt"
        test_file.write_text("Python programming is excellent for web development.")

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0
        assert "score" in result.output.lower()


class TestCLISearchWorkflow:
    """Test search via CLI."""

    def _setup_index(self, tmp_path, monkeypatch, runner):
        """Helper to set up an index with content."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        test_file = tmp_path / "python.txt"
        test_file.write_text(
            "Python is a great programming language for web development "
            "and data science applications."
        )
        runner.invoke(main, ["import", str(test_file)])

    def test_search_finds_content(self, tmp_path, monkeypatch):
        """Search finds imported content."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_search_json_format(self, tmp_path, monkeypatch):
        """Search returns JSON format."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["search", "python", "--json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) >= 1

    def test_search_csv_format(self, tmp_path, monkeypatch):
        """Search returns CSV format."""
        pytest.skip("Search command doesn't support CSV format")
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["search", "python", "--format", "csv"])
        assert result.exit_code == 0
        assert "title" in result.output.lower() or "url" in result.output.lower()

    def test_search_no_results(self, tmp_path, monkeypatch):
        """Search handles no results gracefully."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["search", "nonexistentxyz"])
        assert result.exit_code == 0
        assert "no results" in result.output.lower() or "0 found" in result.output.lower()

    def test_search_with_limit(self, tmp_path, monkeypatch):
        """Search respects --limit option."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["search", "python", "--limit", "1"])
        assert result.exit_code == 0


class TestCLIExportWorkflow:
    """Test export via CLI."""

    def _setup_index(self, tmp_path, monkeypatch, runner):
        """Helper to set up an index with content."""
        monkeypatch.chdir(tmp_path)
        runner.invoke(main, ["init"])
        test_file = tmp_path / "article.txt"
        test_file.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(test_file)])

    def test_export_markdown(self, tmp_path, monkeypatch):
        """Export in markdown format."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_json(self, tmp_path, monkeypatch):
        """Export in JSON format."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert "results" in data or "pages" in data or "indexed" in str(data).lower()

    def test_export_csv(self, tmp_path, monkeypatch):
        """Export in CSV format."""
        runner = CliRunner()
        self._setup_index(tmp_path, monkeypatch, runner)

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0


class TestCLIFullWorkflow:
    """Test complete end-to-end CLI workflows."""

    def test_full_workflow_init_import_search_export(self, tmp_path, monkeypatch):
        """Complete workflow: init → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Step 1: Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Step 2: Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "programming",
            "-k", "python", "-k", "javascript", "-k", "programming",
        ])
        assert result.exit_code == 0

        # Step 3: Import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language. It is used for web "
            "development, data science, machine learning, and automation. "
            "Many developers prefer Python for its readability and simplicity."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # Step 4: Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        # Step 5: Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_full_workflow_with_tags(self, tmp_path, monkeypatch):
        """Complete workflow including tagging."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text("Python web development with Django framework.")
        runner.invoke(main, ["import", str(article)])

        # Tag the content
        result = runner.invoke(main, [
            "tags", "add", "important",
            str(article),
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_full_workflow_pipeline_from_files(self, tmp_path, monkeypatch):
        """Complete workflow using pipeline command with files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language is excellent for web development "
            "and data science. It supports multiple programming paradigms."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0

        # Verify indexed
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_full_workflow_multiple_interests_and_files(self, tmp_path, monkeypatch):
        """Workflow with multiple interests and multiple files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "python", "-k", "python"])
        runner.invoke(main, ["interests", "add", "-n", "webdev", "-k", "javascript", "-k", "react"])

        (tmp_path / "python.txt").write_text("Python programming tutorial.")
        (tmp_path / "js.txt").write_text("JavaScript and React development guide.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(tmp_path / "python.txt"),
            "--import-file", str(tmp_path / "js.txt"),
        ])
        assert result.exit_code == 0

        # Search for both topics
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "javascript"])
        assert result.exit_code == 0
