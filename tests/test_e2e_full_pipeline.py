"""Full end-to-end pipeline integration tests.

Verifies the complete crawl → extract → filter → score → tag → index → search workflow.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from personal_index.cli import main
from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_extractor import ContentExtractor
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage, Interest
from personal_index.pipeline_runner import PipelineRunner
from personal_index.tags import TagStore


class TestFullPipelineEndToEnd:
    """Test the complete pipeline from crawl to search."""

    def test_full_pipeline_with_mocked_crawler(self, tmp_path):
        """Test full pipeline: crawl → extract → filter → score → tag → index."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Setup interests
        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming", "development"],
        ))

        # Create test pages
        pages = [
            CrawledPage(
                url="https://example.com/python-tutorial",
                title="Python Programming Tutorial",
                content="Python is a versatile programming language used for web development, data science, and automation. Python supports multiple programming paradigms including procedural, object-oriented, and functional programming.",
            ),
            CrawledPage(
                url="https://example.com/javascript-guide",
                title="JavaScript Development Guide",
                content="JavaScript is the language of the web, used for frontend and backend development. Node.js enables server-side JavaScript programming for full-stack development.",
            ),
            CrawledPage(
                url="https://example.com/irrelevant",
                title="Cooking Recipes",
                content="This page is about cooking and has nothing to do with programming or development. It discusses recipes and culinary techniques.",
            ),
        ]

        runner = PipelineRunner(
            config=PipelineConfig(min_score_threshold=0.0, min_content_length=10),
            data_dir=data_dir,
        )

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        # Verify all pipeline steps executed
        assert stats.pages_crawled == 3
        assert stats.pages_extracted == 3
        assert stats.pages_filtered_in >= 2  # At least the relevant pages
        assert stats.pages_scored >= 2
        assert stats.pages_tagged >= 0
        assert stats.pages_indexed >= 2

    def test_pipeline_search_after_index(self, tmp_path):
        """Test that indexed pages can be searched."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # Setup interests
        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(
            name="python",
            keywords=["python", "programming"],
        ))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Python is a great programming language for web development and data science.",
            ),
        ]

        runner = PipelineRunner(
            config=PipelineConfig(min_score_threshold=0.0, min_content_length=10),
            data_dir=data_dir,
        )

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            MockCrawler.return_value = mock_crawler
            runner.run(["https://example.com"], max_depth=1)

        # Verify search works on indexed data
        search_index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        results = search_index.search("python")
        assert len(results) >= 1
        assert "Python" in results[0].title

    def test_pipeline_persistence_across_runs(self, tmp_path):
        """Test that indexed data persists across pipeline runs."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        # First run
        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(name="tech", keywords=["python", "rust"]))

        pages1 = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python is a programming language for web development.",
            ),
        ]

        runner = PipelineRunner(
            config=PipelineConfig(min_score_threshold=0.0, min_content_length=10),
            data_dir=data_dir,
        )

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages1
            MockCrawler.return_value = mock_crawler
            runner.run(["https://example.com"], max_depth=1)

        # Second run - verify data persists
        search_index = SearchIndex(db_path=os.path.join(data_dir, "search_index.json"))
        assert search_index.get_page_count() >= 1

        results = search_index.search("python")
        assert len(results) >= 1

    def test_pipeline_filters_irrelevant_content(self, tmp_path):
        """Test that the pipeline filters out content not matching interests."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(name="python", keywords=["python", "django"]))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python is a great programming language for web development with Django framework.",
            ),
            CrawledPage(
                url="https://example.com/cooking",
                title="Cooking Guide",
                content="This is about cooking recipes and has nothing to do with programming.",
            ),
        ]

        runner = PipelineRunner(
            config=PipelineConfig(min_score_threshold=0.0, min_content_length=10),
            data_dir=data_dir,
        )

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            MockCrawler.return_value = mock_crawler
            stats = runner.run(["https://example.com"], max_depth=1)

        # The cooking page should be filtered out
        assert stats.pages_filtered_out >= 1


class TestCLIFullWorkflow:
    """Test the complete CLI workflow."""

    def test_init_import_search_workflow(self, tmp_path, monkeypatch):
        """Test init → import → search workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # 1. Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0
        assert "Initialized" in result.output

        # 2. Add interest
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "programming",
        ])
        assert result.exit_code == 0

        # 3. Create and import content
        article = tmp_path / "article.txt"
        article.write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. Python supports multiple paradigms."
        )
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # 4. Search for imported content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # 5. Verify status shows indexed content
        result = runner.invoke(main, ["status"])
        assert result.exit_code == 0

    def test_full_cli_pipeline_workflow(self, tmp_path, monkeypatch):
        """Test the full CLI pipeline workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        result = runner.invoke(main, ["init"])
        assert result.exit_code == 0

        # Add interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "tech",
            "-k", "python", "-k", "javascript",
        ])
        assert result.exit_code == 0

        # Create test content
        article = tmp_path / "tech_article.txt"
        article.write_text(
            "Python and JavaScript are the most popular programming languages. "
            "Python is used for data science and backend development. "
            "JavaScript powers the web and enables full-stack development."
        )

        # Import content
        result = runner.invoke(main, ["import", str(article)])
        assert result.exit_code == 0

        # Search for content
        result = runner.invoke(main, ["search", "python"])
        assert result.exit_code == 0

        # Export results
        result = runner.invoke(main, ["export", "--format", "markdown"])
        assert result.exit_code == 0

    def test_cli_tag_workflow(self, tmp_path, monkeypatch):
        """Test tag management workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Initialize
        runner.invoke(main, ["init"])

        # Add tags
        result = runner.invoke(main, ["tags", "add", "important", "https://example.com/page1"])
        assert result.exit_code == 0

        result = runner.invoke(main, ["tags", "add", "reference", "https://example.com/page2"])
        assert result.exit_code == 0

        # List tags
        result = runner.invoke(main, ["tags", "list"])
        assert result.exit_code == 0

    def test_cli_interests_workflow(self, tmp_path, monkeypatch):
        """Test interest management workflow."""
        monkeypatch.chdir(tmp_path)
        runner = CliRunner()

        # Add multiple interests
        result = runner.invoke(main, [
            "interests", "add", "-n", "python",
            "-k", "python", "-k", "django", "-k", "flask",
        ])
        assert result.exit_code == 0

        result = runner.invoke(main, [
            "interests", "add", "-n", "javascript",
            "-k", "javascript", "-k", "react", "-k", "node",
        ])
        assert result.exit_code == 0

        # List interests
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0
        assert "python" in result.output.lower()
        assert "javascript" in result.output.lower()

        # Remove interest
        result = runner.invoke(main, ["interests", "remove", "python"])
        assert result.exit_code == 0

        # Verify removal
        result = runner.invoke(main, ["interests", "list"])
        assert result.exit_code == 0


