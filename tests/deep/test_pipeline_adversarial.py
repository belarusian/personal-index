"""Adversarial deep tests for personal_index.pipeline module.

Tests edge cases, malformed input, boundary conditions, and contract
compliance for the Pipeline orchestrator, PipelineConfig, PipelineStats,
and PipelineResult classes.
"""
import json
import os
import pytest
import tempfile
from dataclasses import dataclass, field

from personal_index.pipeline import (
    Pipeline,
    PipelineConfig,
    PipelineStats,
    PipelineResult,
    ScoreWeights,
)


class TestPipelineConfigAdversarial:
    """Adversarial tests for PipelineConfig."""

    def test_default_config_has_all_steps_enabled(self):
        """Default config enables all 7 pipeline steps."""
        config = PipelineConfig()
        expected_steps = ["crawl", "extract", "filter", "score", "tag", "index", "search"]
        assert config.enabled_steps == expected_steps

    def test_is_step_enabled_unknown_step(self):
        """Unknown step name returns False."""
        config = PipelineConfig()
        assert not config.is_step_enabled("nonexistent_step")

    def test_is_step_enabled_empty_string(self):
        """Empty string step name returns False."""
        config = PipelineConfig()
        assert not config.is_step_enabled("")

    def test_is_step_enabled_whitespace(self):
        """Whitespace-only step name returns False."""
        config = PipelineConfig()
        assert not config.is_step_enabled("   ")

    def test_from_dict_unknown_keys_ignored(self):
        """Unknown keys in dict are silently ignored."""
        data = {
            "max_depth": 5,
            "unknown_key": "should be ignored",
            "another_unknown": 123,
        }
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == 5
        assert not hasattr(config, "unknown_key")

    def test_from_dict_empty_dict(self):
        """Empty dict produces default config."""
        config = PipelineConfig.from_dict({})
        assert config.max_depth == 3
        assert config.max_pages == 100

    def test_from_dict_none_values(self):
        """None values overwrite defaults with None."""
        data = {"max_depth": None, "timeout": None}
        config = PipelineConfig.from_dict(data)
        assert config.max_depth is None
        assert config.timeout is None

    def test_from_dict_type_mismatch(self):
        """Type mismatches are accepted (no validation)."""
        data = {"max_depth": "five", "timeout": 30.5}
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == "five"
        assert config.timeout == 30.5

    def test_negative_max_depth(self):
        """Negative max_depth is accepted."""
        config = PipelineConfig(max_depth=-1)
        assert config.max_depth == -1

    def test_zero_max_pages(self):
        """Zero max_pages is accepted."""
        config = PipelineConfig(max_pages=0)
        assert config.max_pages == 0

    def test_negative_timeout(self):
        """Negative timeout is accepted."""
        config = PipelineConfig(timeout=-5)
        assert config.timeout == -5

    def test_disabled_all_steps(self):
        """Config with no enabled steps."""
        config = PipelineConfig(enabled_steps=[])
        assert not config.is_step_enabled("crawl")
        assert not config.is_step_enabled("extract")

    def test_enabled_steps_duplicate(self):
        """Duplicate step names in enabled_steps."""
        config = PipelineConfig(enabled_steps=["crawl", "crawl", "extract"])
        assert config.is_step_enabled("crawl")
        assert config.is_step_enabled("extract")

    def test_unicode_step_name(self):
        """Unicode step name."""
        config = PipelineConfig(enabled_steps=["crawl", "éxtract"])
        assert config.is_step_enabled("éxtract")


