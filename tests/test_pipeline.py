"""Tests for content processing pipeline."""

import pytest
from personal_index.pipeline import ContentPipeline, PipelineStep, PipelineResult


class TestPipelineStep:
    def test_execute_enabled(self):
        def handler(data):
            data["processed"] = True
            return data
        step = PipelineStep(name="test", handler=handler)
        result = step.execute({})
        assert result["processed"] is True

    def test_execute_disabled(self):
        step = PipelineStep(name="test", handler=lambda d: d, enabled=False)
        result = step.execute({"key": "value"})
        assert result == {"key": "value"}

    def test_execute_on_error_continue(self):
        def failing_handler(data):
            raise ValueError("fail")
        step = PipelineStep(name="test", handler=failing_handler, on_error="continue")
        result = step.execute({"key": "value"})
        assert result == {"key": "value"}

    def test_execute_on_error_stop(self):
        def failing_handler(data):
            raise ValueError("fail")
        step = PipelineStep(name="test", handler=failing_handler, on_error="stop")
        with pytest.raises(ValueError):
            step.execute({})


class TestContentPipeline:
    def test_add_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("step1", lambda d: d)
        assert pipeline.step_count == 1

    def test_run_empty_pipeline(self):
        pipeline = ContentPipeline()
        result = pipeline.run({"key": "value"})
        assert result == {"key": "value"}

    def test_run_single_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("upper", lambda d: {**d, "text": d.get("text", "").upper()})
        result = pipeline.run({"text": "hello"})
        assert result["text"] == "HELLO"

    def test_run_multiple_steps(self):
        pipeline = ContentPipeline()
        pipeline.add_step("add_a", lambda d: {**d, "a": 1})
        pipeline.add_step("add_b", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result == {"a": 1, "b": 2}

    def test_step_modifies_data(self):
        pipeline = ContentPipeline()
        pipeline.add_step("double", lambda d: {**d, "val": d.get("val", 0) * 2})
        result = pipeline.run({"val": 5})
        assert result["val"] == 10

    def test_error_continue(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError("fail")), on_error="continue")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result["a"] == 1
        assert result["b"] == 2

    def test_error_stop(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError("fail")), on_error="stop")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        with pytest.raises(ValueError):
            pipeline.run({})

    def test_step_count(self):
        pipeline = ContentPipeline()
        pipeline.add_step("s1", lambda d: d)
        pipeline.add_step("s2", lambda d: d)
        assert pipeline.step_count == 2

    def test_enabled_steps(self):
        pipeline = ContentPipeline()
        pipeline.add_step("a", lambda d: d)
        pipeline.add_step("b", lambda d: d)
        assert pipeline.enabled_steps == ["a", "b"]

    def test_pipeline_name(self):
        pipeline = ContentPipeline(name="custom")
        assert pipeline.name == "custom"
