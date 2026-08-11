"""End-to-end integration tests for the full crawl→extract→filter→score→tag→index→search pipeline.

These tests verify that the complete pipeline works correctly from start to finish,
using real components (not mocks) where possible.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline import Pipeline, PipelineConfig
from personal_index.tags import TagStore


class TestFullPipelineE2E:
    """Test the complete pipeline end-to-end with real components."""

    def test_pipeline_import_extract_filter_score_tag_index(self, tmp_path):
        """Test full pipeline: import → extract → filter → score → tag → index."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        # Add an interest
        pipe.interest_store.add(Interest(
            name="python",
            keywords=["python", "django", "flask"],
        ))

        # Import pages directly
        pages = [
            CrawledPage(
                url="file:///tmp/article1.txt",
                title="Python Tutorial",
                content="Python is a great programming language for web development with Django.",
            ),
            CrawledPage(
                url="file:///tmp/article2.txt",
                title="JavaScript Guide",
                content="JavaScript is the language of the web, used for frontend development.",
            ),
            CrawledPage(
                url="file:///tmp/article3.txt",
                title="Flask Framework",
                content="Flask is a lightweight Python web framework for building APIs.",
            ),
        ]

        imported = 0
        for page in pages:
            if pipe.add_page_directly(page):
                imported += 1

        assert imported >= 2  # At least python/flask articles should pass

        # Verify stats
        stats = pipe.get_stats()
        assert stats["indexed_pages"] >= 2
        assert stats["total_interests"] == 1
        assert stats["total_tags"] >= 1

    def test_pipeline_search_after_index(self, tmp_path):
        """Test that search works after indexing through the pipeline."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(
            name="tech",
            keywords=["python", "javascript", "rust", "programming"],
        ))

        page = CrawledPage(
            url="file:///tmp/tech.txt",
            title="Programming Languages",
            content="Python, JavaScript, and Rust are popular programming languages.",
        )
        assert pipe.add_page_directly(page)

        # Search should find the page
        results = pipe.search("python")
        assert len(results) >= 1
        assert "python" in results[0].title.lower() or "python" in results[0].snippet.lower()

    def test_pipeline_filters_short_content(self, tmp_path):
        """Test that the pipeline filters out short content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=50,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(
            name="test",
            keywords=["hello"],
        ))

        short_page = CrawledPage(
            url="file:///tmp/short.txt",
            title="Short",
            content="Hi there.",
        )
        assert not pipe.add_page_directly(short_page)

        long_page = CrawledPage(
            url="file:///tmp/long.txt",
            title="Long Article",
            content="Hello world! This is a much longer article with enough content to pass the minimum length filter. It discusses various topics in detail.",
        )
        assert pipe.add_page_directly(long_page)

    def test_pipeline_auto_tags_by_interest(self, tmp_path):
        """Test that pages are automatically tagged based on interests."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(
            name="webdev",
            keywords=["javascript", "react", "html", "css"],
        ))

        page = CrawledPage(
            url="https://example.com/blog/react-tutorial",
            title="React Tutorial",
            content="React is a JavaScript library for building user interfaces with HTML and CSS.",
        )
        assert pipe.add_page_directly(page)

        # Check tags were applied
        stats = pipe.get_stats()
        assert stats["total_tags"] >= 1
        assert stats["tagged_pages"] >= 1

    def test_pipeline_auto_tags_by_url_pattern(self, tmp_path):
        """Test that pages are tagged based on URL patterns."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(
            name="general",
            keywords=["content"],
        ))

        page = CrawledPage(
            url="https://github.com/example/repo",
            title="GitHub Repo",
            content="This is a content repository on GitHub with interesting code.",
        )
        assert pipe.add_page_directly(page)

        # Check that github tag was applied
        tags = pipe.tag_store.get_tags_for_page("https://github.com/example/repo")
        tag_names = [t.name for t in tags]
        assert "github" in tag_names

    def test_pipeline_persistence(self, tmp_path):
        """Test that pipeline data persists across Pipeline instances."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )

        # First instance: add content
        pipe1 = Pipeline(data_dir=data_dir, config=config)
        pipe1.interest_store.add(Interest(
            name="test",
            keywords=["hello"],
        ))
        page = CrawledPage(
            url="file:///tmp/persist.txt",
            title="Persistent Page",
            content="Hello world! This content should persist across pipeline instances.",
        )
        pipe1.add_page_directly(page)

        # Second instance: verify content persists
        pipe2 = Pipeline(data_dir=data_dir, config=config)
        stats = pipe2.get_stats()
        assert stats["indexed_pages"] >= 1
        assert stats["total_interests"] >= 1


class TestCLIE2E:
    """Test the CLI end-to-end workflows."""

    def test_cli_full_workflow(self, tmp_path, monkeypatch):
        """Test complete CLI workflow: init → interests → import → search → export."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # 2. Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django",
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language for web development with Django."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # 4. Search
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        # 5. Export
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

        # 6. Status
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0
        assert "Indexed pages:" in result.output

    def test_cli_pipeline_with_import_files(self, tmp_path, monkeypatch):
        """Test CLI pipeline command with --import-file."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        runner.invoke(main, ["init"])

        # Add interests
        runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "javascript",
        ])

        # Create test files
        file1 = tmp_path / "python.txt"
        file1.write_text("Python is a great programming language for web development.")
        file2 = tmp_path / "javascript.txt"
        file2.write_text("JavaScript is the language of the web, used for frontend development.")

        # Run pipeline
        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(file1),
            "--import-file", str(file2),
        ])
        assert result.exit_code == 0
        assert "Imported" in result.output

        # Verify search works
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

    def test_cli_pipeline_dry_run(self, tmp_path, monkeypatch):
        """Test CLI pipeline --dry-run mode."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        file1 = tmp_path / "test.txt"
        file1.write_text("Some content here.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(file1),
            "--dry-run",
        ])
        assert result.exit_code == 0
        assert "Dry run" in result.output

    def test_cli_pipeline_with_min_score(self, tmp_path, monkeypatch):
        """Test CLI pipeline with --min-score filter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python",
        ])

        file1 = tmp_path / "relevant.txt"
        file1.write_text("Python Python Python - very relevant content about Python.")
        file2 = tmp_path / "irrelevant.txt"
        file2.write_text("This content has nothing to do with Python at all.")

        result = runner.invoke(main, [
            "pipeline",
            "--import-file", str(file1),
            "--import-file", str(file2),
            "--min-score", "0.0",
        ])
        assert result.exit_code == 0

    def test_cli_tags_workflow(self, tmp_path, monkeypatch):
        """Test CLI tags workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Add tag
        result = runner.invoke(main, [
            "tags", "add", "important", "https://example.com/page1",
        ])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_cli_search_with_tag_filter(self, tmp_path, monkeypatch):
        """Test CLI search with --tag filter."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        # Import content
        article = tmp_path / "article.txt"
        article.write_text("Python programming tutorial for web development.")
        runner.invoke(main, ["import", str(article)])

        # Search with tag filter (may return empty if no tags)
        result = runner.invoke(main, ["search", "python", "--tag", "python"])
        assert result.exit_code == 0


class TestPipelineComponents:
    """Test individual pipeline components work correctly together."""

    def test_extractor_filter_scorer_chain(self, tmp_path):
        """Test that extractor → filter → scorer chain works."""
        # Extract
        extractor = ContentExtractor()
        html = """
        <html><head><title>Python Tutorial</title></head>
        <body><p>Python is a great programming language.</p></body></html>
        """
        extracted = extractor.extract(html)
        assert extracted.title == "Python Tutorial"
        assert "Python" in extracted.text

        # Build page from extraction
        page = CrawledPage(
            url="https://example.com/python",
            title=extracted.title,
            content=extracted.text,
        )

        # Filter
        store = InterestStore(store_path=str(tmp_path / "interests.json"))
        store.add(Interest(name="python", keywords=["python"]))
        filter_cfg = FilterConfig(min_content_length=10)
        content_filter = ContentFilter(config=filter_cfg, interest_store=store)
        assert content_filter.should_include(page)

        # Score
        scorer = ContentScorer()
        score_result = scorer.score_page(page, store)
        assert score_result.total > 0

    def test_index_search_roundtrip(self, tmp_path):
        """Test that indexing and searching work correctly."""
        db_path = str(tmp_path / "index.json")
        index = SearchIndex(db_path=db_path)

        # Add pages
        pages = [
            CrawledPage(url="https://a.com", title="Page A", content="Alpha content here."),
            CrawledPage(url="https://b.com", title="Page B", content="Beta content here."),
            CrawledPage(url="https://c.com", title="Page C", content="Gamma content here."),
        ]
        for page in pages:
            index.add_page(page)

        assert index.get_page_count() == 3

        # Search
        results = index.search("alpha")
        assert len(results) == 1
        assert results[0].url == "https://a.com"

        # Persistence
        index.close()
        index2 = SearchIndex(db_path=db_path)
        assert index2.get_page_count() == 3
        results2 = index2.search("beta")
        assert len(results2) == 1

    def test_tag_store_operations(self, tmp_path):
        """Test tag store CRUD operations."""
        store = TagStore(store_path=str(tmp_path / "tags.json"))

        # Create tags
        store.create_tag("python", color="#3572A5")
        store.create_tag("web", color="#2ecc71")

        # Add to pages
        store.add_tag_to_page("https://example.com/1", "python")
        store.add_tag_to_page("https://example.com/1", "web")
        store.add_tag_to_page("https://example.com/2", "python")

        # Get tags for page
        tags = store.get_tags_for_page("https://example.com/1")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "web" in tag_names

        # Get pages for tag
        pages = store.get_pages_for_tag("python")
        assert "https://example.com/1" in pages
        assert "https://example.com/2" in pages

        # List all tags
        all_tags = store.list_tags()
        assert len(all_tags) == 2

    def test_interest_store_operations(self, tmp_path):
        """Test interest store CRUD operations."""
        store = InterestStore(store_path=str(tmp_path / "interests.json"))

        # Add interests
        store.add(Interest(name="python", keywords=["python", "django"]))
        store.add(Interest(name="web", keywords=["html", "css", "javascript"]))

        # List all
        interests = store.list_all()
        assert len(interests) == 2

        # Match
        text = "Python and Django are great for web development."
        matches = store.matches_any(text, "")
        assert len(matches) >= 1

        # Score
        score = store.total_score(text)
        assert score > 0

        # Remove
        store.remove("python")
        interests = store.list_all()
        assert len(interests) == 1


class TestPipelineEdgeCases:
    """Test edge cases and error handling in the pipeline."""

    def test_pipeline_empty_content(self, tmp_path):
        """Test pipeline handles empty content gracefully."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(name="test", keywords=["test"]))

        page = CrawledPage(
            url="file:///tmp/empty.txt",
            title="Empty",
            content="",
        )
        assert not pipe.add_page_directly(page)

    def test_pipeline_no_interests(self, tmp_path):
        """Test pipeline works without any interests configured."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=10,
            min_score_threshold=0.0,
        )
        pipe = Pipeline(data_dir=data_dir, config=config)

        # No interests added - filter should still work
        page = CrawledPage(
            url="file:///tmp/no-interest.txt",
            title="No Interest Match",
            content="This content has no matching interests but should still be processable.",
        )
        # Without interests, require_interest_match should be handled
        result = pipe.add_page_directly(page)
        # Should either pass or fail gracefully
        assert isinstance(result, bool)

    def test_pipeline_duplicate_pages(self, tmp_path):
        """Test pipeline handles duplicate pages."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(name="test", keywords=["hello"]))

        page = CrawledPage(
            url="file:///tmp/dup.txt",
            title="Duplicate",
            content="Hello world! This is a test page with hello content.",
        )
        pipe.add_page_directly(page)
        pipe.add_page_directly(page)  # Duplicate

        stats = pipe.get_stats()
        assert stats["indexed_pages"] == 1  # Should only have one copy

    def test_pipeline_special_characters(self, tmp_path):
        """Test pipeline handles special characters in content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(name="unicode", keywords=["test"]))

        page = CrawledPage(
            url="file:///tmp/unicode.txt",
            title="Unicode Test 测试",
            content="Hello 世界! This is a test with unicode characters: émojis 🎉 and symbols ©®™.",
        )
        result = pipe.add_page_directly(page)
        assert isinstance(result, bool)

    def test_pipeline_very_long_content(self, tmp_path):
        """Test pipeline handles very long content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=10, min_score_threshold=0.0)
        pipe = Pipeline(data_dir=data_dir, config=config)

        pipe.interest_store.add(Interest(name="long", keywords=["test"]))

        long_content = "test " * 10000  # 50KB of content
        page = CrawledPage(
            url="file:///tmp/long.txt",
            title="Very Long Page",
            content=long_content,
        )
        result = pipe.add_page_directly(page)
        assert result is True
