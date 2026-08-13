"""Tests for personal_index.pipeline module.

Covers:
- PipelineConfig.is_step_enabled(), from_dict()
- PipelineResult
- PipelineStep.execute()
- ContentPipeline.add_step(), step_count, enabled_steps, run()
- Pipeline.run(), search(), add_page_directly(), get_stats()
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from personal_index.pipeline import (
    ContentPipeline,
    Pipeline,
    PipelineConfig,
    PipelineResult,
    PipelineStep,
)

# ---------------------------------------------------------------------------
# PipelineConfig tests
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    """Tests for PipelineConfig dataclass."""

    def test_default_config(self):
        config = PipelineConfig()
        assert config.max_depth == 3
        assert config.max_pages == 100
        assert config.timeout == 30
        assert config.min_content_length == 100
        assert config.auto_tag is True
        assert config.persist_index is True

    def test_is_step_enabled_default(self):
        config = PipelineConfig()
        assert config.is_step_enabled("crawl") is True
        assert config.is_step_enabled("extract") is True
        assert config.is_step_enabled("filter") is True
        assert config.is_step_enabled("score") is True
        assert config.is_step_enabled("tag") is True
        assert config.is_step_enabled("index") is True
        assert config.is_step_enabled("search") is True

    def test_is_step_enabled_disabled(self):
        config = PipelineConfig(enabled_steps=["crawl"])
        assert config.is_step_enabled("crawl") is True
        assert config.is_step_enabled("extract") is False

    def test_from_dict(self):
        data = {
            "max_depth": 5,
            "max_pages": 200,
            "min_content_length": 50,
            "auto_tag": False,
        }
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == 5
        assert config.max_pages == 200
        assert config.min_content_length == 50
        assert config.auto_tag is False

    def test_from_dict_ignores_unknown_keys(self):
        data = {"max_depth": 5, "unknown_key": "value"}
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == 5
        assert not hasattr(config, "unknown_key")

    def test_from_dict_partial(self):
        data = {"max_depth": 10}
        config = PipelineConfig.from_dict(data)
        assert config.max_depth == 10
        assert config.max_pages == 100  # default


# ---------------------------------------------------------------------------
# PipelineResult tests
# ---------------------------------------------------------------------------


class TestPipelineResult:
    """Tests for PipelineResult dataclass."""

    def test_default_result(self):
        result = PipelineResult()
        assert result.success is True
        assert result.data == {}
        assert result.error == ""
        assert result.step_name == ""

    def test_success_result(self):
        result = PipelineResult(success=True, data={"key": "value"}, step_name="extract")
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.step_name == "extract"

    def test_error_result(self):
        result = PipelineResult(success=False, error="Something failed", step_name="crawl")
        assert result.success is False
        assert result.error == "Something failed"
        assert result.step_name == "crawl"


# ---------------------------------------------------------------------------
# PipelineStep tests
# ---------------------------------------------------------------------------


class TestPipelineStep:
    """Tests for PipelineStep."""

    def test_execute_normal(self):
        def handler(data):
            data["processed"] = True
            return data
        step = PipelineStep(name="test", handler=handler)
        result = step.execute({})
        assert result["processed"] is True

    def test_execute_disabled(self):
        step = PipelineStep(name="test", handler=lambda d: {**d, "x": 1}, enabled=False)
        result = step.execute({"key": "value"})
        assert result == {"key": "value"}

    def test_execute_on_error_raise(self):
        def failing(data):
            raise ValueError("fail")
        step = PipelineStep(name="test", handler=failing, on_error="raise")
        with pytest.raises(ValueError):
            step.execute({})

    def test_execute_on_error_continue(self):
        def failing(data):
            raise ValueError("fail")
        step = PipelineStep(name="test", handler=failing, on_error="continue")
        result = step.execute({"key": "value"})
        assert result == {"key": "value"}

    def test_execute_on_error_skip(self):
        def failing(data):
            raise ValueError("fail")
        step = PipelineStep(name="test", handler=failing, on_error="skip")
        result = step.execute({"key": "value"})
        assert result == {"key": "value"}

    def test_step_attributes(self):
        step = PipelineStep(name="my_step", handler=lambda d: d, enabled=True, on_error="continue")
        assert step.name == "my_step"
        assert step.enabled is True
        assert step.on_error == "continue"


# ---------------------------------------------------------------------------
# ContentPipeline tests
# ---------------------------------------------------------------------------


class TestContentPipeline:
    """Tests for ContentPipeline."""

    def test_add_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("step1", lambda d: d)
        assert pipeline.step_count == 1

    def test_add_multiple_steps(self):
        pipeline = ContentPipeline()
        pipeline.add_step("step1", lambda d: d)
        pipeline.add_step("step2", lambda d: d)
        assert pipeline.step_count == 2

    def test_step_count(self):
        pipeline = ContentPipeline()
        assert pipeline.step_count == 0
        pipeline.add_step("a", lambda d: d)
        assert pipeline.step_count == 1

    def test_enabled_steps(self):
        pipeline = ContentPipeline()
        pipeline.add_step("a", lambda d: d)
        pipeline.add_step("b", lambda d: d)
        assert pipeline.enabled_steps == ["a", "b"]

    def test_run_empty_pipeline(self):
        pipeline = ContentPipeline()
        result = pipeline.run({"key": "value"})
        assert result == {"key": "value"}

    def test_run_single_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("upper", lambda d: {**d, "text": d.get("text", "").upper()})
        result = pipeline.run({"text": "hello"})
        assert result["text"] == "HELLO"

    def test_run_multiple_steps_chaining(self):
        pipeline = ContentPipeline()
        pipeline.add_step("add_a", lambda d: {**d, "a": 1})
        pipeline.add_step("add_b", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result == {"a": 1, "b": 2}

    def test_run_error_continue(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError()), on_error="continue")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result["a"] == 1
        assert result["b"] == 2

    def test_run_error_skip(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError()), on_error="skip")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result["a"] == 1
        assert result["b"] == 2

    def test_run_error_stop(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError()), on_error="stop")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        with pytest.raises(ValueError):
            pipeline.run({})

    def test_pipeline_name(self):
        pipeline = ContentPipeline(name="custom")
        assert pipeline.name == "custom"

    def test_pipeline_default_name(self):
        pipeline = ContentPipeline()
        assert pipeline.name == "default"


# ---------------------------------------------------------------------------
# Pipeline tests (full orchestrator)
# ---------------------------------------------------------------------------


class TestPipeline:
    """Tests for the full Pipeline orchestrator with mocked dependencies."""

    @pytest.fixture
    def mock_pipeline(self, tmp_path):
        """Create a Pipeline with all external dependencies mocked."""
        data_dir = str(tmp_path / "test_data")

        with patch("personal_index.pipeline.ContentExtractor") as MockExtractor, \
             patch("personal_index.pipeline.ContentFilter") as MockFilter, \
             patch("personal_index.pipeline.FilterConfig") as MockFilterConfig, \
             patch("personal_index.pipeline.ContentScorer") as MockScorer, \
             patch("personal_index.pipeline.ScoreWeights") as MockScoreWeights, \
             patch("personal_index.pipeline.SearchIndex") as MockSearchIndex, \
             patch("personal_index.pipeline.InterestStore") as MockInterestStore, \
             patch("personal_index.pipeline.TagStore") as MockTagStore, \
             patch("personal_index.pipeline.HTMLScraper") as MockScraper, \
             patch("personal_index.pipeline.os.makedirs"), \
             patch("personal_index.pipeline.os.path.join", side_effect=lambda *a: "/".join(a)):

            # Setup mocks
            mock_extractor = MagicMock()
            MockExtractor.return_value = mock_extractor

            mock_filter = MagicMock()
            MockFilter.return_value = mock_filter

            mock_filter_config = MagicMock()
            MockFilterConfig.return_value = mock_filter_config

            mock_scorer = MagicMock()
            MockScorer.return_value = mock_scorer

            mock_score_weights = MagicMock()
            MockScoreWeights.return_value = mock_score_weights

            mock_search_index = MagicMock()
            MockSearchIndex.return_value = mock_search_index

            mock_interest_store = MagicMock()
            MockInterestStore.return_value = mock_interest_store

            mock_tag_store = MagicMock()
            MockTagStore.return_value = mock_tag_store

            mock_scraper = MagicMock()
            MockScraper.return_value = mock_scraper

            config = PipelineConfig()
            pipeline = Pipeline(data_dir=data_dir, config=config)

            return pipeline, {
                "extractor": mock_extractor,
                "content_filter": mock_filter,
                "scorer": mock_scorer,
                "search_index": mock_search_index,
                "interest_store": mock_interest_store,
                "tag_store": mock_tag_store,
                "scraper": mock_scraper,
            }

    def test_pipeline_init(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        assert pipeline.data_dir is not None
        assert pipeline.config is not None

    def test_pipeline_search(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        mock_result = MagicMock()
        mock_result.url = "https://example.com"
        mock_result.title = "Test"
        with patch.object(pipeline.search_index, 'search', return_value=[mock_result]):
            results = pipeline.search("test query", limit=10)
        assert len(results) == 1

    def test_pipeline_search_with_tag(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        mock_result1 = MagicMock()
        mock_result1.url = "https://example.com"
        mock_result1.title = "Test"
        mock_result2 = MagicMock()
        mock_result2.url = "https://other.com"
        mock_result2.title = "Other"
        with patch.object(pipeline.tag_store, 'get_pages_for_tag', return_value={"https://example.com"}), \
             patch.object(pipeline.search_index, 'search', return_value=[mock_result1, mock_result2]):
            results = pipeline.search("test", tag="python")
        assert len(results) == 1
        assert results[0].url == "https://example.com"

    def test_pipeline_get_stats(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        with patch.object(pipeline.search_index, 'get_page_count', return_value=42), \
             patch.object(pipeline.interest_store, 'list_all', return_value=[MagicMock()]), \
             patch.object(pipeline.tag_store, 'get_tag_count', return_value=10), \
             patch.object(pipeline.tag_store, 'get_tagged_page_count', return_value=5):
            stats = pipeline.get_stats()
        assert stats["indexed_pages"] == 42
        assert stats["total_interests"] == 1
        assert stats["total_tags"] == 10
        assert stats["tagged_pages"] == 5

    def test_pipeline_add_page_directly_no_content(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        from personal_index.models import CrawledPage
        page = CrawledPage(url="https://example.com", title="Test", content="")
        with patch.object(pipeline.content_filter, 'should_include', return_value=False):
            result = pipeline.add_page_directly(page)
        assert result is False

    def test_pipeline_add_page_directly_success(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        from personal_index.models import CrawledPage
        page = CrawledPage(url="https://example.com", title="Test", content="Some content here")
        mock_score_result = MagicMock()
        mock_score_result.total = 0.8
        with patch.object(pipeline.content_filter, 'should_include', return_value=True), \
             patch.object(pipeline.scorer, 'score_page', return_value=mock_score_result), \
             patch.object(pipeline.interest_store, 'list_all', return_value=[]), \
             patch.object(pipeline.search_index, 'add_page', return_value=None):
            result = pipeline.add_page_directly(page)
        assert result is True

    def test_pipeline_add_page_directly_below_threshold(self, mock_pipeline):
        pipeline, _mocks = mock_pipeline
        from personal_index.models import CrawledPage
        page = CrawledPage(url="https://example.com", title="Test", content="Some content")
        mock_score_result = MagicMock()
        mock_score_result.total = 0.0
        pipeline.config.min_score_threshold = 0.5
        with patch.object(pipeline.content_filter, 'should_include', return_value=True), \
             patch.object(pipeline.scorer, 'score_page', return_value=mock_score_result), \
             patch.object(pipeline.interest_store, 'list_all', return_value=[]):
            result = pipeline.add_page_directly(page)
        assert result is False

    def test_pipeline_run_with_mocked_crawl(self, mock_pipeline, tmp_path):
        """Test Pipeline.run() with mocked _fetch_page."""
        pipeline, _mocks = mock_pipeline
        from personal_index.models import CrawledPage

        mock_page = CrawledPage(
            url="https://example.com",
            title="Test Page",
            content="This is test content with python programming",
            status_code=200,
        )
        pipeline._fetch_page = MagicMock(return_value=mock_page)

        mock_score_result = MagicMock()
        mock_score_result.total = 0.8

        with patch.object(pipeline.content_filter, 'should_include', return_value=True), \
             patch.object(pipeline.scorer, 'score_page', return_value=mock_score_result), \
             patch.object(pipeline.interest_store, 'list_all', return_value=[]), \
             patch.object(pipeline.search_index, 'add_page', return_value=None):
            stats = pipeline.run(["https://example.com"])
        assert stats.pages_crawled == 1
