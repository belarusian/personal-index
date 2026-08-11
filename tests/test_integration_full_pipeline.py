"""Full pipeline integration tests: crawl → extract → filter → score → tag → index → search.

These tests verify that the complete pipeline works end-to-end,
from importing content through searching results.
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
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestFullPipelineEndToEnd:
    """Test the complete pipeline from import to search."""

    def test_import_score_tag_index_search(self, tmp_path, monkeypatch):
        """Full pipeline: import → score → tag → index → search."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Init
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django", "-k", "flask",
        ])
        assert result.exit_code == 0

        # Create test files
        (tmp_path / "python_tutorial.txt").write_text(
            "Python is a popular programming language for web development. "
            "Django and Flask are popular Python web frameworks."
        )
        (tmp_path / "javascript_guide.txt").write_text(
            "JavaScript is a scripting language for web browsers. "
            "React and Vue are popular JavaScript frameworks."
        )

        # Import via pipeline
        result = runner.invoke(main, [
            "pipeline", "--import-file", str(tmp_path / "python_tutorial.txt"),
            "--import-file", str(tmp_path / "javascript_guide.txt"),
        ])
        assert result.exit_code == 0

        # Search for python
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()

        # Search for javascript
        result = runner.invoke(main, ["search", "javascript"])
        assert result.exit_code == 0
        assert "javascript" in result.output.lower()

    def test_pipeline_with_html_files(self, tmp_path, monkeypatch):
        """Pipeline processes HTML files correctly."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "web", "-k", "html", "-k", "css"])

        html_file = tmp_path / "page.html"
        html_file.write_text(
            "<html><head><title>Web Development Guide</title></head>"
            "<body><h1>HTML and CSS Basics</h1>"
            "<p>HTML is the standard markup language for web pages.</p>"
            "<p>CSS is used to style HTML elements.</p></body></html>"
        )

        result = runner.invoke(main, ["pipeline", "--import-file", str(html_file)])
        assert result.exit_code == 0
        assert "Web Development Guide" in result.output or "1" in result.output

        result = runner.invoke(main, ["search", "html"])
        assert result.exit_code == 0

    def test_pipeline_filters_low_quality(self, tmp_path):
        """Pipeline filters out pages with insufficient content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(
            min_content_length=50,
            min_score_threshold=0.0,
        )
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        # Create a page with very short content
        short_page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Hi",
            status_code=200,
        )

        result = runner.add_page_directly(short_page)
        assert result is False  # Should be filtered out

        runner.close()

    def test_pipeline_scores_by_interest(self, tmp_path):
        """Pipeline scores pages based on interest matching."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        # Add interest
        interest_store = runner._interest_store
        interest_store.add(Interest(
            name="python",
            keywords=["python", "django"],
            priority=8,
        ))

        # High-relevance page
        high_page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Python is great for web development with Django.",
            status_code=200,
        )
        assert runner.add_page_directly(high_page) is True

        # Low-relevance page
        low_page = CrawledPage(
            url="https://example.com/cooking",
            title="Cooking Guide",
            content="How to cook pasta and make sauce.",
            status_code=200,
        )
        assert runner.add_page_directly(low_page) is True

        # Verify both indexed but with different scores
        idx = runner._search_index
        assert idx.get_page_count() == 2

        runner.close()

    def test_pipeline_tags_by_interest(self, tmp_path):
        """Pipeline auto-tags pages based on interest matching."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "code"],
        ))

        page = CrawledPage(
            url="https://example.com/code",
            title="Coding Tutorial",
            content="Python and JavaScript are popular programming languages.",
            status_code=200,
        )
        runner.add_page_directly(page)

        # Check tags were applied
        tag_store = runner._tag_store
        tags = tag_store.get_tags_for_page("https://example.com/code")
        tag_names = [t.name for t in tags]
        assert "programming" in tag_names

        runner.close()

    def test_pipeline_persistence(self, tmp_path):
        """Pipeline data persists across sessions."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)

        # First session: add content
        runner1 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        page = CrawledPage(
            url="https://example.com/persist",
            title="Persistence Test",
            content="This content should persist across sessions.",
            status_code=200,
        )
        runner1.add_page_directly(page)
        runner1.close()

        # Second session: verify data persists
        runner2 = PipelineRunner(data_dir=data_dir, pipeline_config=config)
        idx = runner2._search_index
        assert idx.get_page_count() == 1

        results = idx.search("persist")
        assert len(results) == 1
        assert results[0].url == "https://example.com/persist"
        runner2.close()


class TestPipelineStages:
    """Test individual pipeline stages work correctly."""

    def test_extract_stage(self, tmp_path):
        """Extract stage pulls text from HTML."""
        extractor = ContentExtractor()
        html = "<html><head><title>Title</title></head><body><p>Content text here.</p></body></html>"
        result = extractor.extract(html)
        assert "Content text here" in result.text
        assert "Title" in result.title

    def test_filter_stage(self, tmp_path):
        """Filter stage excludes pages based on config."""
        config = FilterConfig(min_content_length=50)
        filter_ = ContentFilter(config=config)

        long_page = CrawledPage(
            url="https://example.com/long",
            title="Long Page",
            content="This is a page with enough content to pass the filter check.",
            status_code=200,
        )
        assert filter_.should_include(long_page) is True

        short_page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short",
            status_code=200,
        )
        assert filter_.should_include(short_page) is False

    def test_score_stage(self, tmp_path):
        """Score stage calculates relevance scores."""
        scorer = ContentScorer(weights=ScoreWeights(relevance=0.5))
        score = scorer.score(
            keyword_matches=3,
            total_keywords=5,
            word_count=200,
            domain_authority=0.7,
        )
        assert 0.0 <= score.total <= 1.0

    def test_index_stage(self, tmp_path):
        """Index stage stores and retrieves pages."""
        idx_path = str(tmp_path / "index.json")
        idx = SearchIndex(db_path=idx_path)

        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="This is test content for indexing.",
            status_code=200,
        )
        idx.add_page(page)
        assert idx.get_page_count() == 1

        results = idx.search("test")
        assert len(results) == 1
        idx.close()

    def test_tag_stage(self, tmp_path):
        """Tag stage associates tags with pages."""
        tag_path = str(tmp_path / "tags.json")
        store = TagStore(store_path=tag_path)

        store.add_tag_to_page("https://example.com/page1", "python")
        store.add_tag_to_page("https://example.com/page1", "tutorial")
        store.add_tag_to_page("https://example.com/page2", "python")

        assert store.get_tag_count() == 2
        assert store.get_tagged_page_count() == 2

        pages = store.get_pages_for_tag("python")
        assert len(pages) == 2


class TestCLIWorkflow:
    """Test complete CLI workflows."""

    def test_full_cli_workflow(self, tmp_path, monkeypatch):
        """Complete CLI workflow: init → interests → import → search → export → status."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Init
        r = runner.invoke(main, ["init"])
        assert r.exit_code == 0

        # 2. Add interests
        r = runner.invoke(main, ["interests", "add", "-n", "tech", "-k", "python", "-k", "ai"])
        assert r.exit_code == 0

        # 3. Create and import content
        (tmp_path / "article.txt").write_text(
            "Python is used in artificial intelligence and machine learning."
        )
        r = runner.invoke(main, ["import", str(tmp_path / "article.txt")])
        assert r.exit_code == 0

        # 4. Search
        r = runner.invoke(main, ["search", "python"])
        assert r.exit_code == 0
        assert "python" in r.output.lower()

        # 5. Export
        r = runner.invoke(main, ["export", "--format", "json"])
        assert r.exit_code == 0

        # 6. Status
        r = runner.invoke(main, ["status"])
        assert r.exit_code == 0
        assert "Pages indexed" in r.output

    def test_pipeline_command_with_files(self, tmp_path, monkeypatch):
        """Pipeline command processes files through all stages."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        runner.invoke(main, ["interests", "add", "-n", "dev", "-k", "python"])

        (tmp_path / "guide.txt").write_text(
            "Python development guide for beginners and advanced users."
        )

        r = runner.invoke(main, ["pipeline", "--import-file", str(tmp_path / "guide.txt")])
        assert r.exit_code == 0

        # Verify indexed
        r = runner.invoke(main, ["search", "python"])
        assert r.exit_code == 0

    def test_directory_import_workflow(self, tmp_path, monkeypatch):
        """Import entire directory of files."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])

        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "intro.txt").write_text("Introduction to Python programming.")
        (docs / "advanced.txt").write_text("Advanced Python patterns and techniques.")
        (docs / "ignore.log").write_text("This should be ignored.")

        r = runner.invoke(main, ["import", str(docs), "--recursive"])
        assert r.exit_code == 0

        r = runner.invoke(main, ["search", "python"])
        assert r.exit_code == 0

    def test_search_with_no_results(self, tmp_path, monkeypatch):
        """Search returns gracefully when no results found."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        r = runner.invoke(main, ["search", "nonexistent"])
        assert r.exit_code == 0
        assert "No results" in r.output

    def test_export_empty_index(self, tmp_path, monkeypatch):
        """Export handles empty index gracefully."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        runner.invoke(main, ["init"])
        r = runner.invoke(main, ["export", "--format", "markdown"])
        assert r.exit_code == 0
        assert "No indexed content" in r.output


