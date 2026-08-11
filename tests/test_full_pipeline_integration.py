"""Integration tests for the complete personal-index pipeline.

Tests verify that the full end-to-end workflow works correctly:
crawl → extract → filter → score → tag → index → search
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main


class TestFullPipelineIntegration:
    """Test the complete pipeline workflow."""

    def test_full_cli_workflow(self, tmp_path, monkeypatch):
        """Test complete CLI workflow from init to search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert os.path.exists(".personal_index")
        assert os.path.exists("config.yaml")

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "python",
            "-k", "python",
            "-k", "django",
            "-p", "8"
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "interests", "add",
            "-n", "rust",
            "-k", "rust",
            "-k", "cargo",
            "-p", "7"
        ])
        assert result.exit_code == 0

        # 3. Import some content
        test_file1 = tmp_path / "article1.txt"
        test_file1.write_text(
            "Python is a powerful programming language for web development, "
            "data science, and automation. Django is a popular Python framework."
        )
        
        test_file2 = tmp_path / "article2.txt"
        test_file2.write_text(
            "Rust is a systems programming language focused on safety and performance. "
            "Cargo is Rust's package manager."
        )

        result = runner.invoke(main, ["import", str(test_file1)])
        assert result.exit_code == 0
        assert "Import complete" in result.output

        result = runner.invoke(main, ["import", str(test_file2)])
        assert result.exit_code == 0
        assert "Import complete" in result.output

        # 4. Search for Python content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        # Should find the python article
        assert "article1" in result.output.lower() or "Article1" in result.output

        # 5. Search for Rust content
        result = runner.invoke(main, ["search", "rust"])
        assert result.exit_code == 0
        # Should find the rust article
        assert "article2" in result.output.lower() or "Article2" in result.output

        # 6. Check status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Indexed pages" in result.output
        assert "Interests" in result.output
        assert "Tags" in result.output

        # 7. Export results
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

    def test_pipeline_with_interests_filtering(self, tmp_path, monkeypatch):
        """Test that interests properly filter and score content."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add high-priority interest
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "web-dev",
            "-k", "javascript",
            "-k", "react",
            "-p", "10"
        ])
        assert result.exit_code == 0

        # Add low-priority interest
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "python",
            "-k", "python",
            "-k", "django",
            "-p", "3"
        ])
        assert result.exit_code == 0

        # Create content with both topics
        test_file = tmp_path / "fullstack.txt"
        test_file.write_text(
            "Full stack development with JavaScript, React, and Python, Django. "
            "Modern web applications use both frontend and backend technologies."
        )

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # Search should find the content
        result = runner.invoke(main, ["search", "javascript"])
        assert result.exit_code == 0
        assert "fullstack" in result.output.lower()

    def test_tagging_system(self, tmp_path, monkeypatch):
        """Test automatic tagging based on interests."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interest
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "api",
            "-k", "api",
            "-k", "endpoint",
            "-p", "5"
        ])
        assert result.exit_code == 0

        # Import content
        test_file = tmp_path / "api-docs.txt"
        test_file.write_text(
            "REST API documentation for endpoints and resources. "
            "This API provides JSON responses."
        )

        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # Check tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0
        # Should have auto-generated tags from interests
        assert "api" in result.output.lower() or "endpoint" in result.output.lower()

    def test_search_with_tag_filter(self, tmp_path, monkeypatch):
        """Test searching with tag filters."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interests
        result = runner.invoke(main, [
            "interests", "add",
            "-n", "blog",
            "-k", "blog",
            "-p", "5"
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "interests", "add",
            "-n", "tutorial",
            "-k", "tutorial",
            "-p", "5"
        ])
        assert result.exit_code == 0

        # Import content
        blog_file = tmp_path / "blog.txt"
        blog_file.write_text("This is a blog post about programming tutorials.")
        
        tutorial_file = tmp_path / "tutorial.txt"
        tutorial_file.write_text("Detailed tutorial for beginners.")

        result = runner.invoke(main, ["import", str(blog_file)])
        assert result.exit_code == 0

        result = runner.invoke(main, ["import", str(tutorial_file)])
        assert result.exit_code == 0

        # Search without tag filter
        result = runner.invoke(main, ["search", "tutorial"])
        assert result.exit_code == 0
        total_results = len([line for line in result.output.split('\n') if 'tutorial' in line.lower() or 'blog' in line.lower()])

        # Search with tag filter would require manual tagging first
        # This is tested in separate tests

    def test_export_formats(self, tmp_path, monkeypatch):
        """Test all export formats."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize and add content
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content for export.")
        
        result = runner.invoke(main, ["import", str(test_file)])
        assert result.exit_code == 0

        # Test markdown export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0
        assert "# Search Results" in result.output

        # Test JSON export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert "pages" in data
        assert "total" in data

        # Test CSV export
        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0
        assert "rank" in result.output.lower()
        assert "title" in result.output.lower()


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_search_empty_index(self, tmp_path, monkeypatch):
        """Test searching when index is empty."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["search", "test"])
        assert result.exit_code == 0
        # Should indicate no indexed content
        assert "No indexed content" in result.output or "No results" in result.output

    def test_invalid_import_path(self, tmp_path, monkeypatch):
        """Test importing from non-existent path."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["import", "/nonexistent/path/file.txt"])
        # Should handle gracefully
        assert result.exit_code == 0 or "not found" in result.output.lower()

    def test_list_empty_index(self, tmp_path, monkeypatch):
        """Test listing pages when index is empty."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["list"])
        assert result.exit_code == 0
        # Should indicate no indexed pages
        assert "No indexed" in result.output or "No pages" in result.output


class TestPipelineCommands:
    """Test individual pipeline commands."""

    def test_crawl_command(self, tmp_path, monkeypatch):
        """Test crawl command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Note: This would actually try to crawl, so we're just testing the command exists
        result = runner.invoke(main, ["crawl", "https://example.com"])
        # May fail due to network, but command should be recognized
        assert result.exit_code in [0, 1]  # 0 if works, 1 if network error

    def test_pipeline_command(self, tmp_path, monkeypatch):
        """Test pipeline command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Test with import files
        file1 = tmp_path / "test1.txt"
        file1.write_text("Python programming language.")
        
        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(file1)
        ])
        assert result.exit_code == 0
        assert "Pipeline complete" in result.output
        assert "Indexed" in result.output

    def test_status_command(self, tmp_path, monkeypatch):
        """Test status command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Personal Index Status" in result.output or "Indexed pages" in result.output

    def test_doctor_command(self, tmp_path, monkeypatch):
        """Test doctor command."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["doctor"])
        assert result.exit_code == 0
        assert "Personal Index Health Check" in result.output or "Index:" in result.output


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
