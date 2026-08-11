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


import pytest
class TestContentPipeline:
    def test_add_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("step1", lambda d: d)
        assert pipeline.step_count == 1

    def test_run_empty_pipeline(self):
        pipeline = ContentPipeline()
        result = pipeline.run({"key": "value"})
        assert result.success is True
        assert result.data == {"key": "value"}
        assert result.steps_executed == 0

    def test_run_single_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("upper", lambda d: {**d, "text": d.get("text", "").upper()})
        result = pipeline.run({"text": "hello"})
        assert result.data["text"] == "HELLO"
        assert result.steps_executed == 1

    def test_run_multiple_steps(self):
        pipeline = ContentPipeline()
        pipeline.add_step("add_a", lambda d: {**d, "a": 1})
        pipeline.add_step("add_b", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result.data == {"a": 1, "b": 2}
        assert result.steps_executed == 2

    def test_step_modifies_data(self):
        pipeline = ContentPipeline()
        pipeline.add_step("double", lambda d: {**d, "val": d.get("val", 0) * 2})
        result = pipeline.run({"val": 5})
        assert result.data["val"] == 10

    def test_disabled_step_skipped(self):
        pipeline = ContentPipeline()
        pipeline.add_step("step1", lambda d: {**d, "a": 1})
        pipeline.add_step("step2", lambda d: {**d, "b": 2})
        pipeline.disable_step("step2")
        result = pipeline.run({})
        assert result.data == {"a": 1}
        assert "b" not in result.data
        assert result.steps_executed == 1

    def test_error_continue(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError("fail")))
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result.success is False
        assert result.steps_failed == 1
        assert result.data["a"] == 1
        assert result.data["b"] == 2

    def test_error_stop(self):
        pipeline = ContentPipeline()
        pipeline.add_step("good", lambda d: {**d, "a": 1})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError("fail")), on_error="stop")
        pipeline.add_step("good2", lambda d: {**d, "b": 2})
        result = pipeline.run({})
        assert result.steps_executed == 1
        assert "b" not in result.data

    def test_remove_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("s1", lambda d: d)
        pipeline.add_step("s2", lambda d: d)
        assert pipeline.remove_step("s1") is True
        assert pipeline.step_count == 1
        assert pipeline.remove_step("nonexistent") is False

    def test_enable_disable_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("s1", lambda d: d)
        pipeline.disable_step("s1")
        assert "s1" not in pipeline.enabled_steps
        pipeline.enable_step("s1")
        assert "s1" in pipeline.enabled_steps

    def test_get_step(self):
        pipeline = ContentPipeline()
        pipeline.add_step("s1", lambda d: d)
        step = pipeline.get_step("s1")
        assert step is not None
        assert step.name == "s1"
        assert pipeline.get_step("missing") is None

    def test_clear(self):
        pipeline = ContentPipeline()
        pipeline.add_step("s1", lambda d: d)
        pipeline.clear()
        assert pipeline.step_count == 0

    def test_chained_add(self):
        pipeline = ContentPipeline()
        (pipeline.add_step("s1", lambda d: d)
                  .add_step("s2", lambda d: d)
                  .add_step("s3", lambda d: d))
        assert pipeline.step_count == 3

    def test_pipeline_name(self):
        pipeline = ContentPipeline(name="custom")
        assert pipeline.name == "custom"

    def test_enabled_steps_list(self):
        pipeline = ContentPipeline()
        pipeline.add_step("a", lambda d: d)
        pipeline.add_step("b", lambda d: d)
        pipeline.disable_step("b")
        assert pipeline.enabled_steps == ["a"]