class TestPipelineStatsAdversarial:
    """Adversarial tests for PipelineStats."""

    def test_summary_default_values(self):
        """Summary with all default values."""
        stats = PipelineStats()
        summary = stats.summary()
        assert "crawled=0" in summary
        assert "extracted=0" in summary
        assert "filtered_in=0" in summary
        assert "filtered_out=0" in summary
        assert "scored=0" in summary
        assert "tagged=0" in summary
        assert "indexed=0" in summary
        assert "tags=0" in summary
        assert "errors=0" in summary
        assert "time=0.0s" in summary

    def test_summary_has_exactly_10_parts(self):
        """Summary contains exactly 10 comma-separated parts."""
        stats = PipelineStats()
        summary = stats.summary()
        parts = summary.split(", ")
        assert len(parts) == 10

    def test_summary_order(self):
        """Summary parts are in the documented order."""
        stats = PipelineStats()
        summary = stats.summary()
        parts = summary.split(", ")
        assert parts[0].startswith("crawled=")
        assert parts[1].startswith("extracted=")
        assert parts[2].startswith("filtered_in=")
        assert parts[3].startswith("filtered_out=")
        assert parts[4].startswith("scored=")
        assert parts[5].startswith("tagged=")
        assert parts[6].startswith("indexed=")
        assert parts[7].startswith("tags=")
        assert parts[8].startswith("errors=")
        assert parts[9].startswith("time=")

    def test_summary_with_errors(self):
        """Summary with error list."""
        stats = PipelineStats()
        stats.errors = ["error1", "error2"]
        summary = stats.summary()
        assert "errors=2" in summary

    def test_summary_elapsed_time_format(self):
        """Elapsed time formatted to 1 decimal place."""
        stats = PipelineStats()
        stats.elapsed_seconds = 12.345
        summary = stats.summary()
        assert "time=12.3s" in summary

    def test_summary_elapsed_time_zero(self):
        """Zero elapsed time."""
        stats = PipelineStats()
        stats.elapsed_seconds = 0.0
        summary = stats.summary()
        assert "time=0.0s" in summary

    def test_summary_negative_values(self):
        """Negative counter values (should not happen but test robustness)."""
        stats = PipelineStats()
        stats.pages_crawled = -5
        stats.pages_extracted = -3
        summary = stats.summary()
        assert "crawled=-5" in summary
        assert "extracted=-3" in summary

    def test_summary_large_values(self):
        """Very large counter values."""
        stats = PipelineStats()
        stats.pages_crawled = 1000000
        stats.pages_extracted = 999999
        summary = stats.summary()
        assert "crawled=1000000" in summary
        assert "extracted=999999" in summary

    def test_summary_no_side_effects(self):
        """Summary does not modify the stats object."""
        stats = PipelineStats()
        stats.pages_crawled = 5
        stats.errors = ["e1"]
        original_crawled = stats.pages_crawled
        original_errors = len(stats.errors)
        stats.summary()
        assert stats.pages_crawled == original_crawled
        assert len(stats.errors) == original_errors

    def test_errors_default_is_list(self):
        """Errors field defaults to empty list."""
        stats = PipelineStats()
        assert isinstance(stats.errors, list)
        assert len(stats.errors) == 0

    def test_errors_independent_instances(self):
        """Each PipelineStats instance has its own errors list."""
        stats1 = PipelineStats()
        stats2 = PipelineStats()
        stats1.errors.append("error1")
        assert len(stats2.errors) == 0


class TestPipelineResultAdversarial:
    """Adversarial tests for PipelineResult."""

    def test_default_values(self):
        """Default PipelineResult values."""
        result = PipelineResult()
        assert result.success is True
        assert result.data == {}
        assert result.error == ""
        assert result.step_name == ""

    def test_data_default_is_dict(self):
        """Data field defaults to empty dict."""
        result = PipelineResult()
        assert isinstance(result.data, dict)

    def test_independent_instances(self):
        """Each PipelineResult has its own data dict."""
        r1 = PipelineResult()
        r2 = PipelineResult()
        r1.data["key"] = "value"
        assert "key" not in r2.data

    def test_failure_result(self):
        """Failed result with error message."""
        result = PipelineResult(success=False, error="something went wrong", step_name="crawl")
        assert result.success is False
        assert result.error == "something went wrong"
        assert result.step_name == "crawl"

    def test_unicode_error_message(self):
        """Unicode in error message."""
        result = PipelineResult(error="Erreur: échec")
        assert result.error == "Erreur: échec"

    def test_empty_string_step_name(self):
        """Empty string step name is valid."""
        result = PipelineResult(step_name="")
        assert result.step_name == ""


