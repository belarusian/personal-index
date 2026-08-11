"""CLI workflow integration tests.

Tests complete CLI workflows using the Click test runner,
verifying the full user journey from init to search.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestCLIWorkflow:
    """Test complete CLI workflows end-to-end."""

    def test_complete_user_journey(self):
        """Test the complete user journey: init → interests → import → search → export."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Step 1: Initialize
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0
            assert "Initialized" in result.output

            # Step 2: Add interests
            result = runner.invoke(main, [
                "interests", "add",
                "-n", "programming",
                "-k", "python", "-k", "javascript", "-k", "rust",
            ])
            assert result.exit_code == 0

            # Step 3: Verify interests
            result = runner.invoke(main, ["interests", "list"])
            assert result.exit_code == 0
            assert "programming" in result.output

            # Step 4: Import content
            article = Path("python_guide.txt")
            article.write_text(
                "Python is a versatile programming language used for web development, "
                "data science, and automation. Python supports multiple paradigms."
            )
            result = runner.invoke(main, ["import", str(article)])
            assert result.exit_code == 0

            # Step 5: Search
            result = runner.invoke(main, ["search", "python"])
            assert result.exit_code == 0

            # Step 6: List pages
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0

            # Step 7: Stats
            result = runner.invoke(main, ["stats"])
            assert result.exit_code == 0

            # Step 8: Export
            result = runner.invoke(main, ["export", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "results" in data or "pages" in data

    def test_pipeline_command_with_files(self):
        """Test the pipeline command with file imports."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize
            runner.invoke(main, ["init"])

            # Add interests
            runner.invoke(main, [
                "interests", "add", "-n", "tech",
                "-k", "python", "-k", "programming",
            ])

            # Create test files
            docs_dir = Path("docs")
            docs_dir.mkdir()
            (docs_dir / "python.txt").write_text(
                "Python programming language for web development and data science."
            )
            (docs_dir / "rust.txt").write_text(
                "Rust programming language for systems programming and performance."
            )

            # Run pipeline
            result = runner.invoke(main, [
                "pipeline",
                "--import-file", str(docs_dir / "python.txt"),
                "--import-file", str(docs_dir / "rust.txt"),
            ])
            assert result.exit_code == 0
            assert "Pipeline complete" in result.output or "Indexed:" in result.output

            # Verify indexed
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0

    def test_search_with_tag_filter(self):
        """Test searching with tag filter."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            # Import content
            article = Path("article.txt")
            article.write_text("Python programming tutorial for web development.")
            runner.invoke(main, ["import", str(article)])

            # Add a tag
            runner.invoke(main, ["tags", "add", "tutorial", "file://*"])

            # Search with tag filter
            result = runner.invoke(main, ["search", "python", "--tag", "tutorial"])
            assert result.exit_code == 0

    def test_export_all_formats(self):
        """Test exporting in all supported formats."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language for web development.")
            runner.invoke(main, ["import", str(article)])

            # JSON export
            result = runner.invoke(main, ["export", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert isinstance(data, dict)

            # CSV export
            result = runner.invoke(main, ["export", "--format", "csv"])
            assert result.exit_code == 0
            assert "title" in result.output.lower() or "url" in result.output.lower()

            # Markdown export
            result = runner.invoke(main, ["export", "--format", "markdown"])
            assert result.exit_code == 0
            assert "#" in result.output

    def test_clear_and_reindex(self):
        """Test clearing the index and re-importing."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language.")
            runner.invoke(main, ["import", str(article)])

            # Verify indexed
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0

            # Clear
            result = runner.invoke(main, ["clear", "--index", "--tags", "--no-interests"])
            assert result.exit_code == 0

            # Verify cleared
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0

            # Re-import
            runner.invoke(main, ["import", str(article)])
            result = runner.invoke(main, ["list"])
            assert result.exit_code == 0

    def test_doctor_command(self):
        """Test the doctor diagnostic command."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language.")
            runner.invoke(main, ["import", str(article)])

            result = runner.invoke(main, ["doctor"])
            assert result.exit_code == 0
            assert "Health Check" in result.output or "checks" in result.output.lower()

    def test_top_command(self):
        """Test the top pages command."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            # Import multiple files
            for i in range(3):
                article = Path(f"article_{i}.txt")
                article.write_text(f"Python programming article number {i}.")
                runner.invoke(main, ["import", str(article)])

            result = runner.invoke(main, ["top", "--limit", "2"])
            assert result.exit_code == 0

    def test_remove_command(self):
        """Test removing a page from the index."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language.")
            runner.invoke(main, ["import", str(article)])

            # Get the URL
            result = runner.invoke(main, ["list", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            if data.get("pages"):
                url = data["pages"][0]["url"]
                result = runner.invoke(main, ["remove", url])
                assert result.exit_code == 0

    def test_version_command(self):
        """Test the version command."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_help_command(self):
        """Test the help command."""
        runner = CliRunner()

        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "personal-index" in result.output.lower() or "Personal Index" in result.output

        # Subcommand help
        result = runner.invoke(main, ["pipeline", "--help"])
        assert result.exit_code == 0
        assert "pipeline" in result.output.lower()

        result = runner.invoke(main, ["search", "--help"])
        assert result.exit_code == 0
        assert "search" in result.output.lower()

    def test_import_recursive_directory(self):
        """Test importing a directory recursively."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            # Create nested directory structure
            docs = Path("docs")
            docs.mkdir()
            (docs / "guide.txt").write_text("Python programming guide.")
            (docs / "tutorial.txt").write_text("JavaScript tutorial for beginners.")

            nested = docs / "advanced"
            nested.mkdir()
            (nested / "deep.txt").write_text("Advanced Rust programming concepts.")

            result = runner.invoke(main, ["import", str(docs), "--recursive"])
            assert result.exit_code == 0

            # Verify all files were imported
            result = runner.invoke(main, ["list", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data.get("pages", [])) >= 3

    def test_search_json_output(self):
        """Test search with JSON output format."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language for web development.")
            runner.invoke(main, ["import", str(article)])

            result = runner.invoke(main, ["search", "python", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert "results" in data
            assert len(data["results"]) >= 1

    def test_list_sort_options(self):
        """Test list command with different sort options."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            for i in range(3):
                article = Path(f"article_{i}.txt")
                article.write_text(f"Content for article {i}.")
                runner.invoke(main, ["import", str(article)])

            # Sort by score
            result = runner.invoke(main, ["list", "--sort", "score"])
            assert result.exit_code == 0

            # Sort by title
            result = runner.invoke(main, ["list", "--sort", "title"])
            assert result.exit_code == 0

            # Sort by date
            result = runner.invoke(main, ["list", "--sort", "date"])
            assert result.exit_code == 0

    def test_interests_add_remove(self):
        """Test adding and removing interests."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            # Add interest
            result = runner.invoke(main, [
                "interests", "add", "-n", "test", "-k", "python",
            ])
            assert result.exit_code == 0

            # Verify
            result = runner.invoke(main, ["interests", "list"])
            assert result.exit_code == 0
            assert "test" in result.output

            # Remove
            result = runner.invoke(main, ["interests", "remove", "test"])
            assert result.exit_code == 0

            # Verify removed
            result = runner.invoke(main, ["interests", "list"])
            assert result.exit_code == 0
            assert "test" not in result.output

    def test_tags_add_list(self):
        """Test adding and listing tags."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            # Add tag
            result = runner.invoke(main, ["tags", "add", "important", "https://example.com"])
            assert result.exit_code == 0

            # List tags
            result = runner.invoke(main, ["tags", "list"])
            assert result.exit_code == 0

    def test_pipeline_with_min_score(self):
        """Test pipeline with minimum score threshold."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            runner.invoke(main, ["init"])

            article = Path("article.txt")
            article.write_text("Python programming language for web development.")

            result = runner.invoke(main, [
                "pipeline",
                "--import-file", str(article),
                "--min-score", "0.0",
            ])
            assert result.exit_code == 0

    def test_full_workflow_with_pipeline(self):
        """Test complete workflow using pipeline command instead of import."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Initialize
            result = runner.invoke(main, ["init"])
            assert result.exit_code == 0

            # Add interests
            result = runner.invoke(main, [
                "interests", "add", "-n", "programming",
                "-k", "python", "-k", "javascript",
            ])
            assert result.exit_code == 0

            # Create test files
            (Path("python.txt")).write_text(
                "Python is a great programming language for web development."
            )
            (Path("javascript.txt")).write_text(
                "JavaScript is the language of the web, used for frontend development."
            )

            # Run pipeline
            result = runner.invoke(main, [
                "pipeline",
                "--import-file", "python.txt",
                "--import-file", "javascript.txt",
            ])
            assert result.exit_code == 0

            # Search for python
            result = runner.invoke(main, ["search", "python"])
            assert result.exit_code == 0

            # Search for javascript
            result = runner.invoke(main, ["search", "javascript"])
            assert result.exit_code == 0

            # List all pages
            result = runner.invoke(main, ["list", "--format", "json"])
            assert result.exit_code == 0
            data = json.loads(result.output)
            assert len(data.get("pages", [])) >= 2

            # Export results
            result = runner.invoke(main, ["export", "--format", "json"])
            assert result.exit_code == 0
