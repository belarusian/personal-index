"""End-to-end integration tests for the full pipeline.

Tests the complete crawl → extract → filter → score → tag → index pipeline
using in-memory components and mock data.
"""

from __future__ import annotations

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer, ScoreWeights
from personal_index.index import SearchIndex
from personal_index.interests import InterestStore
from personal_index.models import CrawledPage, Interest, InterestType
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineRunnerBasic:
    """Test the PipelineRunner with in-memory data."""

    def test_runner_initializes_correctly(self, tmp_path):
        """PipelineRunner should initialize all components."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        assert runner.data_dir == str(tmp_path)
        assert runner._interest_store is not None
        assert runner._tag_store is not None
        assert runner._search_index is not None
        assert runner._filter is not None
        assert runner._scorer is not None
        runner.close()

    def test_runner_creates_data_dirs(self, tmp_path):
        """PipelineRunner should create required subdirectories."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        assert os.path.isdir(os.path.join(tmp_path, "cache"))
        assert os.path.isdir(os.path.join(tmp_path, "archive"))
        assert os.path.isdir(os.path.join(tmp_path, "backups"))
        runner.close()

    def test_add_page_directly_success(self, tmp_path):
        """Adding a page directly should index it."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        # Add an interest first
        interest = Interest(name="python", keywords=["python", "programming"])
        runner._interest_store.add(interest)

        page = CrawledPage(
            url="https://example.com/python-article",
            title="Python Programming Guide",
            content="Python is a great programming language for web development.",
            matched_interests=["python"],
        )

        result = runner.add_page_directly(page)
        assert result is True
        assert runner._search_index.get_page_count() == 1
        runner.close()

    def test_add_page_directly_empty_content_rejected(self, tmp_path):
        """Pages with empty content should be rejected."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        page = CrawledPage(
            url="https://example.com/empty",
            title="Empty Page",
            content="",
        )

        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_add_page_directly_short_content_rejected(self, tmp_path):
        """Pages below min_content_length should be rejected."""
        config = PipelineConfig(min_content_length=100)
        runner = PipelineRunner(data_dir=str(tmp_path), pipeline_config=config)

        page = CrawledPage(
            url="https://example.com/short",
            title="Short",
            content="Too short content.",
        )

        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_add_page_directly_applies_tags(self, tmp_path):
        """Adding a page should apply matching interest tags."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        interest = Interest(name="webdev", keywords=["web", "development"])
        runner._interest_store.add(interest)

        page = CrawledPage(
            url="https://example.com/webdev",
            title="Web Development Tips",
            content="Web development is fun and rewarding for everyone.",
        )

        runner.add_page_directly(page)
        tags = runner._tag_store.get_tags_for_page("https://example.com/webdev")
        tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
        assert "webdev" in tag_names
        runner.close()

    def test_add_page_directly_scores_page(self, tmp_path):
        """Adding a page should compute a relevance score."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        interest = Interest(name="tech", keywords=["tech", "technology"])
        runner._interest_store.add(interest)

        page = CrawledPage(
            url="https://example.com/tech",
            title="Tech News",
            content="Technology news and updates from around the world.",
            matched_interests=["tech"],
        )

        runner.add_page_directly(page)
        indexed = runner._search_index.get_page("https://example.com/tech")
        assert indexed is not None
        assert indexed.score > 0
        runner.close()

    def test_get_stats_returns_dict(self, tmp_path):
        """get_stats should return a dictionary with expected keys."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = runner.get_stats()
        assert isinstance(stats, dict)
        assert "indexed_pages" in stats
        assert "total_interests" in stats
        assert "total_tags" in stats
        assert "tagged_pages" in stats
        runner.close()


class TestPipelineStages:
    """Test individual pipeline stages."""

    def test_extract_stage_preserves_content(self, tmp_path):
        """Extract stage should preserve page content."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        pages = [
            CrawledPage(
                url="https://example.com/page1",
                title="Page One",
                content="This is the content of page one.",
            ),
            CrawledPage(
                url="https://example.com/page2",
                title="Page Two",
                content="This is the content of page two.",
            ),
        ]

        result = runner._extract_stage(pages, stats)
        assert len(result) == 2
        assert stats.pages_extracted == 2
        runner.close()

    def test_extract_stage_removes_empty_pages(self, tmp_path):
        """Extract stage should remove pages with no content."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        pages = [
            CrawledPage(url="https://example.com/good", title="Good", content="Has content"),
            CrawledPage(url="https://example.com/empty", title="Empty", content=""),
            CrawledPage(url="https://example.com/blank", title="Blank", content="   "),
        ]

        result = runner._extract_stage(pages, stats)
        assert len(result) == 1
        assert result[0].url == "https://example.com/good"
        runner.close()

    def test_filter_stage_includes_good_content(self, tmp_path):
        """Filter stage should include pages meeting criteria."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        pages = [
            CrawledPage(
                url="https://example.com/good",
                title="Good Page",
                content="This is a good page with enough content to pass the filter.",
            ),
        ]

        result = runner._filter_stage(pages, stats)
        assert len(result) == 1
        assert stats.pages_filtered_in == 1
        runner.close()

    def test_filter_stage_excludes_short_content(self, tmp_path):
        """Filter stage should exclude pages with too little content."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        # Set a high min_content_length
        runner._filter.config.min_content_length = 100
        stats = PipelineStats()

        pages = [
            CrawledPage(
                url="https://example.com/short",
                title="Short",
                content="Too short.",
            ),
        ]

        result = runner._filter_stage(pages, stats)
        assert len(result) == 0
        assert stats.pages_filtered_out == 1
        runner.close()

    def test_score_stage_assigns_scores(self, tmp_path):
        """Score stage should assign relevance scores to pages."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        interest = Interest(name="python", keywords=["python"])
        runner._interest_store.add(interest)

        pages = [
            CrawledPage(
                url="https://example.com/python",
                title="Python Guide",
                content="Python programming language guide.",
                matched_interests=["python"],
            ),
        ]

        result = runner._score_stage(pages, stats)
        assert len(result) == 1
        assert result[0].relevance_score > 0
        assert stats.pages_scored == 1
        runner.close()

    def test_tag_stage_applies_interest_tags(self, tmp_path):
        """Tag stage should apply tags based on interest matches."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        interest = Interest(name="ai", keywords=["artificial", "intelligence", "ai"])
        runner._interest_store.add(interest)

        pages = [
            CrawledPage(
                url="https://example.com/ai",
                title="AI News",
                content="Artificial intelligence is transforming the world.",
            ),
        ]

        runner._tag_stage(pages, stats)
        tags = runner._tag_store.get_tags_for_page("https://example.com/ai")
        tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
        assert "ai" in tag_names
        assert stats.pages_tagged == 1
        assert stats.tags_applied > 0
        runner.close()

    def test_index_stage_persists_pages(self, tmp_path):
        """Index stage should persist pages to the search index."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = PipelineStats()

        pages = [
            CrawledPage(
                url="https://example.com/indexed",
                title="Indexed Page",
                content="This page should be indexed.",
                relevance_score=0.8,
            ),
        ]

        runner._index_stage(pages, stats)
        assert runner._search_index.get_page_count() == 1
        assert stats.pages_indexed == 1
        runner.close()


