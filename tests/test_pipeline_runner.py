"""Tests for personal_index.pipeline_runner — PipelineRunner and PipelineStats."""

from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from personal_index.models import CrawledPage
from personal_index.pipeline_runner import PipelineRunner, PipelineStats


class TestPipelineStats:
    """Tests for PipelineStats dataclass."""

    def test_default_values(self):
        """Test PipelineStats initializes with sensible defaults."""
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
        """Test summary includes all stage counts."""
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=8,
            pages_filtered_in=6,
            pages_filtered_out=2,
            pages_scored=6,
            pages_tagged=5,
            pages_indexed=5,
            errors=["err1"],
            elapsed_seconds=1.5,
            tags_applied=12,
            interests_matched=3,
        )
        summary = stats.summary()
        assert "Pipeline Summary" in summary
        assert "Crawled:      10" in summary
        assert "Extracted:    8" in summary
        assert "Filtered in:  6" in summary
        assert "Filtered out: 2" in summary
        assert "Scored:       6" in summary
        assert "Tagged:       5" in summary
        assert "Tags applied: 12" in summary
        assert "Indexed:      5" in summary
        assert "Errors:       1" in summary
        assert "Time:         1.5s" in summary

    def test_summary_with_zero_counts(self):
        """Test summary with all zeros."""
        stats = PipelineStats()
        summary = stats.summary()
        assert "Crawled:      0" in summary
        assert "Errors:       0" in summary


class TestPipelineRunnerInit:
    """Tests for PipelineRunner initialization."""

    @pytest.fixture
    def tmp_data_dir(self):
        """Provide a temporary data directory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_init_creates_data_dir(self, tmp_data_dir):
        """Test that __init__ creates the data directory and subdirs."""
        data_dir = os.path.join(tmp_data_dir, "new_data")
        runner = PipelineRunner(data_dir=data_dir)
        assert os.path.isdir(data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_init_sets_data_dir(self, tmp_data_dir):
        """Test that data_dir is stored correctly."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner.data_dir == tmp_data_dir

    def test_init_creates_pipeline_config(self, tmp_data_dir):
        """Test that a default PipelineConfig is created when none provided."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        from personal_index.config.pipeline_config import PipelineConfig
        assert isinstance(runner.pipeline_config, PipelineConfig)

    def test_init_with_custom_config(self, tmp_data_dir):
        """Test that a custom PipelineConfig is used when provided."""
        from personal_index.config.pipeline_config import PipelineConfig
        custom_config = PipelineConfig(min_score_threshold=0.5)
        runner = PipelineRunner(data_dir=tmp_data_dir, pipeline_config=custom_config)
        assert runner.pipeline_config.min_score_threshold == 0.5

    def test_init_creates_interest_store(self, tmp_data_dir):
        """Test that InterestStore is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._interest_store is not None

    def test_init_creates_tag_store(self, tmp_data_dir):
        """Test that TagStore is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._tag_store is not None

    def test_init_creates_search_index(self, tmp_data_dir):
        """Test that SearchIndex is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._search_index is not None

    def test_init_creates_filter(self, tmp_data_dir):
        """Test that ContentFilter is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._filter is not None

    def test_init_creates_scorer(self, tmp_data_dir):
        """Test that ContentScorer is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._scorer is not None

    def test_init_creates_crawler(self, tmp_data_dir):
        """Test that Crawler is initialized."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        assert runner._crawler is not None


class TestPipelineRunnerProgressCallback:
    """Tests for progress callback handling."""

    @pytest.fixture
    def tmp_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_emit_progress_with_three_arg_callback(self, tmp_data_dir):
        """Test progress callback with 3 arguments."""
        calls = []

        def callback(stage, count, total):
            calls.append((stage, count, total))

        runner = PipelineRunner(data_dir=tmp_data_dir, progress_callback=callback)
        runner._emit_progress("crawl", 5, 10)
        assert calls == [("crawl", 5, 10)]

    def test_emit_progress_with_two_arg_callback(self, tmp_data_dir):
        """Test progress callback with 2 arguments."""
        calls = []

        def callback(stage, count):
            calls.append((stage, count))

        runner = PipelineRunner(data_dir=tmp_data_dir, progress_callback=callback)
        runner._emit_progress("crawl", 5, 10)
        assert calls == [("crawl", 5)]

    def test_emit_progress_no_callback(self, tmp_data_dir):
        """Test that no error when callback is None."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        runner._emit_progress("crawl", 5, 10)  # Should not raise


