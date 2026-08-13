"""Tests for pipeline configuration."""

import tempfile

from personal_index.config.pipeline_config import (
    PipelineConfig,
    PipelineStepConfig,
    load_pipeline_config,
)


class TestPipelineStepConfig:
    def test_defaults(self):
        s = PipelineStepConfig()
        assert s.name == ""
        assert s.enabled is True

    def test_custom(self):
        s = PipelineStepConfig(name="crawl", enabled=False)
        assert s.name == "crawl"
        assert s.enabled is False


class TestPipelineConfig:
    def test_defaults(self):
        c = PipelineConfig()
        assert c.enabled is True
        assert c.steps == []
        assert c.min_content_length == 10

    def test_get_enabled_steps(self):
        c = PipelineConfig(steps=[
            PipelineStepConfig(name="crawl", enabled=True),
            PipelineStepConfig(name="parse", enabled=False),
        ])
        assert c.get_enabled_steps() == ["crawl"]

    def test_is_step_enabled_default(self):
        c = PipelineConfig()
        assert c.is_step_enabled("anything") is True

    def test_is_step_enabled_disabled(self):
        c = PipelineConfig(steps=[
            PipelineStepConfig(name="crawl", enabled=False),
        ])
        assert c.is_step_enabled("crawl") is False

    def test_disable_step_existing(self):
        c = PipelineConfig(steps=[
            PipelineStepConfig(name="crawl", enabled=True),
        ])
        c.disable_step("crawl")
        assert c.is_step_enabled("crawl") is False

    def test_disable_step_new(self):
        c = PipelineConfig()
        c.disable_step("newstep")
        assert c.is_step_enabled("newstep") is False

    def test_enable_step_existing(self):
        c = PipelineConfig(steps=[
            PipelineStepConfig(name="crawl", enabled=False),
        ])
        c.enable_step("crawl")
        assert c.is_step_enabled("crawl") is True

    def test_enable_step_new(self):
        c = PipelineConfig()
        c.enable_step("newstep")
        assert c.is_step_enabled("newstep") is True


class TestLoadPipelineConfig:
    def test_missing_file_returns_defaults(self):
        c = load_pipeline_config("/nonexistent/config.yaml")
        assert isinstance(c, PipelineConfig)
        assert c.enabled is True

    def test_load_from_file(self):
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
        tf.write("pipeline:\n  enabled: false\n  steps:\n    - name: crawl\n      enabled: true\n")
        tf.close()
        c = load_pipeline_config(tf.name)
        assert c.enabled is False
        assert len(c.steps) == 1
        assert c.steps[0].name == "crawl"