class TestPipelineRunnerRun:
    """Test the full run() method with mocked crawling."""

    def test_run_with_mocked_crawler(self, tmp_path):
        """Full pipeline run should process pages through all stages."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        # Add an interest
        interest = Interest(name="test", keywords=["test", "example"])
        runner._interest_store.add(interest)

        # Mock the crawler
        mock_page = CrawledPage(
            url="https://example.com/test-page",
            title="Test Page",
            content="This is a test page with enough content to pass all filters and be indexed properly.",
            matched_interests=["test"],
        )
        runner._crawler.crawl = MagicMock(return_value=[mock_page])

        stats = runner.run(["https://example.com"])

        assert stats.pages_crawled == 1
        assert stats.pages_extracted >= 1
        assert stats.pages_indexed >= 1
        assert stats.elapsed_seconds >= 0
        runner.close()

    def test_run_empty_results(self, tmp_path):
        """Pipeline run with no crawl results should complete cleanly."""
        runner = PipelineRunner(data_dir=str(tmp_path))
        runner._crawler.crawl = MagicMock(return_value=[])

        stats = runner.run(["https://example.com"])
        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0
        runner.close()

    def test_run_captures_errors(self, tmp_path):
        """Pipeline run should capture and report errors."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        mock_page = CrawledPage(
            url="https://example.com/bad",
            title="Bad Page",
            content="x" * 200,
        )
        runner._crawler.crawl = MagicMock(return_value=[mock_page])

        # Mock index to raise an error
        runner._search_index.add_page = MagicMock(side_effect=ValueError("index error"))

        stats = runner.run(["https://example.com"])
        assert len(stats.errors) > 0
        runner.close()


