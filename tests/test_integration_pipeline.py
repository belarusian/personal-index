"""Integration tests for the full content processing pipeline."""

from __future__ import annotations

import os
import tempfile

import pytest

from personal_index.app import PersonalIndexApp
from personal_index.pipeline import ContentPipeline, PipelineResult


class TestPipelineIntegration:
    """Test the full content processing pipeline end-to-end."""

    def setup_method(self):
        """Set up a temporary data directory for each test."""
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )

    def test_app_initializes(self):
        """App should initialize without errors."""
        self.app.initialize()
        assert self.app._initialized is True
        assert os.path.isdir(self.app.data_dir)

    def test_pipeline_has_steps(self):
        """Default pipeline should have processing steps."""
        self.app.initialize()
        assert self.app.pipeline.step_count >= 3

    def test_process_content_basic(self):
        """Processing content should return a result dict."""
        self.app.initialize()
        result = self.app.process_content(
            url="https://example.com/test",
            raw_content="<html><body><p>Hello world</p></body></html>",
            title="Test Page",
        )
        assert isinstance(result, dict)
        assert "url" in result
        assert result["url"] == "https://example.com/test"

    def test_process_content_adds_to_index(self):
        """Processed content should be added to the search index."""
        self.app.initialize()
        self.app.process_content(
            url="https://example.com/article1",
            raw_content="Python programming language tutorial",
            title="Python Tutorial",
        )
        results = self.app.search("Python")
        assert len(results) >= 1

    def test_search_returns_results(self):
        """Search should return results for indexed content."""
        self.app.initialize()
        self.app.process_content(
            url="https://example.com/ml",
            raw_content="Machine learning and artificial intelligence",
            title="ML Overview",
        )
        results = self.app.search("machine learning")
        assert len(results) >= 1
        assert any("ML Overview" in r.get("title", "") for r in results)

    def test_search_empty_index(self):
        """Search on empty index should return empty list."""
        self.app.initialize()
        results = self.app.search("nonexistent")
        assert results == []

    def test_add_interest(self):
        """Adding an interest should persist it."""
        self.app.initialize()
        self.app.add_interest(
            name="Python",
            keywords=["python", "programming"],
            priority=8,
        )
        interests = self.app.interest_store.list_all()
        assert len(interests) >= 1
        assert any(i.name == "Python" for i in interests)

    def test_get_stats(self):
        """Stats should return a dict with expected keys."""
        self.app.initialize()
        stats = self.app.get_stats()
        assert "indexed_items" in stats
        assert "interests" in stats
        assert "scheduled_jobs" in stats
        assert "pipeline_steps" in stats
        assert "data_dir" in stats

    def test_stats_reflect_indexed_content(self):
        """Stats should reflect the number of indexed items."""
        self.app.initialize()
        self.app.process_content(
            url="https://example.com/1",
            raw_content="First article about technology",
            title="Tech Article 1",
        )
        self.app.process_content(
            url="https://example.com/2",
            raw_content="Second article about science",
            title="Science Article 2",
        )
        stats = self.app.get_stats()
        assert stats["indexed_items"] >= 2

    def test_shutdown_saves_state(self):
        """Shutdown should complete without errors."""
        self.app.initialize()
        self.app.add_interest(name="Test", keywords=["test"])
        self.app.shutdown()  # Should not raise


class TestPipelineSteps:
    """Test individual pipeline steps."""

    def test_extract_step(self):
        """Extract step should pull text from HTML."""
        pipeline = ContentPipeline()
        from personal_index.content_extractor import extract_text

        def extract_step(data: dict) -> dict:
            data["extracted_text"] = extract_text(data.get("raw_content", ""))
            return data

        pipeline.add_step("extract", extract_step)
        result = pipeline.run({
            "raw_content": "<html><body><p>Hello</p></body></html>",
        })
        assert "extracted_text" in result.data
        assert "Hello" in result.data["extracted_text"]

    def test_score_step(self):
        """Score step should assign a numeric score."""
        pipeline = ContentPipeline()
        from personal_index.content_scoring import ContentScorer

        scorer = ContentScorer()

        def score_step(data: dict) -> dict:
            data["score"] = scorer.score(
                data.get("extracted_text", ""),
                data.get("title", ""),
            )
            return data

        pipeline.add_step("score", score_step)
        result = pipeline.run({
            "extracted_text": "Important content here",
            "title": "Great Title",
        })
        assert "score" in result.data
        assert isinstance(result.data["score"], (int, float))

    def test_pipeline_error_handling(self):
        """Pipeline should continue on step errors when configured."""
        pipeline = ContentPipeline()

        def good_step(data: dict) -> dict:
            data["good"] = True
            return data

        def bad_step(data: dict) -> dict:
            raise ValueError("intentional error")

        pipeline.add_step("good", good_step)
        pipeline.add_step("bad", bad_step, on_error="continue")
        pipeline.add_step("good2", lambda d: {**d, "good2": True})

        result = pipeline.run({})
        assert result.data.get("good") is True
        assert result.data.get("good2") is True
        assert result.steps_failed == 1

    def test_pipeline_stop_on_error(self):
        """Pipeline should stop when on_error is 'stop'."""
        pipeline = ContentPipeline()

        pipeline.add_step("good", lambda d: {**d, "good": True})
        pipeline.add_step("bad", lambda d: (_ for _ in ()).throw(ValueError()), on_error="stop")
        pipeline.add_step("good2", lambda d: {**d, "good2": True})

        result = pipeline.run({})
        assert result.data.get("good") is True
        assert "good2" not in result.data
        assert result.steps_failed == 1


class TestAppFullWorkflow:
    """Test the complete workflow: add interest, process, search."""

    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.app = PersonalIndexApp(
            config_path=os.path.join(self.tmpdir, "config.yaml"),
            data_dir=os.path.join(self.tmpdir, "data"),
        )
        self.app.initialize()

    def test_full_workflow(self):
        """Complete workflow: interest -> process -> search -> stats."""
        # Add an interest
        self.app.add_interest(
            name="AI",
            keywords=["artificial intelligence", "machine learning", "AI"],
            priority=9,
        )

        # Process some content
        articles = [
            ("https://example.com/ai-news", "New breakthrough in artificial intelligence research", "AI News"),
            ("https://example.com/ml-tools", "Top machine learning tools for 2024", "ML Tools"),
            ("https://example.com/cooking", "How to make pasta from scratch", "Cooking"),
        ]
        for url, content, title in articles:
            self.app.process_content(url, content, title)

        # Search for AI-related content
        results = self.app.search("artificial intelligence")
        assert len(results) >= 1

        # Verify stats
        stats = self.app.get_stats()
        assert stats["indexed_items"] >= 3
        assert stats["interests"] >= 1

    def test_multiple_searches(self):
        """Multiple searches should work independently."""
        self.app.process_content(
            "https://example.com/python", "Python is a great programming language", "Python Guide"
        )
        self.app.process_content(
            "https://example.com/rust", "Rust is a systems programming language", "Rust Guide"
        )

        python_results = self.app.search("Python")
        rust_results = self.app.search("Rust")

        assert len(python_results) >= 1
        assert len(rust_results) >= 1
        assert any("Python" in r.get("title", "") for r in python_results)
        assert any("Rust" in r.get("title", "") for r in rust_results)