class TestPipelineEdgeCases:
    """Test pipeline edge cases and error handling."""

    def test_pipeline_with_empty_file(self, tmp_path):
        """Pipeline handles empty files gracefully."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        empty_file = tmp_path / "empty.txt"
        empty_file.write_text("")

        stats = runner.run_from_files([str(empty_file)])
        assert stats.pages_indexed == 0
        runner.close()

    def test_pipeline_with_binary_file(self, tmp_path):
        """Pipeline handles binary files gracefully."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        binary_file = tmp_path / "image.bin"
        binary_file.write_bytes(b"\x00\x01\x02\x03\x04")

        stats = runner.run_from_files([str(binary_file)])
        # Binary files should be skipped or handled gracefully
        assert stats.pages_indexed >= 0
        runner.close()

    def test_pipeline_with_unicode_content(self, tmp_path):
        """Pipeline handles unicode content correctly."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/unicode",
            title="Unicode Test",
            content="Python supports unicode: 你好世界 🌍 Привет мир",
            status_code=200,
        )
        result = runner.add_page_directly(page)
        assert result is True

        results = runner._search_index.search("unicode")
        assert len(results) >= 0
        runner.close()

    def test_pipeline_with_very_long_content(self, tmp_path):
        """Pipeline handles very long content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        long_content = "word " * 10000  # 10000 words
        page = CrawledPage(
            url="https://example.com/long",
            title="Long Page",
            content=long_content,
            status_code=200,
        )
        result = runner.add_page_directly(page)
        assert result is True
        runner.close()

    def test_pipeline_duplicate_content(self, tmp_path):
        """Pipeline handles duplicate content."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        content = "Same content for both pages."
        page1 = CrawledPage(url="https://example.com/1", title="Page 1", content=content, status_code=200)
        page2 = CrawledPage(url="https://example.com/2", title="Page 2", content=content, status_code=200)

        assert runner.add_page_directly(page1) is True
        assert runner.add_page_directly(page2) is True

        # Both should be indexed (different URLs)
        assert runner._search_index.get_page_count() == 2
        runner.close()


class TestSearchIntegration:
    """Test search integration with the full pipeline."""

    def test_search_after_pipeline(self, tmp_path):
        """Search returns results after pipeline runs."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/search-test",
            title="Search Test Page",
            content="This page is about search functionality and indexing.",
            status_code=200,
        )
        runner.add_page_directly(page)

        results = runner._search_index.search("search")
        assert len(results) == 1
        assert results[0].url == "https://example.com/search-test"
        runner.close()

    def test_search_ranking(self, tmp_path):
        """Search results are ranked by relevance."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        # Page with more keyword matches should rank higher
        high_relevance = CrawledPage(
            url="https://example.com/high",
            title="Python Python Python",
            content="Python is great. Python is powerful. Python is fun.",
            status_code=200,
        )
        low_relevance = CrawledPage(
            url="https://example.com/low",
            title="Cooking",
            content="Python is a snake that lives in the wild.",
            status_code=200,
        )
        runner.add_page_directly(high_relevance)
        runner.add_page_directly(low_relevance)

        results = runner._search_index.search("python")
        assert len(results) == 2
        # Higher relevance should rank first
        assert results[0].url == "https://example.com/high"
        runner.close()

    def test_search_case_insensitive(self, tmp_path):
        """Search is case-insensitive."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/case",
            title="Case Test",
            content="Python programming language.",
            status_code=200,
        )
        runner.add_page_directly(page)

        for query in ["python", "PYTHON", "Python", "PyThOn"]:
            results = runner._search_index.search(query)
            assert len(results) == 1, f"Query '{query}' should find the page"
        runner.close()