class TestPipelineRunnerRun:
    """Tests for PipelineRunner.run() method."""

    @pytest.fixture
    def tmp_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_run_returns_pipeline_stats(self, tmp_data_dir):
        """Test that run() returns a PipelineStats instance."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        with patch.object(runner._crawler, "crawl", return_value=[]):
            stats = runner.run(seed_urls=["http://example.com"])
        assert isinstance(stats, PipelineStats)

    def test_run_tracks_elapsed_time(self, tmp_data_dir):
        """Test that run() records elapsed time."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        with patch.object(runner._crawler, "crawl", return_value=[]):
            stats = runner.run(seed_urls=["http://example.com"])
        assert stats.elapsed_seconds >= 0.0

    def test_run_with_empty_seed_urls(self, tmp_data_dir):
        """Test run with empty seed URLs list."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        with patch.object(runner._crawler, "crawl", return_value=[]):
            stats = runner.run(seed_urls=[])
        assert isinstance(stats, PipelineStats)

    def test_run_records_errors(self, tmp_data_dir):
        """Test that run() records errors from crawler."""
        runner = PipelineRunner(data_dir=tmp_data_dir)

        def mock_crawl(*args, **kwargs):
            raise RuntimeError("network error")

        with patch.object(runner._crawler, "crawl", side_effect=mock_crawl):
            stats = runner.run(seed_urls=["http://example.com"])
        assert len(stats.errors) > 0
        assert "network error" in stats.errors[0]

    def test_run_tracks_crawled_pages(self, tmp_data_dir):
        """Test that run() tracks pages crawled."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        page = CrawledPage(
            url="http://example.com",
            title="Example",
            content="This is example content for testing purposes.",
            status_code=200,
            word_count=8,
            crawled_at=datetime.now(timezone.utc),
        )
        with patch.object(runner._crawler, "crawl", return_value=[page]):
            stats = runner.run(seed_urls=["http://example.com"])
        assert stats.pages_crawled == 1


class TestPipelineRunnerAddPageDirectly:
    """Tests for PipelineRunner.add_page_directly()."""

    @pytest.fixture
    def tmp_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_add_page_directly_returns_true(self, tmp_data_dir):
        """Test adding a valid page directly."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        page = CrawledPage(
            url="http://example.com/page1",
            title="Test Page",
            content="This is some test content that is long enough to pass the filter.",
            status_code=200,
            word_count=12,
            crawled_at=datetime.now(timezone.utc),
        )
        result = runner.add_page_directly(page)
        assert result is True

    def test_add_page_directly_empty_content(self, tmp_data_dir):
        """Test that empty content page is rejected."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        page = CrawledPage(
            url="http://example.com/page1",
            title="Test Page",
            content="",
            status_code=200,
            word_count=0,
            crawled_at=datetime.now(timezone.utc),
        )
        result = runner.add_page_directly(page)
        assert result is False

    def test_add_page_directly_filtered_out(self, tmp_data_dir):
        """Test that filtered-out page is rejected."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        # Very short content that should be filtered
        page = CrawledPage(
            url="http://example.com/page1",
            title="T",
            content="ab",
            status_code=200,
            word_count=1,
            crawled_at=datetime.now(timezone.utc),
        )
        result = runner.add_page_directly(page)
        # Should be filtered out due to min_content_length
        assert result is False


class TestPipelineRunnerClose:
    """Tests for PipelineRunner.close()."""

    @pytest.fixture
    def tmp_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_close_calls_crawler_close(self, tmp_data_dir):
        """Test that close() calls crawler.close()."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        runner._crawler.close = MagicMock()
        runner.close()
        runner._crawler.close.assert_called_once()

    def test_close_calls_search_index_close(self, tmp_data_dir):
        """Test that close() calls search_index.close()."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        runner._search_index.close = MagicMock()
        runner.close()
        runner._search_index.close.assert_called_once()

    def test_close_calls_tag_store_save(self, tmp_data_dir):
        """Test that close() calls tag_store._save()."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        runner._tag_store._save = MagicMock()
        runner.close()
        runner._tag_store._save.assert_called_once()

    def test_close_calls_interest_store_save(self, tmp_data_dir):
        """Test that close() calls interest_store._save()."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        runner._interest_store._save = MagicMock()
        runner.close()
        runner._interest_store._save.assert_called_once()


class TestPipelineRunnerReadFile:
    """Tests for PipelineRunner._read_file()."""

    @pytest.fixture
    def tmp_data_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_read_file_nonexistent(self, tmp_data_dir):
        """Test reading a nonexistent file returns None."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        result = runner._read_file("/nonexistent/file.txt")
        assert result is None

    def test_read_file_plain_text(self, tmp_data_dir):
        """Test reading a plain text file."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        filepath = os.path.join(tmp_data_dir, "test.txt")
        with open(filepath, "w") as f:
            f.write("Hello world this is test content.")
        result = runner._read_file(filepath)
        assert result is not None
        assert result.content == "Hello world this is test content."
        assert result.title == "test.txt"

    def test_read_file_empty_content(self, tmp_data_dir):
        """Test reading a file with only whitespace returns None."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        filepath = os.path.join(tmp_data_dir, "empty.txt")
        with open(filepath, "w") as f:
            f.write("   \n  ")
        result = runner._read_file(filepath)
        assert result is None

    def test_read_file_html(self, tmp_data_dir):
        """Test reading an HTML file."""
        runner = PipelineRunner(data_dir=tmp_data_dir)
        filepath = os.path.join(tmp_data_dir, "test.html")
        with open(filepath, "w") as f:
            f.write("<html><head><title>Test</title></head><body>Hello</body></html>")
        result = runner._read_file(filepath)
        assert result is not None
        assert result.url == filepath
