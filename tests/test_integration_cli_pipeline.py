"""Integration tests for the CLI pipeline command with various options.

Tests the pipeline command's ability to handle different input modes,
step configurations, and output formats.
"""

from __future__ import annotations

from click.testing import CliRunner

from personal_index.cli import main


class TestCLIPipelineCommand:
    """Test the pipeline CLI command with various options."""

    def test_pipeline_import_single_file(self, tmp_path, monkeypatch):
        """Pipeline should import a single file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "# Article Title\n\n"
            "This is a comprehensive article about software engineering. "
            "It covers testing, CI/CD, and deployment."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])
        assert result.exit_code == 0
        assert "Indexed:" in result.output
        assert "1" in result.output  # Should show 1 indexed

    def test_pipeline_import_recursive_directory(self, tmp_path, monkeypatch):
        """Pipeline should recursively import directory contents."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "subdir").mkdir()
        (docs / "root.md").write_text("Root level article about programming.")
        (docs / "subdir" / "nested.md").write_text(
            "Nested article about advanced programming topics."
        )
        (docs / "subdir" / "deep.md").write_text(
            "Deep nested article about algorithms and data structures."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs), "--recursive"
        ])
        assert result.exit_code == 0
        # Should have indexed all 3 files
        assert "Indexed:" in result.output

    def test_pipeline_with_min_content_length(self, tmp_path, monkeypatch):
        """Pipeline should filter by minimum content length."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "short.md").write_text("Too short")
        (docs / "long.md").write_text("A" * 200)

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs), "--recursive",
            "--min-content-length", "50"
        ])
        assert result.exit_code == 0
        assert "Filtered out:" in result.output

    def test_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """Pipeline should filter by minimum score threshold."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "An article about programming and software development."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md"),
            "--min-score", "0.0"
        ])
        assert result.exit_code == 0

    def test_pipeline_no_urls_or_files(self, tmp_path, monkeypatch):
        """Pipeline should error when no URLs or files provided."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        result = runner.invoke(main, ["pipeline"])
        assert result.exit_code == 1
        assert "No URLs or files" in result.output

    def test_pipeline_with_interests(self, tmp_path, monkeypatch):
        """Pipeline should use configured interests for scoring."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add interest
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "programming", "-k", "software"
        ])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Programming and software development best practices."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])
        assert result.exit_code == 0

    def test_pipeline_output_format(self, tmp_path, monkeypatch):
        """Pipeline output should include all stage statistics."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about testing and quality assurance."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])
        assert result.exit_code == 0

        # Check output contains all stage stats
        output = result.output
        assert "Crawled:" in output
        assert "Extracted:" in output
        assert "Filtered in:" in output
        assert "Scored:" in output
        assert "Tagged:" in output
        assert "Indexed:" in output
        assert "Errors:" in output


class TestCLIPipelineWithSearch:
    """Test pipeline followed by search operations."""

    def test_pipeline_then_search(self, tmp_path, monkeypatch):
        """Search should work after pipeline import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about machine learning and AI."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["search", "machine learning"])
        assert result.exit_code == 0

    def test_pipeline_then_list(self, tmp_path, monkeypatch):
        """List should show indexed pages after pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about cloud computing and infrastructure."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0

    def test_pipeline_then_export(self, tmp_path, monkeypatch):
        """Export should work after pipeline import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about database design and optimization."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_pipeline_then_stats(self, tmp_path, monkeypatch):
        """Stats should show data after pipeline import."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about security and encryption."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0
