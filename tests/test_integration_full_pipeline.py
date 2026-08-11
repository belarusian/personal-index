"""Full pipeline integration tests: crawl → extract → filter → score → tag → index → search.

These tests verify the complete end-to-end pipeline works correctly
using file-based input (no network required).
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineE2E:
    """Test the complete pipeline from file import through search."""

    def test_full_pipeline_files_to_search(self, tmp_path):
        """Import files → pipeline → search should return results."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        # Create test files
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "python_guide.md").write_text(
            "# Python Programming Guide\n\n"
            "Python is a versatile programming language. It supports "
            "object-oriented, functional, and procedural programming. "
            "Python is widely used in web development, data science, "
            "and machine learning applications."
        )
        (docs / "javascript_guide.md").write_text(
            "# JavaScript Guide\n\n"
            "JavaScript is the language of the web. It runs in browsers "
            "and on servers with Node.js. JavaScript supports event-driven "
            "and functional programming paradigms."
        )
        (docs / "cooking_recipe.txt").write_text(
            "Chocolate Cake Recipe\n\n"
            "Ingredients: flour, sugar, cocoa powder, eggs, butter.\n"
            "Instructions: Mix dry ingredients, add wet ingredients, "
            "bake at 350F for 30 minutes."
        )

        # Set up interests
        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"]
        ))

        # Run pipeline
        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=50)
        )
        stats = runner.run_from_files([
            str(docs / "python_guide.md"),
            str(docs / "javascript_guide.md"),
            str(docs / "cooking_recipe.txt"),
        ])
        runner.close()

        # Verify pipeline processed all files
        assert stats.pages_crawled == 3
        assert stats.pages_extracted == 3
        assert stats.pages_filtered_in == 3
        assert stats.pages_scored == 3
        assert stats.pages_tagged == 3
        assert stats.pages_indexed == 3
        assert len(stats.errors) == 0

        # Verify search works
        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) > 0
        assert any("python" in r.title.lower() or "python" in r.snippet.lower()
                   for r in results)

        results = index.search("javascript")
        assert len(results) > 0

        results = index.search("chocolate")
        assert len(results) > 0

    def test_pipeline_with_filtering(self, tmp_path):
        """Pipeline should filter out content below minimum length."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "short.txt").write_text("Too short")
        (docs / "long.txt").write_text(
            "This is a properly sized article with enough content "
            "to pass the minimum content length filter in the pipeline. "
            "It discusses important topics in detail."
        )

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=50)
        )
        stats = runner.run_from_files([
            str(docs / "short.txt"),
            str(docs / "long.txt"),
        ])
        runner.close()

        assert stats.pages_crawled == 2
        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1
        assert stats.pages_indexed == 1

    def test_pipeline_interest_matching(self, tmp_path):
        """Pipeline should match interests and boost scores."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "relevant.txt").write_text(
            "Machine learning and artificial intelligence are transforming "
            "the technology industry. Deep learning models achieve state-of-the-art "
            "results in many domains."
        )
        (docs / "irrelevant.txt").write_text(
            "The weather today is sunny and warm. Good day for a walk "
            "in the park. Birds are singing and flowers are blooming."
        )

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="tech",
            keywords=["machine learning", "artificial intelligence", "deep learning"]
        ))

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=20)
        )
        stats = runner.run_from_files([
            str(docs / "relevant.txt"),
            str(docs / "irrelevant.txt"),
        ])
        runner.close()

        assert stats.interests_matched > 0
        assert stats.pages_indexed == 2

    def test_pipeline_persistence(self, tmp_path):
        """Pipeline results should persist across runner instances."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Important article about software engineering best practices. "
            "Clean code, testing, and documentation are essential."
        )

        # First run
        runner1 = PipelineRunner(data_dir=data_dir)
        stats1 = runner1.run_from_files([str(docs / "article.txt")])
        runner1.close()

        # Second run - should load existing index
        runner2 = PipelineRunner(data_dir=data_dir)
        index = runner2._search_index
        assert index.get_page_count() >= 1
        runner2.close()

    def test_pipeline_error_handling(self, tmp_path):
        """Pipeline should handle errors gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "good.txt").write_text(
            "This is a valid article with sufficient content for "
            "the pipeline to process and index correctly."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "good.txt"),
            str(docs / "nonexistent.txt"),  # Will cause error
        ])
        runner.close()

        assert stats.pages_indexed >= 1
        assert len(stats.errors) >= 1  # Should have error for missing file


