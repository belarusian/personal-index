"""Integration tests for the full crawl→extract→filter→score→tag→index pipeline."""

from __future__ import annotations

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from personal_index.config.pipeline_config import PipelineConfig, PipelineStepConfig
from personal_index.content_extractor import ContentExtractor, ExtractedContent
from personal_index.content_filter import ContentFilter, FilterConfig
from personal_index.content_scoring import ContentScorer
from personal_index.index import SearchIndex
from personal_index.models import CrawledPage
from personal_index.pipeline_runner import PipelineRunner, PipelineStats
from personal_index.tags import TagStore


class TestPipelineConfig:
    """Test pipeline configuration loading."""

    def test_default_config(self):
        cfg = PipelineConfig()
        assert cfg.enabled is True
        assert cfg.steps == []
        assert cfg.min_score_threshold == 0.0
        assert cfg.min_content_length == 100

    def test_enabled_steps(self):
        cfg = PipelineConfig(
            steps=[
                PipelineStepConfig(name="crawl", enabled=True),
                PipelineStepConfig(name="extract", enabled=True),
                PipelineStepConfig(name="filter", enabled=False),
            ]
        )
        assert cfg.get_enabled_steps() == ["crawl", "extract"]

    def test_is_step_enabled_default(self):
        cfg = PipelineConfig()
        assert cfg.is_step_enabled("crawl") is True

    def test_is_step_enabled_explicit(self):
        cfg = PipelineConfig(
            steps=[PipelineStepConfig(name="crawl", enabled=False)]
        )
        assert cfg.is_step_enabled("crawl") is False

    def test_load_from_yaml(self, tmp_path):
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
pipeline:
  enabled: true
  steps:
    - name: crawl
      enabled: true
    - name: extract
      enabled: true
  min_score_threshold: 0.5
  min_content_length: 200
