"""CLI end-to-end integration tests for the pipeline command.

Tests verify that the CLI pipeline command works correctly
from initialization through search.
"""

from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineEndToEnd:
    """Test the CLI pipeline command end-to-end."""

    def test_pipeline_import_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline command with file import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Create test files
        article1 = tmp_path / "article1.txt"
        article1.write_text(
            "Python is a versatile programming language for web development "
            "and data science applications."
        )
        article2 = tmp_path / "article2.txt"
        article2.write_text(
            "JavaScript is essential for modern web development and "
            "building interactive user interfaces."
        )

        # Run pipeline
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article1), "--import-file", str(article2)
        ])
        assert result.exit_code == 0
        assert "Imported:" in result.output

    def test_pipeline_import_and_search(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline import followed by search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development and data science."
        )

        runner.invoke(main, ["pipeline", "--import-file", str(article)])

        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "article.txt" in result.output

    def test_pipeline_with_interests(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with pre-configured interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add interest
        result = runner.invoke(main, [
            "interests", "add", "-n", "python", "-k", "python", "-k", "programming"
        ])
        assert result.exit_code == 0

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0

    def test_pipeline_min_content_length(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with minimum content length filter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        short_file = tmp_path / "short.txt"
        short_file.write_text("Too short")

        long_file = tmp_path / "long.txt"
        long_file.write_text(
            "This is a longer article about Python programming that "
            "discusses web development and data science techniques."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(short_file),
            "--import-file", str(long_file),
            "--min-content-length", "50"
        ])
        assert result.exit_code == 0

    def test_pipeline_html_files(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with HTML files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        html_file = tmp_path / "article.html"
        html_file.write_text(
            "<html><head><title>Python Guide</title></head>"
            "<body><h1>Python Tutorial</h1>"
            "<p>Python is great for web development.</p></body></html>"
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(html_file)])
        assert result.exit_code == 0

        # Search should find the extracted title
        search_result = runner.invoke(main, ["search", "python"])
        assert search_result.exit_code == 0

    def test_pipeline_full_workflow(self, tmp_path: Path, monkeypatch) -> None:
        """Test complete workflow: init → interests → pipeline → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "tech", "-k", "python", "-k", "javascript"
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python and JavaScript are popular programming languages "
            "for web development and application building."
        )
        result = runner.invoke(main, ["pipeline", "--import-file", str(article)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # 5. Export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        # 6. Status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_pipeline_no_files_or_urls(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with no files or URLs specified shows usage."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["pipeline"])
        # Exits with error when no input provided
        assert result.exit_code != 0
        assert "No URLs or files specified" in result.output

    def test_pipeline_recursive_directory(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with recursive directory import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Create directory structure
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        (docs_dir / "intro.txt").write_text(
            "Introduction to Python programming language."
        )
        (docs_dir / "advanced.txt").write_text(
            "Advanced Python techniques for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs_dir), "--recursive"
        ])
        assert result.exit_code == 0

    def test_pipeline_with_steps_option(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with specific steps enabled."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article),
            "--steps", "extract,filter,score,tag,index"
        ])
        assert result.exit_code == 0

    def test_pipeline_no_filter_flag(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with --no-filter flag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article),
            "--no-filter"
        ])
        assert result.exit_code == 0

    def test_pipeline_no_tag_flag(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with --no-tag flag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article),
            "--no-tag"
        ])
        assert result.exit_code == 0

    def test_pipeline_min_score_flag(self, tmp_path: Path, monkeypatch) -> None:
        """Test pipeline with --min-score flag."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        article = tmp_path / "article.txt"
        article.write_text(
            "Python programming language for web development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(article),
            "--min-score", "0.0"
        ])
        assert result.exit_code == 0