class TestPipelineStats:
    """Test PipelineStats dataclass."""

    def test_stats_default_values(self):
        """PipelineStats should have sensible defaults."""
        stats = PipelineStats()
        assert stats.pages_crawled == 0
        assert stats.pages_extracted == 0
        assert stats.pages_filtered_in == 0
        assert stats.pages_filtered_out == 0
        assert stats.pages_scored == 0
        assert stats.pages_tagged == 0
        assert stats.pages_indexed == 0
        assert stats.errors == []
        assert stats.elapsed_seconds == 0.0
        assert stats.tags_applied == 0
        assert stats.interests_matched == 0

    def test_stats_summary(self):
        """PipelineStats.summary should return readable text."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=6,
            pages_indexed=6,
            tags_applied=12,
            interests_matched=4,
            elapsed_seconds=5.2,
        )
        summary = stats.summary()
        assert "Pipeline Summary" in summary
        assert "Crawled:      10" in summary
        assert "Indexed:      6" in summary
        assert "Time:         5.2s" in summary


class TestPipelineRunnerFromFile:
    """Test run_from_files method."""

    def test_run_from_files_imports_content(self, tmp_path):
        """run_from_files should import and index local files."""
        # Create a test file
        test_file = tmp_path / "test_article.txt"
        test_file.write_text(
            "This is a test article about programming and software development. "
            "It has enough content to pass the content length filter and "
            "should be properly indexed by the pipeline runner."
        )

        runner = PipelineRunner(data_dir=str(tmp_path))

        # Add interest
        interest = Interest(name="programming", keywords=["programming", "software"])
        runner._interest_store.add(interest)

        stats = runner.run_from_files([str(test_file)])

        assert stats.pages_indexed >= 1
        runner.close()

    def test_run_from_files_missing_file(self, tmp_path):
        """run_from_files should handle missing files gracefully."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        stats = runner.run_from_files(["/nonexistent/file.txt"])

        assert stats.pages_indexed == 0
        assert len(stats.errors) > 0
        runner.close()

    def test_run_from_files_empty_file(self, tmp_path):
        """run_from_files should skip empty files."""
        test_file = tmp_path / "empty.txt"
        test_file.write_text("")

        runner = PipelineRunner(data_dir=str(tmp_path))
        stats = runner.run_from_files([str(test_file)])

        assert stats.pages_indexed == 0
        runner.close()


class TestPipelinePersistence:
    """Test that pipeline data persists correctly."""

    def test_interests_persist_after_run(self, tmp_path):
        """Interests should be saved to disk after pipeline run."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        interest = Interest(name="persistence", keywords=["persist", "save"])
        runner._interest_store.add(interest)

        runner.close()

        # Reload and verify
        store = InterestStore(store_path=os.path.join(tmp_path, "interests.json"))
        interests = store.list_all()
        assert len(interests) == 1
        assert interests[0].name == "persistence"

    def test_tags_persist_after_run(self, tmp_path):
        """Tags should be saved to disk after pipeline run."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        runner._tag_store.add_tag_to_page("https://example.com/page", "test-tag")
        runner.close()

        # Reload and verify
        tag_store = TagStore(store_path=os.path.join(tmp_path, "tags.json"))
        tags = tag_store.get_tags_for_page("https://example.com/page")
        tag_names = [t.name if hasattr(t, "name") else str(t) for t in tags]
        assert "test-tag" in tag_names

    def test_index_persists_after_run(self, tmp_path):
        """Search index should be saved to disk after pipeline run."""
        runner = PipelineRunner(data_dir=str(tmp_path))

        page = CrawledPage(
            url="https://example.com/persist",
            title="Persistent Page",
            content="This page should persist after the runner closes.",
            relevance_score=0.9,
        )
        runner._search_index.add_page(page)
        runner.close()

        # Reload and verify
        index = SearchIndex(db_path=os.path.join(tmp_path, "search_index.json"))
        assert index.get_page_count() == 1
        page = index.get_page("https://example.com/persist")
        assert page is not None
        assert page.title == "Persistent Page"