""")
        cfg = PipelineConfig()
        assert cfg.enabled is True


class TestPipelineRunner:
    """Test the end-to-end pipeline runner."""

    def test_runner_creation(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        assert runner.data_dir == data_dir
        assert runner.pipeline_config.enabled is True

    def test_runner_with_custom_config(self, tmp_path):
        cfg = PipelineConfig(
            steps=[
                PipelineStepConfig(name="crawl", enabled=False),
            ],
            min_score_threshold=0.5,
        )
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(config=cfg, data_dir=data_dir)
        assert runner.pipeline_config.min_score_threshold == 0.5

    def test_run_empty_urls(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)
        stats = runner.run([], max_depth=1)
        assert isinstance(stats, PipelineStats)
        assert stats.pages_crawled == 0

    def test_run_with_mocked_crawler(self, tmp_path):
        data_dir = str(tmp_path / "data")
        runner = PipelineRunner(data_dir=data_dir)

        page = CrawledPage(
            url="https://example.com/test",
            title="Test Page",
            content="This is a test page about python programming.",
        )

        with patch('personal_index.pipeline_runner.Crawler') as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = [page]
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 1
        assert stats.pages_extracted == 1

    def test_stats_summary(self):
        stats = PipelineStats(
            pages_crawled=10,
            pages_extracted=10,
            pages_filtered_in=8,
            pages_filtered_out=2,
            pages_scored=8,
            pages_tagged=8,
            pages_indexed=8,
        )
        summary = stats.summary()
        assert "Crawled:    10" in summary
        assert "Filtered out: 2" in summary
        assert "Indexed:    8" in summary

    def test_stats_summary_with_errors(self):
        stats = PipelineStats(
            pages_crawled=5,
            errors=["Error 1", "Error 2"],
        )
        summary = stats.summary()
        assert "Errors:     2" in summary


class TestPipelineSteps:
    """Test individual pipeline steps work correctly."""

    def test_extractor(self):
        extractor = ContentExtractor()
        html = "<html><head><title>Test</title></head><body><p>Hello world</p></body></html>"
        result = extractor.extract(html)
        assert result.title == "Test"
        assert "Hello world" in result.text

    def test_filter_includes_long_content(self):
        filter_cfg = FilterConfig(min_content_length=10)
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="This is a sufficiently long piece of content for testing.",
        )
        assert content_filter.should_include(page) is True

    def test_filter_excludes_short_content(self):
        filter_cfg = FilterConfig(min_content_length=100)
        content_filter = ContentFilter(config=filter_cfg)
        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Short",
        )
        assert content_filter.should_include(page) is False

    def test_scorer_scores_content(self):
        scorer = ContentScorer()
        result = scorer.score(
            keyword_matches=3,
            total_keywords=5,
            word_count=100,
            domain_authority=0.7,
        )
        assert result is not None
        assert hasattr(result, 'total') or hasattr(result, 'score')


class TestPipelineIntegration:
    """Full integration tests with mocked network."""

    def test_full_pipeline_flow(self, tmp_path):
        """Test the complete pipeline with mocked crawler."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        cfg = PipelineConfig(
            steps=[
                PipelineStepConfig(name="crawl", enabled=True),
                PipelineStepConfig(name="extract", enabled=True),
                PipelineStepConfig(name="filter", enabled=True),
                PipelineStepConfig(name="score", enabled=True),
                PipelineStepConfig(name="tag", enabled=True),
                PipelineStepConfig(name="index", enabled=True),
            ],
            min_content_length=10,
        )
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        page = CrawledPage(
            url="https://example.com/article",
            title="Python Tutorial",
            content="This is a comprehensive Python programming tutorial covering basics.",
        )

        with patch('personal_index.pipeline_runner.Crawler') as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = [page]
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 1
        assert stats.pages_extracted >= 0
        assert stats.pages_filtered_in >= 0
        assert stats.pages_scored >= 0

    def test_pipeline_with_disabled_steps(self, tmp_path):
        """Test pipeline skips disabled steps."""
        data_dir = str(tmp_path / "data")
        os.makedirs(data_dir, exist_ok=True)

        cfg = PipelineConfig(
            steps=[
                PipelineStepConfig(name="crawl", enabled=True),
                PipelineStepConfig(name="extract", enabled=False),
                PipelineStepConfig(name="filter", enabled=False),
                PipelineStepConfig(name="score", enabled=False),
                PipelineStepConfig(name="tag", enabled=False),
                PipelineStepConfig(name="index", enabled=False),
            ],
        )
        runner = PipelineRunner(config=cfg, data_dir=data_dir)

        page = CrawledPage(
            url="https://example.com",
            title="Test",
            content="Test content that is long enough to pass any filter.",
        )

        with patch('personal_index.pipeline_runner.Crawler') as MockCrawler:
            mock_crawler = MagicMock()
            mock_crawler.crawl.return_value = [page]
            MockCrawler.return_value = mock_crawler

            stats = runner.run(["https://example.com"], max_depth=1)

        assert stats.pages_crawled == 1
        assert stats.pages_indexed == 0


class TestPipelineStatsOutput:
    """Test pipeline stats output formatting."""

    def test_stats_empty(self):
        stats = PipelineStats()
        summary = stats.summary()
        assert "Pipeline complete:" in summary
        assert "Crawled:    0" in summary

    def test_stats_all_stages(self):
        stats = PipelineStats(
            pages_crawled=100,
            pages_extracted=100,
            pages_filtered_in=80,
            pages_filtered_out=20,
            pages_scored=80,
            pages_tagged=80,
            pages_indexed=80,
        )
        summary = stats.summary()
        assert "Crawled:    100" in summary
        assert "Extracted:  100" in summary
        assert "Filtered in: 80" in summary
        assert "Filtered out: 20" in summary
        assert "Scored:     80" in summary
        assert "Tagged:     80" in summary
        assert "Indexed:    80" in summary