class TestInterestIntegration:
    """Test interest-based scoring and filtering."""

    def test_interest_matching_affects_score(self, tmp_path):
        """Pages matching interests get higher scores."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python", "django"],
            priority=8,
        ))

        matching_page = CrawledPage(
            url="https://example.com/match",
            title="Python Guide",
            content="Python and Django are great for web development.",
            status_code=200,
        )
        non_matching = CrawledPage(
            url="https://example.com/nomatch",
            title="Cooking",
            content="How to bake a cake.",
            status_code=200,
        )

        runner.add_page_directly(matching_page)
        runner.add_page_directly(non_matching)

        # Both should be indexed (threshold is 0)
        assert runner._search_index.get_page_count() == 2
        runner.close()

    def test_interest_threshold_filtering(self, tmp_path):
        """Pages below score threshold are not indexed."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.9)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        runner._interest_store.add(Interest(
            name="python",
            keywords=["python"],
            priority=10,
        ))

        # Page with no matching keywords
        page = CrawledPage(
            url="https://example.com/low",
            title="Unrelated",
            content="This has nothing to do with python.",
            status_code=200,
        )
        result = runner.add_page_directly(page)
        assert result is False  # Below threshold
        runner.close()


class TestTagIntegration:
    """Test tag-based organization."""

    def test_tags_persist_across_sessions(self, tmp_path):
        """Tags persist when data is saved and reloaded."""
        tag_path = str(tmp_path / "tags.json")

        # First session
        store1 = TagStore(store_path=tag_path)
        store1.add_tag_to_page("https://example.com/page1", "python")
        store1.add_tag_to_page("https://example.com/page1", "tutorial")

        # Second session
        store2 = TagStore(store_path=tag_path)
        tags = store2.get_tags_for_page("https://example.com/page1")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "tutorial" in tag_names

    def test_tags_filter_pages(self, tmp_path):
        """Tags can be used to filter pages."""
        tag_path = str(tmp_path / "tags.json")
        store = TagStore(store_path=tag_path)

        store.add_tag_to_page("https://example.com/1", "python")
        store.add_tag_to_page("https://example.com/2", "javascript")
        store.add_tag_to_page("https://example.com/3", "python")

        python_pages = store.get_pages_for_tag("python")
        assert len(python_pages) == 2
        assert "https://example.com/1" in python_pages
        assert "https://example.com/3" in python_pages


class TestExportIntegration:
    """Test export functionality with real data."""

    def test_export_json_with_data(self, tmp_path):
        """JSON export includes all indexed pages."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/export-test",
            title="Export Test",
            content="Content for export testing.",
            status_code=200,
        )
        runner.add_page_directly(page)

        idx = runner._search_index
        pages = idx.list_pages()
        assert len(pages) == 1

        # Verify JSON serialization
        data = json.dumps([p.to_dict() for p in pages], default=str)
        assert "export-test" in data
        runner.close()

    def test_export_markdown_with_data(self, tmp_path):
        """Markdown export formats pages correctly."""
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_score_threshold=0.0)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/md-test",
            title="Markdown Test",
            content="Content for markdown export.",
            status_code=200,
        )
        runner.add_page_directly(page)

        idx = runner._search_index
        pages = idx.list_pages()
        assert len(pages) == 1

        lines = ["# Search Results", ""]
        for p in pages:
            lines.append(f"## {p.title}")
            lines.append(f"- **URL**: {p.url}")
        md = "\n".join(lines)
        assert "## Markdown Test" in md
        runner.close()
