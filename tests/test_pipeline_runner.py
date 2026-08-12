"""Tests for pipeline_runner.py — PipelineRunner class."""

from __future__ import annotations

import os
from unittest.mock import MagicMock

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.models import CrawledPage
from personal_index.pipeline_runner import PipelineRunner, PipelineStats


class TestPipelineStats:
    """Tests for PipelineStats dataclass."""

    def test_default_stats(self):
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

    def test_summary_contains_counts(self):
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=6,
            pages_indexed=6,
            tags_applied=12,
            interests_matched=3,
            errors=["some error"],
            elapsed_seconds=5.5,
        )
        summary = stats.summary()
        assert "Pipeline Summary" in summary
        assert "Crawled:      10" in summary
        assert "Extracted:    8" in summary
        assert "Filtered in:  6" in summary
        assert "Filtered out: 2" in summary
        assert "Scored:       6" in summary
        assert "Tagged:       6" in summary
        assert "Tags applied: 12" in summary
        assert "Indexed:      6" in summary
        assert "Errors:       1" in summary
        assert "Time:         5.5s" in summary


class TestPipelineRunnerInit:
    """Tests for PipelineRunner initialization."""

    def test_creates_data_dir(self, tmp_path):
        data_dir = str(tmp_path / "new_data")
        runner = PipelineRunner(data_dir=data_dir)
        assert os.path.isdir(data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))
        runner.close()

    def test_uses_default_data_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(str(tmp_path))
        runner = PipelineRunner()
        assert os.path.isdir(".personal_index")
        runner.close()


class TestPipelineRunnerAddPageDirectly:
    """Tests for add_page_directly method."""

    def test_adds_valid_page(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        page = CrawledPage(
            url="http://example.com/test",
            title="Test Page",
            content="This is a test page with some meaningful content.",
        )
        result = runner.add_page_directly(page)
        assert result is True
        assert runner._search_index.get_page_count() == 1
        runner.close()

    def test_rejects_empty_content(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        page = CrawledPage(
            url="http://example.com/empty",
            title="Empty Page",
            content="",
        )
        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_filters_short_content(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=100)
        runner = PipelineRunner(data_dir=data_dir, pipeline_config=config)

        page = CrawledPage(
            url="http://example.com/short",
            title="Short",
            content="too short",
        )
        result = runner.add_page_directly(page)
        assert result is False
        runner.close()

    def test_scores_and_tags_with_interests(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        # Add an interest first
        from personal_index.models import Interest
        runner._interest_store.add(Interest(name="python", keywords=["python", "coding"]))

        page = CrawledPage(
            url="http://example.com/python",
            title="Python Guide",
            content="Python is great for coding and programming.",
        )
        result = runner.add_page_directly(page)
        assert result is True
        # Page should have been tagged
        tags = runner._tag_store.get_tags_for_page("http://example.com/python")
        tag_names = [t.name for t in tags]
        assert "python" in tag_names
        runner.close()


class TestPipelineRunnerRun:
    """Tests for the run method with mocked crawler."""

    def test_run_with_mocked_crawler(self, tmp_path):
        """Test that run() processes pages through all stages when crawler returns pages."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        # Add an interest so pages get scored
        from personal_index.models import Interest
        runner._interest_store.add(Interest(name="test", keywords=["test", "example"]))

        # Mock the crawler to return controlled pages
        mock_crawler = MagicMock()
        mock_pages = [
            CrawledPage(
                url="http://example.com/page1",
                title="Test Page 1",
                content="This is a test page with example content.",
                status_code=200,
            ),
            CrawledPage(
                url="http://example.com/page2",
                title="Test Page 2",
                content="Another test page with more example content here.",
                status_code=200,
            ),
        ]
        mock_crawler.crawl.return_value = mock_pages
        runner._crawler = mock_crawler

        stats = runner.run(seed_urls=["http://example.com"])

        # Verify stats
        assert stats.pages_crawled == 2
        assert stats.pages_extracted == 2
        assert stats.pages_filtered_in >= 0
        assert stats.pages_scored >= 0
        assert stats.pages_indexed >= 0
        assert stats.elapsed_seconds >= 0

        # Verify crawler was called
        mock_crawler.crawl.assert_called_once()

        runner.close()

    def test_run_with_empty_crawler_results(self, tmp_path):
        """Test run() when crawler returns no pages."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        mock_crawler = MagicMock()
        mock_crawler.crawl.return_value = []
        runner._crawler = mock_crawler

        stats = runner.run(seed_urls=["http://example.com"])

        assert stats.pages_crawled == 0
        assert stats.pages_indexed == 0
        runner.close()

    def test_run_with_progress_callback(self, tmp_path):
        """Test that progress callback is invoked during run."""
        data_dir = str(tmp_path / "data")
        progress_calls = []

        def progress(stage, count, total=0):
            progress_calls.append((stage, count, total))

        runner = PipelineRunner(data_dir=data_dir, progress_callback=progress)

        mock_crawler = MagicMock()
        mock_pages = [
            CrawledPage(
                url="http://example.com/page1",
                title="Test Page",
                content="Some test content here for the pipeline.",
                status_code=200,
            ),
        ]
        mock_crawler.crawl.return_value = mock_pages
        runner._crawler = mock_crawler

        stats = runner.run(seed_urls=["http://example.com"])

        assert stats.pages_crawled == 1
        assert len(progress_calls) > 0
        runner.close()

    def test_run_captures_errors(self, tmp_path):
        """Test that run() captures errors gracefully."""
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        mock_crawler = MagicMock()
        mock_pages = [
            CrawledPage(
                url="http://example.com/page1",
                title="Test Page",
                content="Some test content here.",
                status_code=200,
            ),
        ]
        mock_crawler.crawl.return_value = mock_pages
        runner._crawler = mock_crawler

        # Mock search index to raise an error
        def failing_add(page):
            raise OSError("disk full")
        runner._search_index.add_page = failing_add

        stats = runner.run(seed_urls=["http://example.com"])

        assert len(stats.errors) > 0
        runner.close()


class TestPipelineRunnerClose:
    """Tests for close method."""

    def test_close_calls_resources(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        runner._crawler.close = MagicMock()
        runner._search_index.close = MagicMock()

        runner.close()

        runner._crawler.close.assert_called_once()
        runner._search_index.close.assert_called_once()
