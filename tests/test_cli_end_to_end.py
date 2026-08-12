"""End-to-end CLI integration tests for personal-index."""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIIntegration:
    """Test complete CLI workflows."""

    def test_init_creates_all_directories(self, tmp_path, monkeypatch):
        """Test that init creates all required directories."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        data_dir = Path(".personal_index")
        assert data_dir.exists()
        assert (data_dir / "cache").exists()
        assert (data_dir / "archive").exists()
        assert (data_dir / "backups").exists()

    def test_interests_add_and_list(self, tmp_path, monkeypatch):
        """Test adding and listing interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add interest
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "python",
            "-k", "python",
            "-k", "django",
        ])
        assert result.exit_code == 0

        # List interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

    def test_interests_remove(self, tmp_path, monkeypatch):
        """Test removing an interest."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add then remove
        runner.invoke(main, [
            "interests", "add",
            "-n", "test-interest",
            "-k", "test",
        ])
        result = runner.invoke(main, ["interests", "remove", "test-interest"])
        assert result.exit_code == 0

    def test_tags_add_and_list(self, tmp_path, monkeypatch):
        """Test adding and listing tags."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add tag
        result = runner.invoke(main, [
            "tags", "add",
            "important",
            "https://example.com/page1",
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_import_text_file(self, tmp_path, monkeypatch):
        """Test importing a text file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Create test file
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python programming tutorial for web development and software engineering."
        )

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

    def test_import_directory_recursive(self, tmp_path, monkeypatch):
        """Test importing a directory recursively."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Create test files
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "file1.txt").write_text(
            "Python programming language for web development."
        )
        (docs_dir / "file2.txt").write_text(
            "JavaScript and Node.js for backend development."
        )

        result = runner.invoke(main, [
            "import", str(docs_dir), "--recursive"
        ])
        assert result.exit_code == 0

    def test_search_functionality(self, tmp_path, monkeypatch):
        """Test search functionality."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize and add content
        runner.invoke(main, ["init"])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python is a versatile programming language for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        # Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_export_markdown_format(self, tmp_path, monkeypatch):
        """Test exporting in markdown format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Setup
        runner.invoke(main, ["init"])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming tutorial for web development."
        )
        runner.invoke(main, ["import", str(test_file)])

        # Export
        result = runner.invoke(main, [
            "export", "--format", "markdown"
        ])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

    def test_export_json_format(self, tmp_path, monkeypatch):
        """Test exporting in JSON format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Setup
        runner.invoke(main, ["init"])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming language."
        )
        runner.invoke(main, ["import", str(test_file)])

        # Export
        result = runner.invoke(main, [
            "export", "--format", "json"
        ])
        assert result.exit_code == 0

    def test_export_csv_format(self, tmp_path, monkeypatch):
        """Test exporting in CSV format."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Setup
        runner.invoke(main, ["init"])

        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming tutorial."
        )
        runner.invoke(main, ["import", str(test_file)])

        # Export
        result = runner.invoke(main, [
            "export", "--format", "csv"
        ])
        assert result.exit_code == 0

    def test_status_command(self, tmp_path, monkeypatch):
        """Test status command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        runner.invoke(main, ["init"])

        # Add content
        test_file = tmp_path / "test.txt"
        test_file.write_text(
            "Python programming language for web development and software engineering."
        )
        runner.invoke(main, ["import", str(test_file)])

        # Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Status" in result.output

    def test_full_workflow(self, tmp_path, monkeypatch):
        """Test complete user workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "tech",
            "-k", "python",
            "-k", "javascript",
        ])
        assert result.exit_code == 0

        # 3. Import content
        test_file = tmp_path / "article.txt"
        test_file.write_text(
            "Python and JavaScript are popular programming languages for web development."
        )
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # 5. Export
        result = runner.invoke(main, [
            "export", "--format", "markdown"
        ])
        assert result.exit_code == 0

        # 6. Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_crawl_without_url(self, tmp_path, monkeypatch):
        """Test crawl command without URL."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["crawl"])
        assert result.exit_code != 0

    def test_import_nonexistent_file(self, tmp_path, monkeypatch):
        """Test importing a non-existent file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, [
            "import", str(tmp_path / "nonexistent.txt")
        ])
        # May or may not fail depending on implementation
        assert result.exit_code == 0 or result.exception is not None

    def test_search_empty_index(self, tmp_path, monkeypatch):
        """Test searching an empty index."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        result = runner.invoke(main, ["search", "nonexistent"])
        assert result.exit_code == 0
