"""Integration tests for PipelineOrchestrator - full pipeline verification.

Tests the complete crawl→extract→filter→score→tag→index→search pipeline
using local files (no network required).
"""

from __future__ import annotations

import os

from personal_index.config.pipeline_config import PipelineConfig
from personal_index.pipeline_orchestrator import PipelineOrchestrator, PipelineResult


class TestPipelineOrchestratorInit:
    """Test PipelineOrchestrator initialization."""

    def test_default_init(self, tmp_path):
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        assert orch.data_dir == data_dir
        assert orch.interest_store is not None
        assert orch.tag_store is not None
        assert orch.search_index is not None
        orch.close()

    def test_init_creates_directories(self, tmp_path):
        data_dir = str(tmp_path / "data")
        PipelineOrchestrator(data_dir=data_dir)
        assert os.path.isdir(os.path.join(data_dir, "cache"))
        assert os.path.isdir(os.path.join(data_dir, "archive"))
        assert os.path.isdir(os.path.join(data_dir, "backups"))

    def test_init_with_custom_config(self, tmp_path):
        data_dir = str(tmp_path / "data")
        config = PipelineConfig(min_content_length=50, max_pages=50)
        orch = PipelineOrchestrator(data_dir=data_dir, config=config)
        assert orch.config.min_content_length == 50
        orch.close()


class TestPipelineFromFileImport:
    """Test pipeline with local file imports."""

    def _create_test_files(self, tmp_path):
        """Create test content files."""
        docs = tmp_path / "docs"
        docs.mkdir()

        (docs / "python_intro.txt").write_text(
            "Python is a versatile programming language used for web development, "
            "data science, and automation. It features clean syntax and a large "
            "standard library. Python supports multiple programming paradigms "
            "including procedural, object-oriented, and functional programming."
        )

        (docs / "javascript_guide.txt").write_text(
            "JavaScript is the language of the web. It powers interactive "
            "websites and modern web applications. Node.js extends JavaScript "
            "to server-side development. JavaScript frameworks like React and "
            "Vue.js enable building complex user interfaces."
        )

        (docs / "short.txt").write_text(
            "Too short"
        )

        (docs / "devops.txt").write_text(
            "DevOps practices include continuous integration, continuous deployment, "
            "infrastructure as code, and monitoring. Tools like Docker, Kubernetes, "
            "and Jenkins automate the software delivery pipeline. DevOps culture "
            "promotes collaboration between development and operations teams."
        )

        return docs

    def test_run_from_files_basic(self, tmp_path):
        """Test basic file import pipeline."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.success is True
        assert result.stats.pages_crawled > 0
        assert result.stats.pages_indexed > 0
        orch.close()

    def test_run_from_files_filters_short_content(self, tmp_path):
        """Test that short content is filtered out."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        config = PipelineConfig(min_content_length=100)
        orch = PipelineOrchestrator(data_dir=data_dir, config=config)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        # short.txt should be filtered out
        assert result.stats.pages_filtered_out >= 1
        orch.close()

    def test_run_from_files_with_interests(self, tmp_path):
        """Test pipeline scoring with configured interests."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)

        # Add interests before running
        from personal_index.models import Interest
        orch.interest_store.add(Interest(
            name="programming",
            keywords=["python", "javascript", "programming"],
        ))

        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.success is True
        assert result.stats.pages_scored > 0
        orch.close()

    def test_run_from_files_tags_pages(self, tmp_path):
        """Test that pages get tagged during pipeline."""
        data_dir = str(tmp_path / "data")
        docs = self._create_test_files(tmp_path)

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(f) for f in docs.glob("*.txt")]
        result = orch.run_from_files(files)

        assert result.stats.tags_applied > 0
        orch.close()

    def test_run_from_files_empty_list(self, tmp_path):
        """Test pipeline with no files."""
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch.run_from_files([])

        assert result.success is True
        assert result.stats.pages_crawled == 0
        assert result.stats.pages_indexed == 0
        orch.close()

    def test_run_from_files_nonexistent(self, tmp_path):
        """Test pipeline with nonexistent files."""
        data_dir = str(tmp_path / "data")
        orch = PipelineOrchestrator(data_dir=data_dir)
        result = orch.run_from_files(["/nonexistent/file.txt"])

        assert result.success is True
        assert result.stats.pages_crawled == 0
        orch.close()


class TestPipelineSearch:
    """Test search after pipeline execution."""

    def test_search_after_import(self, tmp_path):
        """Test that search works after pipeline import."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development and data science."
        )

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(docs / "article.txt")]
        orch.run_from_files(files)

        results = orch.search("python")
        assert len(results) >= 1
        orch.close()

    def test_search_no_results(self, tmp_path):
        """Test search with no matching results."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development."
        )

        orch = PipelineOrchestrator(data_dir=data_dir)
        files = [str(docs / "article.txt")]
        orch.run_from_files(files)

        results = orch.search("quantum physics")
        assert len(results) == 0
        orch.close()

    def test_search_persists_across_instances(self, tmp_path):
        """Test that search index persists between orchestrator instances."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development."
        )

        # First instance: import
        orch1 = PipelineOrchestrator(data_dir=data_dir)
        orch1.run_from_files([str(docs / "article.txt")])
        orch1.close()

        # Second instance: search
        orch2 = PipelineOrchestrator(data_dir=data_dir)
        results = orch2.search("python")
        assert len(results) >= 1
        orch2.close()


class TestPipelineResult:
    """Test PipelineResult data class."""

    def test_result_summary(self):
        from personal_index.models import PipelineStats
        result = PipelineResult(stats=PipelineStats(
            pages_crawled=10,
            pages_extracted=10,
            pages_passed_filter=8,
            pages_scored=8,
            pages_tagged=8,
            pages_indexed=8,
            tags_applied=24,
            elapsed_seconds=1.5,
        ))
        summary = result.summary()
        assert "Pipeline Result" in summary
        assert "Pages crawled:    10" in summary
        assert "Pages indexed:    8" in summary

    def test_result_with_errors(self):
        result = PipelineResult(success=False, errors=["test error"])
        assert result.success is False
        assert len(result.errors) == 1


class TestPipelineProgressCallback:
    """Test progress callback integration."""

    def test_progress_callback_called(self, tmp_path):
        """Test that progress callback receives updates."""
        data_dir = str(tmp_path / "data")
        docs = tmp_path / "docs"
        docs.mkdir()
        (docs / "article.txt").write_text(
            "Python programming language for web development and data science. "
            "This is a longer article with enough content to pass the filter. "
            "It covers various topics including programming, development, and more."
        )

        callbacks = []

        def callback(stage, current, total):
            callbacks.append((stage, current, total))

        orch = PipelineOrchestrator(data_dir=data_dir, progress_callback=callback)
        orch.run_from_files([str(docs / "article.txt")])
        orch.close()

        assert len(callbacks) > 0
        stages = [c[0] for c in callbacks]
        assert "read" in stages or "filter" in stages