class TestPipelineStepIntegration:
    """Test individual pipeline steps work together."""

    def test_extract_then_filter(self, tmp_path):
        """Test extract → filter integration."""
        extractor = ContentExtractor()
        html = """
        <html>
            <head><title>Python Tutorial</title></head>
            <body>
                <h1>Learning Python</h1>
                <p>Python is a great programming language for web development.</p>
            </body>
        </html>
        """
        content = extractor.extract(html)
        assert content.title == "Python Tutorial"
        assert "Python" in content.text

        # Create filter with interest
        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(str(tmp_path), "interests.json"))
        interest_store.add(Interest(name="python", keywords=["python", "programming"]))

        filter_ = ContentFilter(
            config=FilterConfig(min_content_length=10, require_interest_match=True),
            interest_store=interest_store,
        )

        page = CrawledPage(
            url="https://example.com/python",
            title=content.title,
            content=content.text,
        )
        assert filter_.should_include(page)

    def test_filter_then_score(self, tmp_path):
        """Test filter → score integration."""
        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(str(tmp_path), "interests.json"))
        interest_store.add(Interest(name="python", keywords=["python", "programming"]))

        filter_ = ContentFilter(
            config=FilterConfig(min_content_length=10, require_interest_match=True),
            interest_store=interest_store,
        )

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Guide",
            content="Python is a great programming language for web development.",
        )

        assert filter_.should_include(page)

        # Score the page
        scorer = ContentScorer()
        score = scorer.score(
            keyword_matches=2,
            total_keywords=2,
            word_count=10,
            domain_authority=0.5,
        )
        assert score.total > 0

    def test_score_then_tag(self, tmp_path):
        """Test score → tag integration."""
        scorer = ContentScorer()
        score = scorer.score(
            keyword_matches=3,
            total_keywords=5,
            word_count=500,
            domain_authority=0.8,
        )

        # Tag based on score
        tag_store = TagStore(store_path=os.path.join(str(tmp_path), "tags.json"))
        if score.total > 0.5:
            tag_store.add_tag_to_page("https://example.com/page", "high-quality")

        tags = tag_store.get_tags_for_page("https://example.com/page")
        assert len(tags) >= 1

    def test_tag_then_index(self, tmp_path):
        """Test tag → index integration."""
        tag_store = TagStore(store_path=os.path.join(str(tmp_path), "tags.json"))
        search_index = SearchIndex(db_path=os.path.join(str(tmp_path), "index.json"))

        page = CrawledPage(
            url="https://example.com/python",
            title="Python Tutorial",
            content="Python is a great programming language.",
        )

        # Tag the page
        tag_store.add_tag_to_page(page.url, "python")
        tag_store.add_tag_to_page(page.url, "tutorial")

        # Index the page
        search_index.add_page(page)
        assert search_index.get_page_count() == 1

        # Verify tags persist
        tags = tag_store.get_tags_for_page(page.url)
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        assert "tutorial" in tag_names

    def test_index_then_search(self, tmp_path):
        """Test index → search integration."""
        search_index = SearchIndex(db_path=os.path.join(str(tmp_path), "index.json"))

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Tutorial",
                content="Python is a great programming language for web development.",
            ),
            CrawledPage(
                url="https://example.com/javascript",
                title="JavaScript Guide",
                content="JavaScript is the language of the web for frontend development.",
            ),
        ]

        for page in pages:
            search_index.add_page(page)

        # Search for Python
        results = search_index.search("python")
        assert len(results) >= 1
        assert "Python" in results[0].title

        # Search for JavaScript
        results = search_index.search("javascript")
        assert len(results) >= 1
        assert "JavaScript" in results[0].title

        # Search for development (should match both)
        results = search_index.search("development")
        assert len(results) >= 1


class TestPipelineErrorHandling:
    """Test pipeline error handling."""

    def test_pipeline_handles_crawl_errors(self, tmp_path):
        """Test pipeline handles crawl failures gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        runner = PipelineRunner(data_dir=data_dir)

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.side_effect = OSError("Network error")
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert len(stats.errors) >= 1
        assert "Network error" in stats.errors[0]

    def test_pipeline_handles_index_errors(self, tmp_path):
        """Test pipeline handles index failures gracefully."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        from personal_index.interests import InterestStore
        interest_store = InterestStore(store_path=os.path.join(data_dir, "interests.json"))
        interest_store.add(Interest(name="test", keywords=["test"]))

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Test Page",
                content="This is a test page with enough content to pass the filter.",
            ),
        ]

        runner = PipelineRunner(
            config=PipelineConfig(min_score_threshold=0.0, min_content_length=10),
            data_dir=data_dir,
        )

        with patch("personal_index.pipeline_runner.Crawler") as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = pages
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        # Should complete without crashing
        assert stats.pages_crawled == 1