class TestCLIEndToEnd:
    """Test CLI commands work end-to-end."""

    def test_cli_init_and_pipeline(self, tmp_path, monkeypatch):
        """CLI init → pipeline → search should work."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Create test file
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.md").write_text(
            "# Test Article\n\n"
            "This article covers important topics in software development. "
            "It discusses testing, CI/CD, and deployment strategies."
        )

        # Add interest
        result = runner.invoke(main, [
            "interests", "add", "dev",
            "-k", "software", "-k", "testing", "-k", "development"
        ])
        assert result.exit_code == 0

        # Run pipeline with file import
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "test.md")
        ])
        assert result.exit_code == 0
        assert "Indexed:" in result.output

        # Search
        result = runner.invoke(main, ["search", "testing"])
        assert result.exit_code == 0
        assert "test" in result.output.lower() or "article" in result.output.lower()

    def test_cli_full_workflow(self, tmp_path, monkeypatch):
        """Complete CLI workflow: init → interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interests
        result = runner.invoke(main, [
            "interests", "add", "python",
            "-k", "python", "-k", "programming"
        ])
        assert result.exit_code == 0

        # Create and import files
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article1.md").write_text(
            "Python programming is fun and powerful. "
            "It supports multiple paradigms."
        )
        (docs / "article2.md").write_text(
            "Web development with frameworks like Django and Flask. "
            "Building REST APIs and web applications."
        )

        result = runner.invoke(main, [
            "pipeline", "--import-file", str(docs), "--recursive"
        ])
        assert result.exit_code == 0

        # Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Export
        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_cli_interests_workflow(self, tmp_path, monkeypatch):
        """Test complete interests management workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add multiple interests
        for name, keywords in [
            ("tech", ["python", "javascript"]),
            ("science", ["physics", "chemistry"]),
            ("cooking", ["recipe", "baking"]),
        ]:
            result = runner.invoke(main, [
                "interests", "add", name,
                "-k", keywords[0], "-k", keywords[1]
            ])
            assert result.exit_code == 0

        # List interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "tech" in result.output
        assert "science" in result.output
        assert "cooking" in result.output

        # Remove one
        result = runner.invoke(main, ["interests", "remove", "cooking"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["interests", "list"])
        assert "cooking" not in result.output

    def test_cli_tags_workflow(self, tmp_path, monkeypatch):
        """Test complete tags management workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add tags
        result = runner.invoke(main, [
            "tags", "add", "important", "https://example.com/page1"
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "tags", "add", "read-later", "https://example.com/page2"
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0
        assert "important" in result.output

    def test_cli_stats_command(self, tmp_path, monkeypatch):
        """Test stats command after pipeline run."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "An article about programming languages and their features. "
            "This covers syntax, performance, and ecosystem."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["stats"])
        assert result.exit_code == 0


class TestPipelineStages:
    """Test individual pipeline stages work correctly."""

    def test_crawl_stage(self, tmp_path):
        """Crawl stage should process files."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text("Test content here.")

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        assert stats.pages_crawled == 1

    def test_extract_stage(self, tmp_path):
        """Extract stage should parse content."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.html").write_text(
            "<html><body><h1>Title</h1><p>Content here.</p></body></html>"
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "test.html")])
        runner.close()

        assert stats.pages_extracted == 1

    def test_filter_stage(self, tmp_path):
        """Filter stage should apply content length filter."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "short.txt").write_text("Hi")
        (docs / "long.txt").write_text("A" * 200)

        runner = PipelineRunner(
            data_dir=data_dir,
            pipeline_config=PipelineConfig(min_content_length=50)
        )
        stats = runner.run_from_files([
            str(docs / "short.txt"),
            str(docs / "long.txt"),
        ])
        runner.close()

        assert stats.pages_filtered_in == 1
        assert stats.pages_filtered_out == 1

    def test_score_stage(self, tmp_path):
        """Score stage should assign scores."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text(
            "Python programming language is great for web development."
        )

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="python", keywords=["python", "programming"]
        ))

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        assert stats.pages_scored == 1

    def test_tag_stage(self, tmp_path):
        """Tag stage should apply tags."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text(
            "Machine learning and AI are transforming technology."
        )

        interest_store = InterestStore(
            store_path=os.path.join(data_dir, "interests.json")
        )
        interest_store.add(Interest(
            name="ai", keywords=["machine learning", "AI"]
        ))

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        assert stats.pages_tagged == 1
        assert stats.tags_applied > 0

    def test_index_stage(self, tmp_path):
        """Index stage should make content searchable."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text(
            "Docker containers and Kubernetes orchestration for "
            "modern cloud-native applications."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("docker")
        assert len(results) > 0

        results = index.search("kubernetes")
        assert len(results) > 0


class TestSearchIntegration:
    """Test search functionality after indexing."""

    def test_search_relevance_ordering(self, tmp_path):
        """Search results should be ordered by relevance."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        # High relevance: many keyword matches
        (docs / "high.txt").write_text(
            "Python Python Python programming. Python is great. "
            "Python libraries, Python frameworks, Python ecosystem."
        )
        # Low relevance: few keyword matches
        (docs / "low.txt").write_text(
            "The weather is nice today. Python is mentioned once."
        )

        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run_from_files([
            str(docs / "high.txt"),
            str(docs / "low.txt"),
        ])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("python")
        assert len(results) >= 2
        # First result should be the high-relevance page
        assert results[0].relevance_score >= results[1].relevance_score

    def test_search_no_results(self, tmp_path):
        """Search for non-existent terms should return empty."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text("About programming and code.")

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("xyznonexistent123")
        assert len(results) == 0

    def test_search_with_snippets(self, tmp_path):
        """Search results should include content snippets."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir)

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "test.txt").write_text(
            "This article discusses advanced Python decorators "
            "and metaclasses for expert developers."
        )

        runner = PipelineRunner(data_dir=data_dir)
        runner.run_from_files([str(docs / "test.txt")])
        runner.close()

        index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = index.search("decorators")
        assert len(results) > 0
        assert len(results[0].snippet) > 0


class TestExportIntegration:
    """Test export functionality after indexing."""

    def test_export_json_after_pipeline(self, tmp_path, monkeypatch):
        """JSON export should work after pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about testing strategies in software development."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["export", "--format", "json"])
        assert result.exit_code == 0

    def test_export_markdown_after_pipeline(self, tmp_path, monkeypatch):
        """Markdown export should work after pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about testing strategies in software development."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_export_csv_after_pipeline(self, tmp_path, monkeypatch):
        """CSV export should work after pipeline."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.md").write_text(
            "Article about testing strategies in software development."
        )

        runner.invoke(main, [
            "pipeline", "--import-file", str(docs / "article.md")
        ])

        result = runner.invoke(main, ["export", "--format", "csv"])
        assert result.exit_code == 0