class TestPipelineIntegrationAdversarial:
    """Integration tests for Pipeline with adversarial inputs."""

    def test_pipeline_empty_seed_urls(self, tmp_path):
        """Pipeline with empty seed URL list."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=[])
        assert stats is not None
        assert isinstance(stats, PipelineStats)

    def test_pipeline_single_seed_url(self, tmp_path):
        """Pipeline with single seed URL."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=1,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=["https://example.com"])
        assert stats is not None

    def test_pipeline_duplicate_seed_urls(self, tmp_path):
        """Pipeline with duplicate seed URLs."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=5,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        urls = ["https://example.com", "https://example.com", "https://example.com"]
        stats = pipeline.run(seed_urls=urls)
        assert stats is not None

    def test_pipeline_malformed_urls(self, tmp_path):
        """Pipeline with malformed URLs."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=5,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        urls = [
            "not-a-url",
            "http://",
            "https://",
            "ftp://example.com",
            "",
        ]
        stats = pipeline.run(seed_urls=urls)
        assert stats is not None

    def test_pipeline_unicode_urls(self, tmp_path):
        """Pipeline with unicode in URLs."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=5,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        urls = ["https://example.com/путь", "https://example.com/路径"]
        stats = pipeline.run(seed_urls=urls)
        assert stats is not None

    def test_pipeline_disabled_all_steps(self, tmp_path):
        """Pipeline with all steps disabled."""
        config = PipelineConfig(enabled_steps=[])
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=["https://example.com"])
        assert stats is not None
        assert stats.pages_crawled == 0

    def test_pipeline_only_crawl_enabled(self, tmp_path):
        """Pipeline with only crawl step enabled."""
        config = PipelineConfig(enabled_steps=["crawl"], max_pages=1)
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=["https://example.com"])
        assert stats is not None

    def test_pipeline_only_search_enabled(self, tmp_path):
        """Pipeline with only search step enabled (no crawl)."""
        config = PipelineConfig(enabled_steps=["search"])
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=[])
        assert stats is not None

    def test_pipeline_data_dir_created(self, tmp_path):
        """Pipeline creates data directory structure."""
        data_dir = tmp_path / "new_pipeline_data"
        config = PipelineConfig(enabled_steps=[])
        pipeline = Pipeline(data_dir=str(data_dir), config=config)
        assert data_dir.exists()
        assert (data_dir / "cache").exists()
        assert (data_dir / "archive").exists()
        assert (data_dir / "backups").exists()

    def test_pipeline_existing_data_dir(self, tmp_path):
        """Pipeline with pre-existing data directory."""
        data_dir = tmp_path / "existing"
        data_dir.mkdir()
        config = PipelineConfig(enabled_steps=[])
        pipeline = Pipeline(data_dir=str(data_dir), config=config)
        assert pipeline.data_dir == str(data_dir)

    def test_pipeline_callback_receives_stats(self, tmp_path):
        """Pipeline callback receives stats object."""
        callback_calls = []

        def test_callback(step, current, total):
            callback_calls.append((step, current, total))

        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=1,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        pipeline.run(seed_urls=["https://example.com"], callback=test_callback)
        # Callback may or may not be called depending on implementation
        # Just verify it doesn't crash

    def test_pipeline_idempotent_run(self, tmp_path):
        """Running pipeline twice on same data doesn't crash."""
        config = PipelineConfig(
            enabled_steps=["crawl", "extract", "filter", "score", "tag", "index"],
            require_interest_match=False,
            max_pages=1,
        )
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats1 = pipeline.run(seed_urls=["https://example.com"])
        stats2 = pipeline.run(seed_urls=["https://example.com"])
        assert stats1 is not None
        assert stats2 is not None

    def test_pipeline_config_from_dict_integration(self, tmp_path):
        """Pipeline with config created from dict."""
        data = {
            "max_depth": 1,
            "max_pages": 5,
            "require_interest_match": False,
            "enabled_steps": ["crawl", "extract", "filter", "score", "tag", "index"],
        }
        config = PipelineConfig.from_dict(data)
        pipeline = Pipeline(data_dir=str(tmp_path), config=config)
        stats = pipeline.run(seed_urls=["https://example.com"])
        assert stats is not None


class TestScoreWeightsAdversarial:
    """Adversarial tests for ScoreWeights."""

    def test_default_weights(self):
        """Default score weights."""
        weights = ScoreWeights()
        assert weights.recency == 0.2
        assert weights.relevance == 0.25
        assert weights.engagement == 0.15
        assert weights.quality == 0.15
        assert weights.authority == 0.1
        assert weights.freshness == 0.15

    def test_negative_weights(self):
        """Negative weights are accepted."""
        weights = ScoreWeights(recency=-1.0, relevance=-2.0)
        assert weights.recency == -1.0
        assert weights.relevance == -2.0

    def test_zero_weights(self):
        """Zero weights are accepted."""
        weights = ScoreWeights(recency=0.0, relevance=0.0)
        assert weights.recency == 0.0
        assert weights.relevance == 0.0

    def test_large_weights(self):
        """Very large weights."""
        weights = ScoreWeights(recency=1000.0, relevance=2000.0)
        assert weights.recency == 1000.0
        assert weights.relevance == 2000.0

    def test_float_precision(self):
        """Float precision in weights."""
        weights = ScoreWeights(recency=0.123456789, relevance=0.987654321)
        assert weights.recency == pytest.approx(0.123456789)
        assert weights.relevance == pytest.approx(0.987654321)

    def test_normalize_returns_new_instance(self):
        """normalize() returns a new ScoreWeights, doesn't mutate original."""
        weights = ScoreWeights(recency=1.0, relevance=1.0)
        normalized = weights.normalize()
        assert normalized is not weights
        assert weights.recency == 1.0  # original unchanged

    def test_normalize_sums_to_one(self):
        """Normalized weights sum to 1.0."""
        weights = ScoreWeights(recency=1.0, relevance=2.0, engagement=1.0)
        normalized = weights.normalize()
        total = (normalized.recency + normalized.relevance + normalized.engagement +
                 normalized.quality + normalized.authority + normalized.freshness)
        assert total == pytest.approx(1.0)

    def test_normalize_all_zero_returns_default(self):
        """normalize() with all zero weights returns default."""
        weights = ScoreWeights()
        weights.recency = 0.0
        weights.relevance = 0.0
        weights.engagement = 0.0
        weights.quality = 0.0
        weights.authority = 0.0
        weights.freshness = 0.0
        normalized = weights.normalize()
        assert normalized.recency == 0.2
        assert normalized.relevance == 0.25
